# Revisão do Plano de Fallback — Storybrand

## 1. Sumário Executivo
- O plano posiciona corretamente o `StoryBrandQualityGate` logo após o `landing_page_analyzer`, reutilizando o `PlanningOrRunSynth` existente e o limiar já exposto em `config.min_storybrand_completeness`, preservando o fluxo feliz quando o score é suficiente.【F:aprimoramento_plano_storybrand_v2.md†L10-L27】【F:app/agent.py†L1221-L1228】【F:app/config.py†L34-L58】
- Há conflitos importantes na Seção 3 sobre quando o fallback pode ser forçado: o texto exige as duas flags ativas e, ao mesmo tempo, autoriza `state['force_storybrand_fallback']`/`config.storybrand_gate_debug` a ignorarem essa regra, o que pode acionar o pipeline sem os dados obrigatórios.【F:aprimoramento_plano_storybrand_v2.md†L22-L26】【F:app/server.py†L302-L356】
- A lista das 16 seções do fallback não usa os nomes `storybrand_*` consumidos pelo compilador existente, o que quebraria a etapa final caso fosse implementada literalmente.【F:aprimoramento_plano_storybrand_v2.md†L44-L48】【F:app/agents/fallback_compiler.py†L90-L218】

## 2. Itens Corretos e Consistentes
- **Gate após a análise da landing page** — Inserir o `StoryBrandQualityGate` logo depois do `landing_page_analyzer`, reaproveitando o `PlanningOrRunSynth` e o limiar `config.min_storybrand_completeness`, mantém o encadeamento atual e concentra a decisão de rota em um único agente.【F:aprimoramento_plano_storybrand_v2.md†L10-L27】【F:app/agent.py†L1221-L1228】【F:app/config.py†L34-L58】  
  - Evidências no código: `complete_pipeline` encadeia analisador → planejador, e o objeto de configuração já expõe o limiar utilizado hoje.
- **Contrato 16→7 alinhado ao compilador existente** — As regras descritas para transformar as 16 seções em `StoryBrandAnalysis` coincidem com o que `FallbackStorybrandCompiler` já executa, inclusive a sincronização do `storybrand_completeness` para 1.0 no estado da landing page.【F:aprimoramento_plano_storybrand_v2.md†L29-L38】【F:app/agents/fallback_compiler.py†L90-L220】  
  - Evidências no código: o compilador lê as mesmas chaves (`storybrand_*`, `exposition_*`) e popula `storybrand_analysis`, `storybrand_summary` e `storybrand_ad_context` com score final 1.0.
- **Pré-condições de dados coerentes com o backend atual** — A exigência de que preflight/backend/front validem `nome_empresa`, `o_que_a_empresa_faz` e `sexo_cliente_alvo` antes de liberar a sessão já está coberta pelo `UserInputExtractor` e pelo `/run_preflight`, garantindo que o fallback só execute com dados válidos quando as flags estiverem ativas.【F:aprimoramento_plano_storybrand_v2.md†L51-L56】【F:helpers/user_extract_data.py†L423-L599】【F:app/server.py†L302-L356】  
  - Evidências no código: o helper enriquece e valida os campos, e o servidor propaga `force_storybrand_fallback` apenas quando as duas flags relevantes estão habilitadas.

## 3. Inconsistências Encontradas
- **Regras conflitantes para forçar o fallback** — A Seção 3 afirma que o gate só considera o fallback quando `enable_storybrand_fallback` **e** `enable_new_input_fields` estão `True`, mas logo abaixo diz que `state['force_storybrand_fallback']` ou `config.storybrand_gate_debug` devem acionar o fallback imediatamente.  
  - Impacto: ALTA — permitir bypass sem os campos obrigatórios pode disparar o pipeline com estado incompleto, contrariando as validações do preflight e introduzindo falhas difíceis de depurar.  
  - Evidências: plano ambíguo nas linhas 22–26; servidor hoje bloqueia `force_storybrand_fallback` quando as flags não estão ativas, demonstrando a preocupação com esse cenário.【F:aprimoramento_plano_storybrand_v2.md†L22-L26】【F:app/server.py†L302-L356】  
  - Relação com ADK: afeta a decisão do `BaseAgent` gate e o contrato de estado compartilhado (`ctx.session.state`).  
  - **Correção Sugerida**: explicitar que `storybrand_gate_debug` só deve pular o score quando ambas as flags estiverem ativas (ou documentar claramente a exceção e como inicializar os campos faltantes) e que `state['force_storybrand_fallback']` é ignorado quando qualquer flag estiver `False`.
