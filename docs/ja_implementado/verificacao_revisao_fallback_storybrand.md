### Verificação da Revisão do Plano de Fallback — StoryBrand

Data: 2025-09-22

- Item: Uso do limiar `config.min_storybrand_completeness`
  - Veredicto: Correto
  - Evidência: `app/config.py` expõe o campo.

- Item: Manter contrato de estado (`storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context`)
  - Veredicto: Correto
  - Evidência: Persistência no estado no callback de análise.

- Item: Decisão de fallback posicionada após `landing_page_analyzer`
  - Veredicto: Correto
  - Evidência: `complete_pipeline` já encadeia análise → orquestrador de planejamento.

- Item: Plano cita chave inexistente `state['storybrand_completeness_score']`
  - Veredicto: Correto (inconsistência real)
  - Evidência: Score existe em `storybrand_analysis['completeness_score']`; não há `storybrand_completeness_score` no estado.
  - Nota: A revisão menciona `landing_page_context['storybrand_completeness']` como alternativa; não há gravação dessa chave no estado atualmente (apenas exemplo em comentário/docstring).

- Item: Gate deveria respeitar `PlanningOrRunSynth` (não chamar `planning_pipeline` direto)
  - Veredicto: Correto
  - Evidência: O pipeline atual utiliza `PlanningOrRunSynth` entre análise e planejamento.

- Item: Estrutura sugerida `app/agents/...` não existe
  - Veredicto: Correto
  - Evidência: Não há diretório `app/agents/`; agentes vivem em `app/agent.py` e submódulos (`callbacks`, `tools`).

- Item: Uso de `state['landing_page_analysis']` no coletor do fallback
  - Veredicto: Correto (inconsistência no plano)
  - Evidência: Chave padrão utilizada é `landing_page_context`; não há produção de `landing_page_analysis` no estado.

- Item: 16 seções precisam mapear para o schema `StoryBrandAnalysis` (7 elementos)
  - Veredicto: Correto
  - Evidência: `app/schemas/storybrand.py` define 7 elementos (+ metadata). O mapeamento não está especificado.

- Item: Definir `state['storybrand_completeness'] = 1.0` não previne reentradas
  - Veredicto: Correto
  - Evidência: A leitura de qualidade ocorre via `storybrand_analysis['completeness_score']`. Nenhum agente lê uma chave de topo `storybrand_completeness`.

- Item: Novos campos (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`) exigem ajustes no backend/frontend
  - Veredicto: Correto
  - Evidência: `WIZARD_INITIAL_STATE` não contém esses campos; `UserInputExtractor` não retorna essas chaves.

- Item: Checklist/documentação pedem diretórios não existentes
  - Veredicto: Correto
  - Evidência: Há `checklist.md` na raiz; não há `checklists/` nem `docs/storybrand_fallback.md`.

- Pontos de incerteza (mapeamento 16→7, vocabulário de `sexo_cliente_alvo`, versionamento do audit trail)
  - Veredicto: Não verificável no código atual; requer decisão de design/dados.

Referências (trechos relevantes do código):

```52:56:/Users/institutorecriare/VSCodeProjects/instagram_ads/app/config.py
    web_fetch_timeout: int = 30
    cache_landing_pages: bool = True
    min_storybrand_completeness: float = 0.6
```

```113:124:/Users/institutorecriare/VSCodeProjects/instagram_ads/app/callbacks/landing_page_callbacks.py
            # Salvar no estado se disponível
            if hasattr(tool_context, 'state'):
                # Salvar análise completa
                tool_context.state['storybrand_analysis'] = analysis.model_dump()

                # Salvar resumo para fácil acesso
                tool_context.state['storybrand_summary'] = analysis.to_summary()

                # Salvar contexto para anúncios
                tool_context.state['storybrand_ad_context'] = analysis.to_ad_context()
```

```1221:1228:/Users/institutorecriare/VSCodeProjects/instagram_ads/app/agent.py
complete_pipeline = SequentialAgent(
    name="complete_pipeline",
    description="Pipeline completo (Ads): input → análise LP → planejamento → execução → montagem → validação.",
    sub_agents=[
        input_processor,
        landing_page_analyzer,  # NOVO: adicionar aqui
        PlanningOrRunSynth(synth_agent=context_synthesizer, planning_agent=planning_pipeline),
        execution_pipeline
    ],
```

```82:116:/Users/institutorecriare/VSCodeProjects/instagram_ads/app/schemas/storybrand.py
class StoryBrandAnalysis(BaseModel):
    """
    Análise completa do framework StoryBrand.

    Este modelo estrutura os 7 elementos do StoryBrand de Donald Miller,
    fornecendo uma análise narrativa completa da página analisada.
    """

    character: CharacterElement = Field(
        description="O cliente como herói da história"
    )
    problem: ProblemElement = Field(
        description="Os problemas que o cliente enfrenta"
    )
    guide: GuideElement = Field(
        description="A marca como guia/mentor"
    )
    plan: PlanElement = Field(
        description="O plano de ação proposto"
    )
    action: ActionElement = Field(
        description="Calls to action"
    )
    failure: FailureElement = Field(
        description="O que acontece se não agir"
    )
    success: SuccessElement = Field(
        description="A transformação desejada"
    )
    completeness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de completude da análise (0-1)"
    )
```

```12:19:/Users/institutorecriare/VSCodeProjects/instagram_ads/frontend/src/constants/wizard.constants.ts
export const WIZARD_INITIAL_STATE: WizardFormState = {
  landing_page_url: '',
  objetivo_final: '',
  formato_anuncio: '',
  perfil_cliente: '',
  foco: '',
};
```


