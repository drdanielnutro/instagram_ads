# Plano de Fallback StoryBrand — Versão Corrigida e Alinhada ao Código

## 1. Objetivos e Princípios
- **Garantir resiliência**: acionar reconstrução do StoryBrand quando a análise da landing page não atingir o limiar configurável.
- **Preservar eficiência**: manter o caminho atual (landing → planning/synth → execution) quando o score atender ao limiar.
- **Contrato de estado claro**: ambos os caminhos devem popular exatamente as mesmas chaves consumidas hoje (`storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context`), permitindo retomada transparente.
- **Observabilidade**: registrar decisões do gate, iterações do fallback e resultados para tuning e auditoria.

## 2. Pontos de Integração no `app/agent.py`
- Inserir o `StoryBrandQualityGate` imediatamente após `landing_page_analyzer` dentro de `complete_pipeline`.
- No caminho “feliz”, o gate deve invocar a instância existente de `PlanningOrRunSynth` (e não `planning_pipeline` diretamente), preservando o modo `planning_mode == "fixed"` quando aplicável.
- No caminho de “fallback”, o gate deve invocar o novo `fallback_storybrand_pipeline`.
- Respeitar `config.min_storybrand_completeness` (com override por ambiente) e uma flag `ENABLE_STORYBRAND_FALLBACK` para condicionar a inclusão do gate no pipeline.

## 3. StoryBrandQualityGate (BaseAgent customizado)
- **Local**: implementar no módulo existente `app/agent.py` para reduzir difusão de mudanças. (Opcional: modularizar criando `app/agents/` com `__init__.py` e ajustar imports.)
- **Lógica do `_run_async_impl`**:
  - Ler o score primariamente de `ctx.session.state['storybrand_analysis']['completeness_score']`.
  - Fallback de leitura: `ctx.session.state['landing_page_context']['storybrand_completeness']` (quando presente).
  - Se score estiver ausente/ inválido, acionar o fallback por segurança.
  - Comparar com `config.min_storybrand_completeness` e registrar a decisão em `state['storybrand_gate_metrics']` (campos: `score`, `threshold`, `path`, `timestamp`).
  - Caminho “feliz”: `async for ev in planning_or_run_synth.run_async(ctx): yield ev`.
  - Caminho “fallback”: `async for ev in fallback_storybrand_pipeline.run_async(ctx): yield ev`.
  - Registrar logs estruturados (`logger.info`) para auditoria.

## 4. Fallback StoryBrand Pipeline (SequentialAgent)
- **Local**: `app/agent.py` (ou `app/agents/storybrand_fallback.py` se optar por modularizar).
- **Sub-agentes**:
  1) `fallback_input_initializer` (BaseAgent): garantir que chaves opcionais existam no estado (strings vazias ou defaults), sem bloquear o fluxo.
  2) `fallback_input_collector` (LlmAgent, opcional): tentar preencher `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo` a partir de `landing_page_context`; não inferir “persona”/“tom” além do contexto factual. Tratá-los como opcionais até frontend/extractor suportarem.
  3) `section_pipeline_runner` (BaseAgent): executar, seção a seção, o bloco (preparador de contexto → escritor da seção → loop de revisão compartilhado).
  4) `fallback_storybrand_compiler` (BaseAgent recomendado; LlmAgent opcional): consolidar seções no schema `StoryBrandAnalysis` e popular o contrato de estado.
  5) `fallback_quality_reporter` (BaseAgent, opcional): agregar métricas/itens do loop e salvar em `state['storybrand_recovery']`.

## 5. Mapeamento das Seções para o Schema `StoryBrandAnalysis`
> O compilador deve aplicar este mapeamento determinístico ao instanciar `StoryBrandAnalysis` (Pydantic) antes do `.model_dump()`:
- `character.description` ← seção `character` (descrição do cliente ideal)
- `problem.types.external` ← seção `problem` (parte: problema externo)
- `problem.types.internal` ← seção `problem` (parte: problema interno)
- `problem.types.philosophical` ← seção `problem` (parte: problema filosófico)
- `problem.description` ← concatenação coerente dos tipos presentes
- `guide.authority` / `guide.empathy` / `guide.description` ← seção `guide`
- `plan.steps` / `plan.description` ← seção `plan` (até 3 passos principais)
- `action.primary` / `action.secondary` ← seção `action`
- `failure.description` / `failure.consequences` ← seção `failure`
- `success.transformation` / `success.benefits` ← seção `success`
- `metadata` ← pode incluir `identity` (seção extra) e outros metadados derivados

Observação: a seção `identity` é opcional e não mapeia diretamente ao schema; use-a para enriquecer `guide.description`, `success.transformation` ou `metadata` sem quebrar o contrato.

