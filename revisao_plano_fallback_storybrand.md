# Revisão do Plano de Fallback — Storybrand

## 1. Sumário Executivo
- O plano propõe corretamente posicionar um gate de qualidade após o `landing_page_analyzer`, reutilizando o limiar centralizado em `config.min_storybrand_completeness` e preservando as chaves já consumidas pelos agentes subsequentes. Porém, vários detalhes operacionais se apoiam em chaves de estado inexistentes (`storybrand_completeness_score`, `landing_page_analysis`) ou ignoram componentes consolidados (`PlanningOrRunSynth`).
- [Resolvido] A estrutura sugerida para o fallback (16 seções com prompts dedicados) carecia de mapeamento 16→7. Implementamos o `FallbackStorybrandCompiler` em `app/agents/fallback_compiler.py`, que compila as 16 seções no schema `StoryBrandAnalysis` com `completeness_score=1.0` e sincroniza `landing_page_context.storybrand_completeness`.
- Há dependências cruzadas não tratadas: novos campos exigem mudanças coordenadas no frontend e no extractor backend, diretórios indicados não existem e o plano de documentação/checklists diverge do processo atual descrito em `AGENTS.md`.

### Atualizações Implementadas
- Novo pacote: `app/agents/`.
- Novo agente: `FallbackStorybrandCompiler` com mapeamento 16→7 (gera `storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context`).
- Nenhuma alteração de pipeline ainda: o agente não está conectado; fluxo atual permanece inalterado.

## 2. Itens Corretos e Consistentes
- **Uso do limiar de qualidade já exposto em `config.min_storybrand_completeness`** — A leitura direta da configuração mantém a coerência com `DevelopmentConfiguration` (`app/config.py`, linhas 34-71) e permite override por ambiente. Isso garante que o fallback seja acionado com o mesmo parâmetro usado hoje para validar a análise inicial.
  - Evidências no código: `DevelopmentConfiguration.min_storybrand_completeness` em `app/config.py`.
- **Manter o contrato de estado (`storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context`)** — O plano reforça que o fallback deve popular as mesmas chaves já persistidas pelo callback `process_and_extract_sb7` (`app/callbacks/landing_page_callbacks.py`, linhas 108-155) e consumidas por agentes como `context_synthesizer` (`app/agent.py`, linhas 697-744). Isso garante compatibilidade com o pipeline atual.
  - Evidências no código: escrita das chaves em `process_and_extract_sb7`; uso em `context_synthesizer`.
- **Inserir o gate logo após o `landing_page_analyzer`** — A proposta preserva o fluxo do `complete_pipeline` (`app/agent.py`, linhas 1208-1235), onde a análise da landing page deve preceder a decisão de planejar ou sintetizar. O posicionamento mantém o encadeamento de agentes já estabelecido.
  - Evidências no código: definição do `complete_pipeline` com `landing_page_analyzer` seguido de `PlanningOrRunSynth`.
- **Adoção de LoopAgent para revisão iterativa** — A ideia de reaproveitar um loop de revisão compartilhado está alinhada com o padrão já implementado (`plan_review_loop`, `code_review_loop`, `task_execution_loop` em `app/agent.py`, linhas 1133-1200). Criar prompts específicos sem alterar o mecanismo de loop respeita a infraestrutura existente.
  - Evidências no código: definição dos loops com `LoopAgent` em `app/agent.py`.

## 3. Inconsistências Encontradas
- **Leitura de `state['storybrand_completeness_score']`** — A chave não é produzida em nenhum ponto. O callback `process_and_extract_sb7` grava o score como `analysis.completeness_score` dentro de `storybrand_analysis` e duplica o valor em `storybrand_completeness` dentro de `landing_page_context`; não há `storybrand_completeness_score` na raiz do estado.
  - Impacto: o gate jamais encontraria o score e acionaria o fallback em 100% das execuções.
  - Evidências no código: `app/callbacks/landing_page_callbacks.py`, linhas 108-155; `app/agent.py`, linhas 662-678.
  - Relação com ADK: `InvocationContext.session.state` retorna `dict`; acessar uma chave inexistente levanta `KeyError` ou retorna `None`, comprometendo o roteamento.
  - **Correção Sugerida**: ler `score = ctx.session.state.get('storybrand_analysis', {}).get('completeness_score')` e, se ausente, reutilizar `ctx.session.state.get('landing_page_context', {}).get('storybrand_completeness')` antes de forçar o fallback.