- **Lista de seções sem o prefixo `storybrand_`** — A Seção 5 sugere chaves como `character`, `plan` e `identity`, porém o compilador existente espera `storybrand_character`, `storybrand_plan`, `storybrand_identity` etc.  
  - Impacto: CRÍTICA — se implementado literalmente, o compilador gerará elementos vazios, quebrando o contrato do fallback.  
  - Evidências: plano lista nomes genéricos; `FallbackStorybrandCompiler` lê explicitamente `storybrand_*` e `exposition_*` para montar o `StoryBrandAnalysis`.【F:aprimoramento_plano_storybrand_v2.md†L44-L48】【F:app/agents/fallback_compiler.py†L90-L218】  
  - Relação com ADK: o `SequentialAgent` de fallback e seu compilador dependerão dessas chaves para manter o estado consistente.  
  - **Correção Sugerida**: atualizar a tabela de seções para usar as mesmas chaves com prefixo (`storybrand_character`, `storybrand_problem_external`, etc.) e alinhar os prompts/loop à nomenclatura já usada pelo compilador.
- **Aborto do pipeline sem mecanismo definido** — A Seção 4 determina que o `fallback_input_collector` deve “abortar o pipeline imediatamente” quando não conseguir normalizar `sexo_cliente_alvo`, mas não especifica como interromper um `SequentialAgent` no ADK.  
  - Impacto: MÉDIA — sem indicar o uso de `EventActions(escalate=True)` ou exceções, a implementação pode apenas logar o erro e seguir para as próximas etapas, deixando o estado inconsistente.  
  - Evidências: plano linha 46–47; o código existente usa `EventActions(escalate=True)` para romper loops/controlar fluxos (ex.: `EscalationChecker`, `TaskCompletionChecker`).【F:aprimoramento_plano_storybrand_v2.md†L45-L47】【F:app/agent.py†L200-L235】  
  - Relação com ADK: depende do mecanismo de escalada de eventos no `SequentialAgent`.  
  - **Correção Sugerida**: instruir explicitamente o uso de `Event(actions=EventActions(escalate=True))` (ou lançamento de exceção) para encerrar o pipeline em caso de pré-requisito não atendido.
- **Campo de configuração já existente** — A Seção 10 lista `storybrand_gate_debug` como adição necessária, mas o atributo já está definido em `DevelopmentConfiguration`, o que gera instruções redundantes.  
  - Impacto: BAIXA — pode causar retrabalho desnecessário ou dúvidas sobre renomeação.  
  - Evidências: plano linhas 108–110; configuração atual já inclui o campo com override por `STORYBRAND_GATE_DEBUG`.【F:aprimoramento_plano_storybrand_v2.md†L108-L110】【F:app/config.py†L34-L40】  
  - Relação com ADK: nenhuma direta.  
  - **Correção Sugerida**: ajustar o plano para reconhecer que o campo existe e focar em documentar/testar seu uso em vez de recriá-lo.

## 4. Pontos de Incerteza
- O plano pressupõe que `landing_page_context` terá sinais suficientes (pronomes/personas) para uma inferência final de `sexo_cliente_alvo`, mas não apresenta critérios objetivos nem confirmações no código atual — é necessário definir fontes mínimas ou fallback seguro para essa heurística.【F:aprimoramento_plano_storybrand_v2.md†L45-L47】【F:app/callbacks/landing_page_callbacks.py†L41-L159】
- Não está claro qual modelo deve ser usado quando `config.fallback_storybrand_model` estiver `None`: reutilizar `worker_model` ou permitir configuração por agente? O plano não define prioridade ou fallback, deixando a decisão aberta.【F:aprimoramento_plano_storybrand_v2.md†L104-L110】【F:app/config.py†L34-L58】

## 5. Viabilidade de Implementação (por tema)
- **Integração do gate no pipeline** — Viável; basta substituir o `PlanningOrRunSynth` na lista de `sub_agents` por um gate que, quando autorizado pelas flags, encaminhe para o planejador ou para o fallback. O pipeline atual já compartilha estado via `ctx.session.state` e tem exemplos de agentes de controle.【F:aprimoramento_plano_storybrand_v2.md†L10-L27】【F:app/agent.py†L200-L235】【F:app/agent.py†L1221-L1228】
- **Pipeline de fallback e compilador** — Parcialmente implementado: o compilador existe e segue o contrato 16→7, restando criar initializer/collector/loops. A viabilidade depende de alinhar a nomenclatura das seções e definir claramente os mecanismos de interrupção/logs sugeridos.【F:aprimoramento_plano_storybrand_v2.md†L38-L111】【F:app/agents/fallback_compiler.py†L90-L220】
- **Coleta e enriquecimento de inputs** — Já suportada pelo backend/frontend sempre que as flags estiverem ativas; o esforço principal será reutilizar esses valores no fallback e garantir métricas/audit trail conforme descrito.【F:aprimoramento_plano_storybrand_v2.md†L51-L107】【F:helpers/user_extract_data.py†L423-L599】【F:app/server.py†L302-L356】
- **Observabilidade e métricas** — O plano descreve contratos detalhados (`storybrand_gate_metrics`, `storybrand_audit_trail`); o código ainda não os implementa, mas há infraestrutura de logging estruturado no preflight que pode ser replicada, mantendo compatibilidade com o ADK.【F:aprimoramento_plano_storybrand_v2.md†L112-L189】【F:app/server.py†L205-L356】
