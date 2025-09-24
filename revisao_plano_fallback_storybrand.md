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
- [Resolvido] **Leitura de `state['storybrand_completeness_score']`** — O plano foi ajustado para usar `state['storybrand_analysis']['completeness_score']` com fallback para `state['landing_page_context']['storybrand_completeness']`, exatamente como o callback `process_and_extract_sb7` já produz (`app/callbacks/landing_page_callbacks.py:111-134`).
- [Resolvido] **Ignorar o agente `PlanningOrRunSynth`** — O documento agora orienta o gate a receber o próprio `PlanningOrRunSynth` como dependência e a reutilizar `run_async`, preservando a lógica existente (`aprimoramento_plano_storybrand_v2.md:13-24`; `app/agent.py:260-278`).
- [Resolvido] **Estrutura inexistente `app/agents/...`** — O pacote `app/agents/` foi criado e contém o `FallbackStorybrandCompiler`, viabilizando a organização proposta e mantendo os imports válidos (`app/agents/__init__.py:1-5`; `app/agents/fallback_compiler.py:1-214`).
- [Resolvido] **Uso da chave `state['landing_page_analysis']`** — As referências do plano passaram a apontar para `landing_page_context`, alinhadas ao que o `landing_page_analyzer` já persiste (`app/agent.py:626-687`; `aprimoramento_plano_storybrand_v2.md:6-24`).
- [Resolvido] **Mapeamento das 16 seções para `StoryBrandAnalysis`** — Implementado via `FallbackStorybrandCompiler` (`app/agents/fallback_compiler.py`). O compilador:
  - Sintetiza `problem.description` a partir de `exposition_*`, `inciting_*`, `unmet_needs_summary` e usa `problem_external/internal/philosophical` em `problem.types` e `evidence`.
  - Define `guide.description` priorizando `value_proposition` e agrega autoridade do `guide`; preenche `plan.steps` e CTAs a partir de `plan` e `action`.
  - Preenche `evidence`/`confidence` básicos, `success.benefits/transformation` e `metadata.text_length`.
  - Persiste `storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context` e sincroniza `landing_page_context.storybrand_completeness = 1.0`.
- [Resolvido] **Definir `state['storybrand_completeness'] = 1.0` como garantia** — O compilador atualiza `storybrand_analysis['completeness_score'] = 1.0` e sincroniza `landing_page_context['storybrand_completeness'] = 1.0`, evitando loops desnecessários (`app/agents/fallback_compiler.py:200-214`).
- [Resolvido] **Novos campos (`nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`) alinhados com frontend/back-end** — Wizard, extractor e preflight já persistem essas chaves com normalização e defaults.
- **Checklist e documentação em caminhos divergentes** — O plano prevê `checklists/storybrand_fallback.md`, mas o processo atual documentado em `AGENTS.md` exige atualizar `checklist.md` na raiz.
  - Impacto: risco de equipes seguirem checklists diferentes ou ignorarem o fluxo “Checklist Primeiro, Código Depois”.
  - **Correção Sugerida**: alinhar com o fluxo vigente (atualizar `checklist.md` ou documentar claramente como o novo arquivo se integra ao processo oficial).

## 4. Pontos de Incerteza
- Mapeamento detalhado das 16 seções narrativas para os campos do `StoryBrandAnalysis` (quais atributos alimentam `guide.authority`, `plan.steps`, `metadata`).
- Vocabulário esperado para `sexo_cliente_alvo` (masculino/feminino/apresentação neutra?) e implicações de prompt nos revisores.
- Necessidade de versionar ou auditar StoryBrands antigos antes que o fallback sobrescreva `storybrand_analysis` (não há requisito explícito).

## 5. Viabilidade de Implementação (por tema)
- **Seção 1 — Objetivos e Princípios**: Viável após corrigir a leitura do score; limiar e chaves já existem.
- **Seção 2 — Pontos de Integração em `agent.py`**: Viável; o plano já prevê o gate reutilizando `PlanningOrRunSynth`, restando apenas implementar a classe no módulo escolhido (`app/agent.py` ou `app/agents/storybrand_gate.py`).
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