## 6. Loop de Revisão Compartilhado (LoopAgent)
- Componentes:
  - `section_reviewer` (LlmAgent): produz `{ "grade": "pass|fail", "comment": "..." }` com critérios claros; usar prompt parametrizado (ex.: gênero) apenas se definido.
  - `approval_checker` (BaseAgent): quando `grade == "pass"`, aciona `actions.escalate=True` para encerrar o loop daquela seção.
  - `section_corrector` (LlmAgent): aplica correções baseadas no `comment` sobrescrevendo o estado da seção atual.
- Parâmetros:
  - Máximo de iterações: `config.fallback_storybrand_max_iterations` (default 3; override via `FALLBACK_STORYBRAND_MAX_ITERATIONS`).
  - Logar por iteração: nome da seção, `grade`, resumo do `comment`.

## 7. Prompts (diretório sugerido `prompts/storybrand_fallback/`)
- `collector.txt` — instruções para levantar dados faltantes (JSON estruturado; sem invenções; usar apenas o que está em `landing_page_context`).
- `section_<nome>.txt` — oito prompts (character, problem, guide, plan, action, failure, success, identity) com estrutura e exemplos.
- `review_*.txt` — checklists de revisão (coerência, clareza, ancoragem no conteúdo real, tom e CTA adequados).
- `corrector.txt` — reescrita orientada por feedback.
- `compiler.txt` (se LLM): instruções para consolidar seções no schema; preferir BaseAgent determinístico quando possível.

## 8. Inputs Opcionais e Fontes
- Fonte principal para o fallback: `state['landing_page_context']` (já produzido pelo `landing_page_analyzer` + callback StoryBrand).
- Campos opcionais: `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`. Somente utilizar se presentes; caso contrário, seguir com o conteúdo factual da landing.
- Coordenação futura:
  - Backend (`helpers/user_extract_data.py`) e Wizard (`frontend/src/...`) devem ser atualizados antes de tornar esses campos mandatórios.

## 9. Contrato de Estado Pós-Fallback (obrigatório)
Ao final do `fallback_storybrand_compiler`, garantir:
- `state['storybrand_analysis']` — instância válida de `StoryBrandAnalysis` (Pydantic), com `completeness_score >= config.min_storybrand_completeness` (padrão conservador: 1.0).
- `state['storybrand_summary']` — texto de `StoryBrandAnalysis.to_summary()`.
- `state['storybrand_ad_context']` — dict de `StoryBrandAnalysis.to_ad_context()`.
- `state['landing_page_context']['storybrand_completeness']` — sincronizar com o `completeness_score` final.
- (Opcional) `state['storybrand_recovery']` — `{ status, sections, iterations }`.

Nota: não depender de `state['storybrand_completeness']` na raiz; leitores atuais usam `storybrand_analysis.completeness_score` e/ou `landing_page_context.storybrand_completeness`.

## 10. Ajustes em `app/config.py`
- Adicionar:
  - `fallback_storybrand_max_iterations: int = 3`
  - `fallback_storybrand_model: str | None = None`
  - `storybrand_gate_debug: bool = False`
  - `ENABLE_STORYBRAND_FALLBACK: bool = True`
- Manter `min_storybrand_completeness: float` como fonte única do limiar.

## 11. Logs, Métricas e Auditoria
- Gate: salvar `state['storybrand_gate_metrics'] = { score, threshold, path, timestamp }` e logar a decisão.
- Fallback: logar início/fim por seção, iterações e principais comentários de revisão.
- `state['storybrand_audit_trail']`: lista ordenada de eventos para depuração.

## 12. Testes e Validação
- Unitários:
  - Gate com scores acima/abaixo/ausentes (mocks dos pipelines chamados).
  - Carregamento e validação da configuração das seções.
  - Funções de compilação que instanciam `StoryBrandAnalysis` com mapeamento 5.
- Integração:
  - Execução completa do fallback com `LlmAgent`s mockados; verificar contrato de estado final.
  - Garantir que o caminho “feliz” permanece funcional (com `PlanningOrRunSynth`).
- QA manual:
  - Forçar score baixo e observar logs/estado resultante.

## 13. Documentação
- Atualizar `AGENTS.md` com o gate e o pipeline de fallback.
- Criar/atualizar `docs/storybrand_fallback.md` com fluxo real e contrato de estado.
- Usar o `checklist.md` existente para controlar implementação (evitar divergências de diretório).

## 14. Feature Flag
- Introduzir `ENABLE_STORYBRAND_FALLBACK` (default `True`).
- Condicionar a inclusão do gate e do pipeline ao valor da flag ao construir o `complete_pipeline`.

## 15. Considerações Finais
- Evitar modificar contratos já consumidos pelos agentes (`storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context`).
- Não depender de chaves inexistentes como `state['landing_page_analysis']` ou `state['storybrand_completeness_score']`.
- Preservar a arquitetura atual (Loops, `PlanningOrRunSynth`) e adicionar fallback de forma incremental e observável.