- **Ignorar o agente `PlanningOrRunSynth`** — O plano sugere que o gate invoque diretamente `planning_pipeline`, mas o `complete_pipeline` atual delega a decisão entre planejamento completo e apenas síntese ao agente `PlanningOrRunSynth` (`app/agent.py`, linhas 264-280 e 1221-1229).
  - Impacto: sessões com `planning_mode="fixed"` ou cenários onde apenas o sintetizador deveria rodar seriam encaminhadas para o pipeline errado.
  - Relação com ADK: `PlanningOrRunSynth` encapsula dois sub-agentes e já recebe o `InvocationContext`; removê-lo requer refatoração estrutural.
  - **Correção Sugerida**: injetar o próprio `PlanningOrRunSynth` no gate e reutilizar sua interface `run_async`, preservando o comportamento atual.
- **Estrutura inexistente `app/agents/...`** — Todos os agentes vivem hoje em `app/agent.py` e em subpacotes existentes (`app/callbacks`, `app/tools`). Não há diretório `app/agents` inicializado.
  - Impacto: imports quebrados até que o pacote seja criado e registrado.
  - **Correção Sugerida**: ou planejar a criação de `app/agents/__init__.py` com ajustes de import, ou definir explicitamente que novas classes ficarão em módulos existentes como `app/agent.py` ou um novo módulo registrado no pacote atual.
- **Uso da chave `state['landing_page_analysis']`** — O fallback propõe extrair dados dessa chave, mas o `landing_page_analyzer` salva o resultado em `landing_page_context` (`app/agent.py`, linhas 626-688). Não existe `landing_page_analysis` no estado.
  - Impacto: os inputs essenciais (`nome_empresa`, etc.) permaneceriam vazios mesmo quando a análise trouxe dados.
  - **Correção Sugerida**: ler de `landing_page_context` e documentar como derivar os campos necessários a partir das chaves existentes.
- [Resolvido] **Mapeamento das 16 seções para `StoryBrandAnalysis`** — Implementado via `FallbackStorybrandCompiler` (`app/agents/fallback_compiler.py`). O compilador:
  - Sintetiza `problem.description` a partir de `exposition_*`, `inciting_*`, `unmet_needs_summary` e usa `problem_external/internal/philosophical` em `problem.types` e `evidence`.
  - Define `guide.description` priorizando `value_proposition` e agrega autoridade do `guide`; preenche `plan.steps` e CTAs a partir de `plan` e `action`.
  - Preenche `evidence`/`confidence` básicos, `success.benefits/transformation` e `metadata.text_length`.
  - Persiste `storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context` e sincroniza `landing_page_context.storybrand_completeness = 1.0`.
- **Definir `state['storybrand_completeness'] = 1.0` como garantia** — Essa chave hoje só aparece dentro de `landing_page_context`; nenhum agente lê um valor na raiz do estado.
  - Impacto: falsa sensação de bloqueio de loops. Se o gate continuar usando o score de `storybrand_analysis`, o fallback pode ser reexecutado.
  - **Correção Sugerida**: atualizar `storybrand_analysis['completeness_score']` ao final da recompilação e, opcionalmente, sincronizar `landing_page_context['storybrand_completeness']`.
