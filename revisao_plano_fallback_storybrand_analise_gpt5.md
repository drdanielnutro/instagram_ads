# Revisão técnica do plano de fallback StoryBrand — GPT‑5

Este documento consolida a verificação, no código‑fonte real, das inconsistências apontadas em `revisao_plano_fallback_storybrand.md` sobre o plano `aprimoramento_plano_storybrand_v2.md`, e expande cada sugestão com base no que já existe no projeto.

## Escopo e fontes consultadas
- Plano: `aprimoramento_plano_storybrand_v2.md`
- Revisão: `revisao_plano_fallback_storybrand.md`
- Código: `app/agent.py`, `app/callbacks/landing_page_callbacks.py`, `app/tools/langextract_sb7.py`, `app/schemas/storybrand.py`, `app/config.py`, `helpers/user_extract_data.py`, `frontend/src/constants/wizard.constants.ts`
- Referência ADK: [ADK docs](https://google.github.io/adk-docs/)

---

## Inconsistências e sugestões (validadas no código)

### 1) Chave `storybrand_completeness_score`
- Conclusão: Concordo com a inconsistência apontada.
- Evidência no código:
  - O score é salvo em `state['storybrand_analysis']['completeness_score']` e também exposto como `result['storybrand_completeness']` pelo callback pós‑fetch.
  - Não existe `state['storybrand_completeness_score']`.
```python
# app/callbacks/landing_page_callbacks.py (trecho)
analysis = StoryBrandAnalysis(**storybrand_data)
if hasattr(tool_context, 'state'):
    tool_context.state['storybrand_analysis'] = analysis.model_dump()
    tool_context.state['storybrand_summary'] = analysis.to_summary()
    tool_context.state['storybrand_ad_context'] = analysis.to_ad_context()
# Adicionado ao resultado do fetch
result['storybrand_analysis'] = analysis.model_dump()
result['storybrand_summary'] = analysis.to_summary()
result['storybrand_completeness'] = analysis.completeness_score
```
```python
# app/schemas/storybrand.py (trecho)
completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
```
- Sugestão (expandida): o gate deve ler o score via:
  - Primário: `ctx.session.state.get('storybrand_analysis', {}).get('completeness_score')`
  - Reserva: `ctx.session.state.get('landing_page_context', {}).get('storybrand_completeness')`

### 2) Ignorar `PlanningOrRunSynth` e chamar `planning_pipeline` direto
- Conclusão: Concordo com a inconsistência.
- Evidência no código:
  - O pipeline atual usa `PlanningOrRunSynth` para decidir entre sintetizar apenas o briefing (quando já há plano fixo) ou rodar o planejamento completo.
```python
# app/agent.py (trecho)
complete_pipeline = SequentialAgent(
    sub_agents=[
        input_processor,
        landing_page_analyzer,
        PlanningOrRunSynth(synth_agent=context_synthesizer, planning_agent=planning_pipeline),
        execution_pipeline,
    ],
)
```
- Sugestão (expandida): o gate, no caminho “feliz”, deve invocar a instância já criada de `PlanningOrRunSynth` (e não chamar `planning_pipeline` diretamente), preservando o modo `planning_mode == "fixed"`.

### 3) Estrutura de diretórios sugerida (`app/agents/...`) não existe
- Conclusão: Concordo.
- Evidência no projeto: hoje todos os agentes vivem em `app/agent.py` (callbacks em `app/callbacks`).
- Sugestão (expandida): duas opções viáveis e consistentes com o repositório atual:
  - Implementar `StoryBrandQualityGate` no próprio `app/agent.py` (menor difusão de mudanças), ou
  - Criar `app/agents/__init__.py` + módulos necessários, ajustando imports com cuidado.

### 4) Uso de `state['landing_page_analysis']` no fallback collector
- Conclusão: Concordo com a inconsistência.
- Evidência no código:
  - O output do `landing_page_analyzer` é gravado sob `landing_page_context` (não existe `landing_page_analysis`).
```python
# app/agent.py (trecho do agente de análise)
landing_page_analyzer = LlmAgent(
    ...,
    tools=[FunctionTool(func=web_fetch_tool)],
    after_tool_callback=process_and_extract_sb7,
    output_key="landing_page_context",
)
```
- Sugestão (expandida): o fallback deve consumir `state['landing_page_context']` para derivar campos auxiliares.

### 5) Mapeamento “16 seções” → schema `StoryBrandAnalysis` (7 elementos)
- Conclusão: Concordo com a inconsistência.
- Evidência no código:
  - O schema oficial contém os 7 elementos (`character`, `problem`, `guide`, `plan`, `action`, `failure`, `success`) e `completeness_score`.
```python
# app/schemas/storybrand.py (trecho)
class StoryBrandAnalysis(BaseModel):
    character: CharacterElement
    problem: ProblemElement
    guide: GuideElement
    plan: PlanElement
    action: ActionElement
    failure: FailureElement
    success: SuccessElement
    completeness_score: float
```
- Sugestão (expandida): documentar explicitamente o mapeamento de cada uma das 16 seções para os campos do schema, por exemplo:
  - `problem_external` → `problem.types.external`
  - `problem_internal` → `problem.types.internal`
  - `problem_philosophical` → `problem.types.philosophical`
  - `plan` (seção) → `plan.description`/`plan.steps`
  - CTAs → `action.primary`/`action.secondary`
  - etc.
  Sem esse mapeamento, o compilador do fallback não consegue gerar um `StoryBrandAnalysis` válido.

### 6) Definir `state['storybrand_completeness'] = 1.0` como garantia
- Conclusão: Concordo com a crítica (insuficiente).
- Evidência no consumo atual: leitores apontam para `storybrand_analysis.completeness_score` e, opcionalmente, `landing_page_context['storybrand_completeness']`.
- Sugestão (expandida): quando o fallback recompilar o StoryBrand, deve atualizar diretamente `storybrand_analysis['completeness_score']` (e opcionalmente sincronizar `landing_page_context['storybrand_completeness']`). Apenas criar uma chave avulsa `state['storybrand_completeness']` não previne reentrada do fallback.

### 7) Novos campos (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`) ausentes no backend/frontend
- Conclusão: Concordo.
- Evidência no backend (`helpers/user_extract_data.py`): somente os 5 campos atuais são extraídos.
```python
# helpers/user_extract_data.py (trecho)
data = {
  "landing_page_url": None,
  "objetivo_final": None,
  "perfil_cliente": None,
  "formato_anuncio": None,
  "foco": None,
}
```
- Evidência no frontend (`frontend/src/constants/wizard.constants.ts`): o `WIZARD_INITIAL_STATE` inclui apenas os mesmos 5 campos.
```ts
export const WIZARD_INITIAL_STATE = {
  landing_page_url: '',
  objetivo_final: '',
  formato_anuncio: '',
  perfil_cliente: '',
  foco: '',
};
```
- Sugestão (expandida):
  - Backend: ampliar o extractor para reconhecer e validar `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`.
  - Frontend: incluir campos opcionais e respectivas validações/UX no Wizard (estado inicial, envio ao backend).

### 8) Checklist e documentação em diretórios não existentes
- Conclusão: Concordo.
- Evidência no repo: existe `checklist.md` na raiz; não há `checklists/storybrand_fallback.md`.
- Sugestão (expandida):
  - Opção A: manter um único `checklist.md`, adicionando a seção do fallback.
  - Opção B: criar `checklists/storybrand_fallback.md` e referenciá‑lo em `AGENTS.md`/README, alinhando com o fluxo “Checklist Primeiro, Código Depois”.

---

## Itens corretos do plano (confirmados no código)
- Limiar configurável: `config.min_storybrand_completeness = 0.6` já existe e deve ser usado pelo gate.
```python
# app/config.py (trecho)
min_storybrand_completeness: float = 0.6
```
- Posição do gate: após `landing_page_analyzer` é o ponto correto, pois o estado StoryBrand já foi populado.
- Contrato de estado: os consumidores atuais esperam `storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context` e (no contexto da LP) `storybrand_completeness`.

---

## Recomendações práticas para implementação (sem executar)
1) Gate de qualidade
- Ler score conforme item 1 e comparar com `config.min_storybrand_completeness`.
- Caminho “feliz”: chamar a instância de `PlanningOrRunSynth` já montada no pipeline.
- Caminho “fallback”: desviar para o pipeline de fallback.
- Registrar métricas em `state['storybrand_gate_metrics']` (score, threshold, decisão, timestamp) e logs estruturados.

2) Fallback compiler
- Definir o mapeamento 16→7 antes de escrever código.
- Garantir que o compilado final preencha um `StoryBrandAnalysis` válido e atualize `completeness_score`.

3) Inputs auxiliares
- Orquestrar a inclusão dos novos campos no Wizard e no extractor antes de depender deles no fallback.

---

## Referências
- Documentação ADK (composição de agentes, Sequential/Loop, custom agents): [https://google.github.io/adk-docs/](https://google.github.io/adk-docs/)

---

## Conclusão
As inconsistências destacadas na revisão procedem frente ao código atual. As sugestões são coerentes e, com os ajustes indicados (fonte correta do score, preservação do `PlanningOrRunSynth`, mapeamento 16→7 e sincronização de inputs/contrato de estado), o plano torna‑se implementável sem romper o fluxo existente.
