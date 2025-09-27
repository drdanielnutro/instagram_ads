### Inconsistência #1: Chaves das seções divergentes do compilador existente
**Severidade**: CRÍTICA
**Descrição**: O plano enumera as 16 seções do fallback usando chaves como `storybrand_exposition_1`, `storybrand_inciting_incident_1/2` e `storybrand_unmet_needs_summary`, mas o `FallbackStorybrandCompiler` lê `exposition_1`, `inciting_incident_1/2` e `unmet_needs_summary` (sem prefixo). Se implementado conforme o plano, os textos compilados ficariam vazios.
**Impacto**: Compromete completamente o StoryBrand reconstruído, produzindo análise sem dados para as etapas de exposição/inciting/unmet e quebrando o contrato consumido pelos agentes seguintes.
**Evidências**: Plano com a nomenclatura proposta; compilador atual buscando chaves sem prefixo.
**Referências**: 【F:aprimoramento_plano_storybrand_v2.md†L60-L69】【F:app/agents/fallback_compiler.py†L89-L108】
**Relação ADK**: A inconsistência viola o contrato de estado do `SequentialAgent` de fallback e impacta qualquer agente subsequente que consuma `ctx.session.state`.
**Correção Sugerida**: Ajustar o plano (e a futura configuração das seções) para usar exatamente as chaves esperadas pelo compilador (`exposition_1`, `inciting_incident_1`, `exposition_2`, `inciting_incident_2`, `unmet_needs_summary`).

### Inconsistência #2: Fallback não dispara o sintetizador de briefing
**Severidade**: CRÍTICA
**Descrição**: O gate proposto escolhe entre executar `PlanningOrRunSynth` ou o novo `fallback_storybrand_pipeline`. No caminho de fallback, `PlanningOrRunSynth` deixa de rodar, mas ele é responsável por gerar o `feature_briefing` que alimenta o planner e todos os agentes de execução.
**Impacto**: Sem briefing, `code_generator` e demais agentes recebem contexto vazio, travando a geração do anúncio e invalidando o pipeline.
**Evidências**: Seção 3 do plano descreve o roteamento exclusivo; `code_generator` exige `{feature_briefing}` na entrada.
**Referências**: 【F:aprimoramento_plano_storybrand_v2.md†L20-L27】【F:app/agent.py†L744-L818】
**Relação ADK**: Rompe o contrato de dados esperado pelo `SequentialAgent` principal, gerando exceções nos `LlmAgents` subsequentes.
**Correção Sugerida**: Após concluir o fallback, executar `PlanningOrRunSynth` (ao menos o `context_synthesizer`) antes de prosseguir para `execution_pipeline`, ou incorporar etapa equivalente no pipeline de fallback.

### Inconsistência #3: Validação de `VITE_ENABLE_NEW_FIELDS` fora do alcance do backend
**Severidade**: MÉDIA
**Descrição**: O plano exige confirmar `VITE_ENABLE_NEW_FIELDS` antes de permitir fallback forçado, mas o backend só consegue validar as flags `ENABLE_NEW_INPUT_FIELDS` e `ENABLE_STORYBRAND_FALLBACK`. Não há mecanismo atual para inspecionar a flag de frontend.
**Impacto**: Cria expectativa de proteção automática que o backend não pode garantir, podendo induzir erros operacionais.
**Evidências**: Plano cita a validação da flag de frontend; o preflight atual verifica apenas flags de backend e apenas instrui o operador a ajustar a flag do frontend via mensagem.
**Referências**: 【F:aprimoramento_plano_storybrand_v2.md†L56-L57】【F:app/server.py†L329-L356】
**Relação ADK**: Indiretamente afeta quando a sessão ADK é criada; o backend não tem visibilidade de configurações do frontend.
**Correção Sugerida**: Ajustar o plano para tratar essa checagem como processo operacional/documental ou introduzir mecanismo de configuração compartilhada; não pressupor validação automática dentro do backend.
