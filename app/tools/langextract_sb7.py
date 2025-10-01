"""
StoryBrand Framework Extractor using LangExtract
Uses Google's LangExtract library with LLMs to extract the 7 StoryBrand elements.
"""

import hashlib
import logging
import os
import textwrap
from typing import Any, Dict, List, Optional

try:
    import langextract as lx
except ImportError:
    raise ImportError(
        "LangExtract not installed. Please run: pip install langextract"
    )

logger = logging.getLogger(__name__)

from app.utils.cache import get_storybrand_cache, make_storybrand_cache_key
from app.utils.vertex_retry import VertexRetryExceededError, call_with_vertex_retry


class StoryBrandExtractor:
    """
    Extrai os 7 elementos do framework StoryBrand usando LangExtract com LLM.

    O framework StoryBrand define 7 elementos narrativos:
    1. Character (Personagem) - O cliente como herói
    2. Problem (Problema) - O que o cliente enfrenta (3 níveis)
    3. Guide (Guia) - A marca como mentor
    4. Plan (Plano) - Como resolver o problema
    5. Call to Action (Ação) - O que fazer agora
    6. Failure (Fracasso) - O que evitar
    7. Success (Sucesso) - A transformação desejada
    """

    def __init__(self, model_id: str = "gemini-2.5-flash", api_key: Optional[str] = None):
        """
        Inicializa o extrator com configurações do LangExtract.

        Args:
            model_id: Modelo a usar (default: gemini-2.5-flash)
            api_key: Chave API (se None, usa LANGEXTRACT_API_KEY do ambiente)
        """
        self.model_id = model_id
        self.cache_enabled = os.getenv("STORYBRAND_CACHE_ENABLED", "true").lower() != "false"
        self._cache = get_storybrand_cache()

        # Forçar uso de Vertex AI (sem API key)
        self.project = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        # Definir prompt para extração StoryBrand
        self.prompt = textwrap.dedent("""\
            Extract StoryBrand framework elements from landing page content.

            The StoryBrand framework has 7 narrative elements that should be identified:

            1. CHARACTER - The ideal customer/hero of the story
            2. PROBLEM - What problems they face (3 levels):
               - External: Tangible, practical problem
               - Internal: Feelings and frustrations
               - Philosophical: Why it's wrong/unfair
            3. GUIDE - How the brand positions itself:
               - Authority: Credentials, experience, testimonials
               - Empathy: Understanding of customer's problem
            4. PLAN - The steps to solve the problem
            5. ACTION - Calls to action (primary and secondary)
            6. FAILURE - What happens if they don't act
            7. SUCCESS - The transformation/outcome promised

            Extract exact text from the content when possible.
            Provide meaningful attributes for context.
            Use Portuguese (pt-BR) for attributes when the source is in Portuguese.
            If a StoryBrand element is not explicitly present, leave the corresponding field empty.
            Do not fabricate or infer content that is absent in the landing page.
            Only quote information that can be grounded in the provided text.
            """)

        # Criar exemplos para few-shot learning
        self.examples = self._create_storybrand_examples()

    def _create_storybrand_examples(self) -> List[lx.data.ExampleData]:
        """Cria exemplos de alta qualidade para treinar o modelo."""

        examples = []

        # Exemplo 1: Página de curso online
        example1_text = """
        Você é um empreendedor cansado de trabalhar muito e ganhar pouco?
        Sabemos como é frustrante ver seu negócio estagnado enquanto outros crescem.
        Com 15 anos de experiência, já ajudamos mais de 5.000 empresários como você.
        Nosso método comprovado em 3 passos simples: 1) Diagnóstico gratuito,
        2) Plano personalizado, 3) Acompanhamento semanal.
        Clique aqui para agendar sua consulta gratuita. Ou baixe nosso e-book.
        Não deixe sua empresa ficar para trás da concorrência.
        Transforme seu negócio em uma máquina de lucros em 90 dias.
        """

        examples.append(lx.data.ExampleData(
            text=example1_text,
            extractions=[
                # Character
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="empreendedor",
                    attributes={
                        "description": "dono de negócio",
                        "situation": "trabalhando muito e ganhando pouco"
                    }
                ),
                # Problem - External
                lx.data.Extraction(
                    extraction_class="problem_external",
                    extraction_text="ganhar pouco",
                    attributes={
                        "type": "problema financeiro",
                        "impact": "negócio não é lucrativo"
                    }
                ),
                # Problem - Internal
                lx.data.Extraction(
                    extraction_class="problem_internal",
                    extraction_text="frustrante ver seu negócio estagnado",
                    attributes={
                        "feeling": "frustração",
                        "cause": "estagnação enquanto outros crescem"
                    }
                ),
                # Problem - Philosophical
                lx.data.Extraction(
                    extraction_class="problem_philosophical",
                    extraction_text="enquanto outros crescem",
                    attributes={
                        "belief": "injustiça",
                        "reason": "merece crescer também"
                    }
                ),
                # Guide - Authority
                lx.data.Extraction(
                    extraction_class="guide_authority",
                    extraction_text="15 anos de experiência, já ajudamos mais de 5.000 empresários",
                    attributes={
                        "credentials": "15 anos experiência",
                        "proof": "5.000 empresários ajudados"
                    }
                ),
                # Guide - Empathy
                lx.data.Extraction(
                    extraction_class="guide_empathy",
                    extraction_text="Sabemos como é frustrante",
                    attributes={
                        "understanding": "compreende a frustração",
                        "connection": "já passou por isso"
                    }
                ),
                # Plan
                lx.data.Extraction(
                    extraction_class="plan",
                    extraction_text="3 passos simples: 1) Diagnóstico gratuito, 2) Plano personalizado, 3) Acompanhamento semanal",
                    attributes={
                        "steps": "3",
                        "step1": "Diagnóstico gratuito",
                        "step2": "Plano personalizado",
                        "step3": "Acompanhamento semanal"
                    }
                ),
                # Action - Primary
                lx.data.Extraction(
                    extraction_class="action_primary",
                    extraction_text="Clique aqui para agendar sua consulta gratuita",
                    attributes={
                        "type": "agendar consulta",
                        "incentive": "gratuita"
                    }
                ),
                # Action - Secondary
                lx.data.Extraction(
                    extraction_class="action_secondary",
                    extraction_text="baixe nosso e-book",
                    attributes={
                        "type": "download",
                        "resource": "e-book"
                    }
                ),
                # Failure
                lx.data.Extraction(
                    extraction_class="failure",
                    extraction_text="Não deixe sua empresa ficar para trás da concorrência",
                    attributes={
                        "consequence": "ficar para trás",
                        "threat": "concorrência vai passar na frente"
                    }
                ),
                # Success
                lx.data.Extraction(
                    extraction_class="success",
                    extraction_text="Transforme seu negócio em uma máquina de lucros em 90 dias",
                    attributes={
                        "transformation": "máquina de lucros",
                        "timeframe": "90 dias",
                        "benefit": "lucratividade"
                    }
                )
            ]
        ))

        # Exemplo 2: Landing institucional sem CTA explícito (ensina o modelo a deixar ACTION vazio)
        example2_text = """
        A Clínica Horizonte atende mulheres que buscam reposição hormonal segura e acompanhamento humano.
        Entendemos a insegurança de lidar com sintomas constantes sem uma equipe especializada.
        Nosso corpo clínico reúne endocrinologistas reconhecidos e protocolos baseados em evidência.
        Cada paciente passa por exames completos e um acompanhamento próximo com foco em longo prazo.
        A clínica prioriza acolhimento, transparência e comunicação direta com as pacientes.
        """

        examples.append(lx.data.ExampleData(
            text=example2_text,
            extractions=[
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="mulheres",
                    attributes={
                        "description": "pacientes que buscam reposição hormonal",
                        "stage": "enfrentando sintomas recorrentes"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="problem_internal",
                    extraction_text="insegurança de lidar com sintomas constantes",
                    attributes={
                        "feeling": "insegurança",
                        "symptom": "sintomas hormonais recorrentes"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="guide_authority",
                    extraction_text="corpo clínico reúne endocrinologistas reconhecidos",
                    attributes={
                        "credentials": "endocrinologistas especializados",
                        "evidence": "protocolos baseados em evidência"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="guide_empathy",
                    extraction_text="Entendemos a insegurança",
                    attributes={
                        "acknowledgement": "reconhece os sintomas prolongados",
                        "support": "acompanhamento humano"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="plan",
                    extraction_text="Cada paciente passa por exames completos e acompanhamento",
                    attributes={
                        "steps": "2",
                        "step1": "exames completos",
                        "step2": "acompanhamento próximo"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="failure",
                    extraction_text="sem uma equipe especializada",
                    attributes={
                        "risk": "seguir sem orientação médica",
                        "impact": "sintomas permanecem"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="success",
                    extraction_text="acolhimento, transparência e comunicação direta",
                    attributes={
                        "benefit": "acompanhamento contínuo",
                        "transformation": "sensação de segurança e cuidado"
                    }
                )
            ]
        ))

        # Exemplo 3: Landing sem plano estruturado (ensina a manter PLAN vazio)
        example3_text = """
        A Revista Urbanistas conta histórias de moradores que revitalizaram bairros abandonados.
        Mostrar o impacto positivo de iniciativas comunitárias inspira outras cidades a agir.
        Somos um coletivo de jornalistas e urbanistas que pesquisam políticas públicas e habitação.
        Novas edições trazem guias culturais, mapas de memória e entrevistas com lideranças locais.
        Assine para receber a próxima edição especial dedicada a mobilidade sustentável.
        Não deixe sua cidade perder oportunidades de transformação social.
        Cada relato prova que é possível viver em espaços mais humanos e seguros.
        """

        examples.append(lx.data.ExampleData(
            text=example3_text,
            extractions=[
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="moradores",
                    attributes={
                        "description": "habitantes engajados na revitalização",
                        "location": "bairros urbanos abandonados"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="problem_external",
                    extraction_text="bairros abandonados",
                    attributes={
                        "type": "degradação urbana",
                        "effect": "perda de vitalidade comunitária"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="guide_authority",
                    extraction_text="coletivo de jornalistas e urbanistas",
                    attributes={
                        "credentials": "especialistas em políticas públicas",
                        "experience": "pesquisam habitação e mobilidade"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="action_primary",
                    extraction_text="Assine para receber a próxima edição",
                    attributes={
                        "type": "assinatura",
                        "urgency": "próxima edição especial"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="failure",
                    extraction_text="Não deixe sua cidade perder oportunidades",
                    attributes={
                        "risk": "perder oportunidades de transformação",
                        "threat": "cidades ficam estagnadas"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="success",
                    extraction_text="possível viver em espaços mais humanos e seguros",
                    attributes={
                        "benefit": "espaços humanos",
                        "transformation": "cidades seguras"
                    }
                )
            ]
        ))

        # Exemplo 4: Página de produto SaaS (completo)
        example4_text = """
        Marketing teams struggling with content creation spend hours on repetitive tasks.
        We understand the pressure to produce quality content at scale.
        Our AI platform, trusted by Fortune 500 companies, automates your workflow.
        Get started in minutes: Connect your tools, Set your brand voice, Let AI work.
        Start your free trial today. Watch a demo video.
        Don't let competitors outpace your content production.
        Scale your content 10x while maintaining quality and brand consistency.
        """

        examples.append(lx.data.ExampleData(
            text=example4_text,
            extractions=[
                lx.data.Extraction(
                    extraction_class="character",
                    extraction_text="Marketing teams",
                    attributes={
                        "role": "marketing professionals",
                        "challenge": "content creation"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="problem_external",
                    extraction_text="spend hours on repetitive tasks",
                    attributes={
                        "type": "time waste",
                        "activity": "repetitive content tasks"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="problem_internal",
                    extraction_text="pressure to produce quality content at scale",
                    attributes={
                        "feeling": "pressure",
                        "source": "scale vs quality dilemma"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="guide_authority",
                    extraction_text="trusted by Fortune 500 companies",
                    attributes={
                        "credibility": "Fortune 500 clients",
                        "market_position": "enterprise-grade"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="guide_empathy",
                    extraction_text="We understand the pressure",
                    attributes={
                        "empathy": "understands challenge",
                        "tone": "supportive"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="plan",
                    extraction_text="Connect your tools, Set your brand voice, Let AI work",
                    attributes={
                        "simplicity": "3 simple steps",
                        "automation": "AI does the work"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="action_primary",
                    extraction_text="Start your free trial today",
                    attributes={
                        "urgency": "today",
                        "risk": "free trial"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="action_secondary",
                    extraction_text="Watch a demo video",
                    attributes={
                        "type": "demo",
                        "channel": "video"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="failure",
                    extraction_text="competitors outpace your content production",
                    attributes={
                        "risk": "falling behind",
                        "competitor": "advantage to others"
                    }
                ),
                lx.data.Extraction(
                    extraction_class="success",
                    extraction_text="Scale your content 10x while maintaining quality",
                    attributes={
                        "metric": "10x scale",
                        "benefit": "quality maintained"
                    }
                )
            ]
        ))

        return examples

    def _prepare_input(self, content: str) -> tuple[str, bool, dict[str, Any]]:
        """Normalize and adaptively truncate the HTML/text payload for Vertex AI."""

        if not isinstance(content, str):
            return "", False, {"input_length": 0, "strategy": "empty"}

        hard_limit = max(0, int(os.getenv("STORYBRAND_HARD_CHAR_LIMIT", "20000")))
        soft_limit = max(1000, int(os.getenv("STORYBRAND_SOFT_CHAR_LIMIT", "12000")))
        tail_ratio = float(os.getenv("STORYBRAND_TAIL_RATIO", "0.2"))
        tail_ratio = min(max(tail_ratio, 0.05), 0.4)

        length = len(content)
        overflow = max(0, length - soft_limit)
        adaptive_bonus = min(soft_limit, int(overflow * 0.3))
        allowed = soft_limit + adaptive_bonus
        if hard_limit:
            allowed = min(allowed, hard_limit)

        metadata: dict[str, Any] = {
            "input_length": length,
            "soft_limit": soft_limit,
            "hard_limit": hard_limit,
            "allowed_chars": allowed,
            "tail_ratio": tail_ratio,
        }

        if length <= allowed or allowed <= 0:
            metadata.update({"strategy": "passthrough", "truncated": False})
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            metadata["input_hash"] = digest
            return content, False, metadata

        head_chars = max(soft_limit, int(allowed * (1 - tail_ratio)))
        head_chars = min(head_chars, allowed)
        tail_chars = max(0, allowed - head_chars)
        truncated_content = content[:head_chars]
        if tail_chars:
            truncated_content += "\n<!-- storybrand:tail -->\n" + content[-tail_chars:]

        digest = hashlib.sha256(truncated_content.encode("utf-8")).hexdigest()
        metadata.update(
            {
                "strategy": "head_tail",
                "truncated": True,
                "head_chars": head_chars,
                "tail_chars": tail_chars,
                "input_hash": digest,
            }
        )
        return truncated_content, True, metadata

    def extract(self, page_content: str, *, landing_page_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Extrai os elementos StoryBrand do conteúdo HTML usando LangExtract.

        Args:
            page_content: Conteúdo da página (HTML bruto ou texto processado via Trafilatura)

        Returns:
            Dict com os 7 elementos StoryBrand extraídos
        """

        if not page_content:
            return self._empty_result()

        try:
            logger.info("Iniciando extração StoryBrand com LangExtract (Vertex AI)")

            # Parâmetros de performance via env vars (com defaults seguros)
            passes = int(os.getenv("STORYBRAND_EXTRACTION_PASSES", "1"))
            max_workers = int(os.getenv("STORYBRAND_MAX_WORKERS", "4"))
            max_char_buffer = int(os.getenv("STORYBRAND_MAX_CHAR_BUFFER", "1500"))

            prepared_input, truncated, truncation_info = self._prepare_input(page_content)
            if truncated:
                logger.info("StoryBrand input truncated", extra=truncation_info)
            else:
                logger.debug("StoryBrand input passthrough", extra=truncation_info)

            # Configurar parâmetros baseado no modo (Vertex AI ou Gemini API)
            extract_kwargs = {
                "text_or_documents": prepared_input,
                "prompt_description": self.prompt,
                "examples": self.examples,
                "model_id": self.model_id,  # String com nome do modelo
                "extraction_passes": passes,
                "max_workers": max_workers,
                "max_char_buffer": max_char_buffer,
                "use_schema_constraints": True,  # Forçar estrutura
                "fence_output": False
            }

            # Sempre usar Vertex AI via ADC (sem API key)
            logger.info(f"Usando Vertex AI - Projeto: {self.project}, Região: {self.location}")
            logger.info(
                "LangExtract params: passes=%s, max_workers=%s, max_char_buffer=%s",
                passes,
                max_workers,
                max_char_buffer,
            )
            extract_kwargs["language_model_params"] = {
                "vertexai": True,
                "project": self.project,
                "location": self.location,
            }

            cache_key = None
            if self.cache_enabled and truncation_info.get("input_hash"):
                cache_key = make_storybrand_cache_key(
                    truncation_info["input_hash"],
                    self.model_id,
                    passes,
                    max_workers,
                    max_char_buffer,
                    os.getenv("GOOGLE_CLOUD_PROJECT"),
                    landing_page_url or "",
                )
                cached = self._cache.get(cache_key) if cache_key else None
                if cached is not None:
                    logger.info(
                        "Retornando StoryBrand do cache local", extra={"landing_page_url": landing_page_url}
                    )
                    return cached

            # Executar extração com LangExtract usando retry/backoff
            result = call_with_vertex_retry(
                lambda: lx.extract(**extract_kwargs),
                logger_obj=logger,
            )

            # Converter resultado para formato StoryBrand
            converted = self._convert_to_storybrand_format(result)

            if cache_key:
                self._cache.set(cache_key, converted)

            return converted

        except VertexRetryExceededError as e:
            logger.error("Vertex AI saturado após múltiplas tentativas: %s", e)
            raise
        except Exception as e:
            logger.error(f"Erro ao extrair StoryBrand com LangExtract: {str(e)}")
            return self._empty_result()

    def _convert_to_storybrand_format(self, langextract_result) -> Dict[str, Any]:
        """
        Converte o resultado do LangExtract para nosso formato StoryBrand.

        Args:
            langextract_result: Resultado do LangExtract

        Returns:
            Dict no formato esperado pelo schema StoryBrand
        """

        # Inicializar estrutura de resposta
        storybrand = {
            'character': {'description': '', 'evidence': [], 'confidence': 0},
            'problem': {
                'description': '',
                'evidence': [],
                'types': {
                    'external': '',
                    'internal': '',
                    'philosophical': ''
                },
                'confidence': 0
            },
            'guide': {
                'description': '',
                'authority': '',
                'empathy': '',
                'evidence': [],
                'confidence': 0
            },
            'plan': {'description': '', 'steps': [], 'evidence': [], 'confidence': 0},
            'action': {'primary': '', 'secondary': '', 'evidence': [], 'confidence': 0},
            'failure': {'description': '', 'consequences': [], 'evidence': [], 'confidence': 0},
            'success': {
                'description': '',
                'benefits': [],
                'transformation': '',
                'evidence': [],
                'confidence': 0
            },
            'completeness_score': 0,
            'metadata': {}
        }

        # Processar extrações do LangExtract
        if hasattr(langextract_result, 'extractions'):
            extractions = langextract_result.extractions
        elif isinstance(langextract_result, dict) and 'extractions' in langextract_result:
            extractions = langextract_result['extractions']
        else:
            logger.warning("Formato de resultado LangExtract não reconhecido")
            return storybrand

        elements_found = set()

        for extraction in extractions:
            ext_class = extraction.extraction_class
            ext_text = extraction.extraction_text
            ext_attrs = extraction.attributes if hasattr(extraction, 'attributes') else {}

            # Character
            if ext_class == 'character':
                storybrand['character']['description'] = ext_attrs.get('description', ext_text)
                storybrand['character']['evidence'].append(ext_text)
                storybrand['character']['confidence'] = 0.9
                elements_found.add('character')

            # Problem types
            elif ext_class == 'problem_external':
                storybrand['problem']['types']['external'] = ext_text
                storybrand['problem']['evidence'].append(ext_text)
                elements_found.add('problem')

            elif ext_class == 'problem_internal':
                storybrand['problem']['types']['internal'] = ext_text
                storybrand['problem']['evidence'].append(ext_text)
                elements_found.add('problem')

            elif ext_class == 'problem_philosophical':
                storybrand['problem']['types']['philosophical'] = ext_text
                storybrand['problem']['evidence'].append(ext_text)
                elements_found.add('problem')

            # Guide
            elif ext_class == 'guide_authority':
                storybrand['guide']['authority'] = ext_text
                storybrand['guide']['evidence'].append(ext_text)
                storybrand['guide']['confidence'] = 0.8
                elements_found.add('guide')

            elif ext_class == 'guide_empathy':
                storybrand['guide']['empathy'] = ext_text
                storybrand['guide']['evidence'].append(ext_text)
                elements_found.add('guide')

            # Plan
            elif ext_class == 'plan':
                # Preencher somente quando houver conteúdo real.
                plan_steps_attr = ext_attrs.get('steps')
                if plan_steps_attr:
                    storybrand['plan']['description'] = plan_steps_attr
                elif ext_text:
                    storybrand['plan']['description'] = ext_text

                steps = []
                for key, value in ext_attrs.items():
                    if key.startswith('step') and value:
                        steps.append(value)
                if not steps and ext_text:
                    steps.append(ext_text)
                if steps:
                    storybrand['plan']['steps'] = steps
                if ext_text:
                    storybrand['plan']['evidence'].append(ext_text)
                storybrand['plan']['confidence'] = 0.85
                elements_found.add('plan')

            # Actions
            elif ext_class == 'action_primary':
                storybrand['action']['primary'] = ext_text
                storybrand['action']['evidence'].append(ext_text)
                storybrand['action']['confidence'] = 0.9
                elements_found.add('action')

            elif ext_class == 'action_secondary':
                storybrand['action']['secondary'] = ext_text
                storybrand['action']['evidence'].append(ext_text)
                elements_found.add('action')

            # Failure
            elif ext_class == 'failure':
                storybrand['failure']['description'] = ext_attrs.get('consequence', ext_text)
                storybrand['failure']['consequences'].append(ext_text)
                storybrand['failure']['evidence'].append(ext_text)
                storybrand['failure']['confidence'] = 0.75
                elements_found.add('failure')

            # Success
            elif ext_class == 'success':
                storybrand['success']['transformation'] = ext_attrs.get('transformation', ext_text)
                storybrand['success']['benefits'].append(ext_text)
                storybrand['success']['evidence'].append(ext_text)
                storybrand['success']['confidence'] = 0.85
                elements_found.add('success')

        # Compilar descrições dos problemas
        if any(storybrand['problem']['types'].values()):
            problems = [p for p in storybrand['problem']['types'].values() if p]
            storybrand['problem']['description'] = '; '.join(problems)
            storybrand['problem']['confidence'] = 0.8

        # Compilar descrição do guia
        if storybrand['guide']['authority'] or storybrand['guide']['empathy']:
            guide_parts = []
            if storybrand['guide']['authority']:
                guide_parts.append(f"Autoridade: {storybrand['guide']['authority']}")
            if storybrand['guide']['empathy']:
                guide_parts.append(f"Empatia: {storybrand['guide']['empathy']}")
            storybrand['guide']['description'] = '; '.join(guide_parts)

        # Calcular completeness score
        total_elements = 7
        found_count = len(elements_found)
        storybrand['completeness_score'] = round(found_count / total_elements, 2)

        # Adicionar metadados
        storybrand['metadata'] = {
            'extraction_method': 'langextract',
            'model_used': self.model_id,
            'elements_found': list(elements_found),
            'total_extractions': len(extractions) if extractions else 0
        }

        logger.info(f"Extração StoryBrand completa. Score: {storybrand['completeness_score']}")
        logger.info(f"Elementos encontrados: {', '.join(elements_found)}")

        return storybrand

    def _empty_result(self) -> Dict:
        """Retorna estrutura vazia para casos de erro."""
        return {
            'character': {'description': '', 'evidence': [], 'confidence': 0},
            'problem': {
                'description': '',
                'evidence': [],
                'types': {'external': '', 'internal': '', 'philosophical': ''},
                'confidence': 0
            },
            'guide': {
                'description': '',
                'authority': '',
                'empathy': '',
                'evidence': [],
                'confidence': 0
            },
            'plan': {'description': '', 'steps': [], 'evidence': [], 'confidence': 0},
            'action': {'primary': '', 'secondary': '', 'evidence': [], 'confidence': 0},
            'failure': {'description': '', 'consequences': [], 'evidence': [], 'confidence': 0},
            'success': {
                'description': '',
                'benefits': [],
                'transformation': '',
                'evidence': [],
                'confidence': 0
            },
            'completeness_score': 0,
            'metadata': {'extraction_method': 'langextract', 'error': 'extraction_failed'}
        }

    def save_visualization(self, result, output_dir: str = ".") -> str:
        """
        Salva os resultados e gera visualização HTML interativa.

        Args:
            result: Resultado da extração
            output_dir: Diretório para salvar arquivos

        Returns:
            Caminho do arquivo HTML gerado
        """
        try:
            import os
            from pathlib import Path

            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)

            # Salvar como JSONL
            jsonl_file = output_path / "storybrand_extraction.jsonl"
            lx.io.save_annotated_documents([result], str(jsonl_file.stem), str(output_path))

            # Gerar visualização HTML
            html_content = lx.visualize(str(jsonl_file))
            html_file = output_path / "storybrand_visualization.html"

            with open(html_file, "w", encoding="utf-8") as f:
                if hasattr(html_content, 'data'):
                    f.write(html_content.data)
                else:
                    f.write(html_content)

            logger.info(f"Visualização salva em: {html_file}")
            return str(html_file)

        except Exception as e:
            logger.error(f"Erro ao salvar visualização: {str(e)}")
            return ""