- **Novos campos (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`) sem alinhamento com frontend/back-end** — O wizard do frontend (`frontend/src/constants/wizard.constants.ts`) e o extractor (`helpers/user_extract_data.py`) não conhecem essas chaves.
  - Impacto: o fallback nunca receberá os dados prometidos; o initializer precisaria sempre preencher com strings vazias.
  - **Correção Sugerida**: detalhar as mudanças necessárias no wizard (estado inicial, validação, submissão) e na extração de dados, inclusive quais valores serão aceitos para `sexo_cliente_alvo`.
- **Checklist e documentação em caminhos divergentes** — O plano prevê `checklists/storybrand_fallback.md`, mas o processo atual documentado em `AGENTS.md` exige atualizar `checklist.md` na raiz.
  - Impacto: risco de equipes seguirem checklists diferentes ou ignorarem o fluxo “Checklist Primeiro, Código Depois”.
  - **Correção Sugerida**: alinhar com o fluxo vigente (atualizar `checklist.md` ou documentar claramente como o novo arquivo se integra ao processo oficial).

## 4. Pontos de Incerteza
- Mapeamento detalhado das 16 seções narrativas para os campos do `StoryBrandAnalysis` (quais atributos alimentam `guide.authority`, `plan.steps`, `metadata`).
- Vocabulário esperado para `sexo_cliente_alvo` (masculino/feminino/apresentação neutra?) e implicações de prompt nos revisores.
- Necessidade de versionar ou auditar StoryBrands antigos antes que o fallback sobrescreva `storybrand_analysis` (não há requisito explícito).

## 5. Viabilidade de Implementação (por tema)
- **Seção 1 — Objetivos e Princípios**: Viável após corrigir a leitura do score; limiar e chaves já existem.
- **Seção 2 — Pontos de Integração em `agent.py`**: Parcialmente viável. É necessário reutilizar `PlanningOrRunSynth` e definir onde viverá o novo agente (módulo existente ou pacote novo preparado).
- **Seção 3 — StoryBrandQualityGate**: Viável após corrigir as chaves do estado e definir a estrutura de logging (`storybrand_gate_metrics`).
- **Seção 4 — Fallback StoryBrand Pipeline**: Viável após corrigir a origem de dados para `landing_page_context` e com o compilador 16→7 já implementado. Continua dependendo da coleta dos novos campos no frontend/extractor quando o fallback for ativado.
- **Seção 5 — Configuração das Seções**: Parcialmente desbloqueada pelo mapeamento 16→7. Ainda requer catalogar nomes de chaves no estado e a lista final das 16 seções com seus prompts.
- **Seção 6 — Loop de Revisão Compartilhado**: Viável; já existem `LoopAgent`s no projeto, mas falta especificar onde armazenar resultados intermediários.
- **Seção 7 — Prompts Necessários**: Viável se o diretório for criado e houver estratégia de carregamento dos arquivos.
- **Seção 8 — Coleta de Inputs Essenciais**: Requer coordenação entre frontend e extractor; viável após definir dados opcionais e validações.
- **Seção 9 — Contrato de Estado Pós-Fallback**: Dependente do compilador produzir um `StoryBrandAnalysis` válido; ajustar apenas `storybrand_completeness` não basta.
- **Seção 10 — Ajustes em `app/config.py`**: Simples; basta acrescentar campos na configuração e documentar variáveis de ambiente.
- **Seção 11 — Logs e Observabilidade**: Viável, mas precisa definir formato de `storybrand_gate_metrics` e `storybrand_audit_trail` para facilitar análise posterior.
- **Seção 12 — Testes e Validação**: Viável com mocks dos novos agentes; falta plano para simular as respostas dos `LlmAgent` no fallback.
- **Seção 13 — Documentação**: Viável desde que alinhada ao processo atual (atualizar `AGENTS.md` e/ou `checklist.md` conforme o fluxo oficial).
- **Seção 14 — Feature Flag**: Viável; segue padrão de outras flags em `config` e pode condicionar a inclusão do gate.
- **Seção 15 — Etapas Futuras**: Conceitualmente válidas, mas dependem das métricas e do audit trail definidos nas seções anteriores.