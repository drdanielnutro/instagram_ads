"""
Callbacks for processing landing page content.
Integrates StoryBrand analysis after web fetching.
"""

import logging
import json
from typing import Any, Dict, Optional
from app.tools.langextract_sb7 import StoryBrandExtractor
from app.schemas.storybrand import StoryBrandAnalysis

logger = logging.getLogger(__name__)


def process_and_extract_sb7(
    *,
    tool: Any,
    args: Dict[str, Any] | None = None,
    tool_context: Any,
    tool_response: Dict[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """
    Callback para processar HTML com análise StoryBrand após web fetch.

    Este callback é executado após a ferramenta web_fetch_tool,
    aplicando o framework StoryBrand ao conteúdo extraído.

    Args:
        tool_context: Contexto da ferramenta com acesso ao estado
        tool: A ferramenta que foi executada
        result: Resultado da ferramenta
        **kwargs: Argumentos adicionais do ADK (como 'args')

    Returns:
        O resultado original, potencialmente modificado
    """

    # Verificar se é a ferramenta correta
    if not hasattr(tool, 'name') or tool.name != 'web_fetch_tool':
        return tool_response

    # Verificar se o fetch foi bem-sucedido
    result = tool_response or {}
    if not isinstance(result, dict) or result.get('status') != 'success':
        logger.warning("Web fetch não foi bem-sucedido, pulando análise StoryBrand")
        return result

    # Preferir texto limpo do Trafilatura quando disponível (melhor latência/precisão)
    text_content = result.get('text_content')
    html_content = result.get('html_content', '')
    if not (text_content or html_content):
        logger.warning("Conteúdo vazio, pulando análise StoryBrand")
        return result

    try:
        logger.info("Iniciando análise StoryBrand do conteúdo HTML")

        # Criar extrator e processar
        extractor = StoryBrandExtractor()
        # Se houver texto limpo, usar; senão, cair para HTML bruto
        storybrand_data = extractor.extract(text_content or html_content)

        # Validar com schema Pydantic
        try:
            # Converter dados brutos para modelo Pydantic
            analysis = StoryBrandAnalysis(**storybrand_data)

            # Salvar no estado se disponível
            if hasattr(tool_context, 'state'):
                # Salvar análise completa
                tool_context.state['storybrand_analysis'] = analysis.model_dump()

                # Salvar resumo para fácil acesso
                tool_context.state['storybrand_summary'] = analysis.to_summary()

                # Salvar contexto para anúncios
                tool_context.state['storybrand_ad_context'] = analysis.to_ad_context()

                logger.info(f"Análise StoryBrand salva no estado. Completeness: {analysis.completeness_score}")

            # Adicionar análise ao resultado
            result['storybrand_analysis'] = analysis.model_dump()
            result['storybrand_summary'] = analysis.to_summary()
            result['storybrand_completeness'] = analysis.completeness_score

            # Log de elementos encontrados
            elements_found = []
            if analysis.character.confidence > 0:
                elements_found.append('Character')
            if analysis.problem.confidence > 0:
                elements_found.append('Problem')
            if analysis.guide.confidence > 0:
                elements_found.append('Guide')
            if analysis.plan.confidence > 0:
                elements_found.append('Plan')
            if analysis.action.confidence > 0:
                elements_found.append('Action')
            if analysis.failure.confidence > 0:
                elements_found.append('Failure')
            if analysis.success.confidence > 0:
                elements_found.append('Success')

            logger.info(f"Elementos StoryBrand identificados: {', '.join(elements_found)}")

        except Exception as e:
            logger.error(f"Erro ao validar análise StoryBrand com schema: {str(e)}")
            # Ainda assim salvar dados brutos
            if hasattr(tool_context, 'state'):
                tool_context.state['storybrand_raw'] = storybrand_data

    except Exception as e:
        logger.error(f"Erro ao processar análise StoryBrand: {str(e)}")

    return result


def check_storybrand_quality(tool_context: Any) -> Dict[str, Any]:
    """
    Verifica a qualidade da análise StoryBrand e decide se deve escalar.

    Esta função pode ser usada como ferramenta para verificar se a análise
    StoryBrand atingiu qualidade suficiente.

    Args:
        tool_context: Contexto com acesso ao estado

    Returns:
        Dict com status da verificação
    """

    if not hasattr(tool_context, 'state'):
        return {
            "status": "error",
            "message": "Sem acesso ao estado"
        }

    analysis = tool_context.state.get('storybrand_analysis')
    if not analysis:
        return {
            "status": "incomplete",
            "message": "Análise StoryBrand não encontrada"
        }

    # Verificar completeness score
    completeness = analysis.get('completeness_score', 0)

    # Critério de qualidade: pelo menos 60% de completude
    MIN_COMPLETENESS = 0.6

    if completeness >= MIN_COMPLETENESS:
        # Análise satisfatória - escalar para parar loop
        tool_context.actions.escalate = True
        return {
            "status": "success",
            "message": f"Análise StoryBrand completa (score: {completeness})",
            "should_continue": False
        }
    else:
        # Análise incompleta - continuar tentando
        missing_elements = []

        if analysis.get('character', {}).get('confidence', 0) < 0.3:
            missing_elements.append('Character')
        if analysis.get('problem', {}).get('confidence', 0) < 0.3:
            missing_elements.append('Problem')
        if analysis.get('guide', {}).get('confidence', 0) < 0.3:
            missing_elements.append('Guide')
        if analysis.get('plan', {}).get('confidence', 0) < 0.3:
            missing_elements.append('Plan')
        if analysis.get('action', {}).get('confidence', 0) < 0.3:
            missing_elements.append('Action')

        return {
            "status": "incomplete",
            "message": f"Análise incompleta (score: {completeness})",
            "missing_elements": missing_elements,
            "should_continue": True
        }


def enrich_landing_context_with_storybrand(callback_context: Any) -> None:
    """
    Enriquece o contexto da landing page com insights do StoryBrand.

    Este callback pode ser usado após a análise para enriquecer
    o contexto que será usado pelos agentes subsequentes.

    Args:
        callback_context: Contexto do callback com acesso ao estado
    """

    if not hasattr(callback_context, 'state'):
        return

    # Obter análise StoryBrand
    storybrand = callback_context.state.get('storybrand_ad_context')
    if not storybrand:
        return

    # Obter ou criar contexto da landing page
    landing_context = callback_context.state.get('landing_page_context', {})
    if isinstance(landing_context, str):
        try:
            landing_context = json.loads(landing_context)
        except:
            landing_context = {}

    # Enriquecer com StoryBrand
    if not isinstance(landing_context, dict):
        landing_context = {}

    # Adicionar elementos do StoryBrand ao contexto
    landing_context['storybrand_persona'] = storybrand.get('persona', '')
    landing_context['storybrand_dores'] = storybrand.get('dores_principais', [])
    landing_context['storybrand_proposta'] = storybrand.get('proposta_valor', '')
    landing_context['storybrand_autoridade'] = storybrand.get('autoridade', '')
    landing_context['storybrand_beneficios'] = storybrand.get('beneficios', [])
    landing_context['storybrand_transformacao'] = storybrand.get('transformacao', '')
    landing_context['storybrand_cta_principal'] = storybrand.get('cta_principal', '')
    landing_context['storybrand_urgencia'] = storybrand.get('urgencia', [])

    # Salvar contexto enriquecido
    callback_context.state['landing_page_context'] = landing_context
    callback_context.state['landing_context_enriched'] = True

    logger.info("Contexto da landing page enriquecido com análise StoryBrand")
