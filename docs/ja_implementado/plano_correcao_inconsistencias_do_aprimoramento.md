# Plano de Correção das Inconsistências do Plano StoryBrand Fallback v2

Este documento lista exclusivamente as pendências identificadas na revisão (`inconsistencias_implementacao_codex_cloud_1.md`) e detalha as ações corretivas necessárias. Use-o em conjunto com `checklist_correcao_inconsistencias.md`.

## 3. StoryBrandQualityGate
### 3.2 Ajustar `storybrand_gate_metrics` ao contrato
- **Status atual:** Inconsistência: contrato de dados violado
- **Problema observado:** O dicionário salvo em `state['storybrand_gate_metrics']` dentro de `StoryBrandQualityGate` inclui as chaves `force_flag_active`, `fallback_enabled` e `block_reason`, que não fazem parte do contrato definido na Seção 16.1 do plano.
- **Arquivos envolvidos:** app/agents/storybrand_gate.py
- **Ações necessárias:**
  - Editar o método `_run_async_impl` da classe `StoryBrandQualityGate` para que `metrics` contenha apenas `score_obtained`, `score_threshold`, `decision_path`, `timestamp_utc`, `is_forced_fallback` e `debug_flag_active` antes de ser atribuído a `state['storybrand_gate_metrics']`.
  - Remover ou mover para outro registro as chaves adicionais (`force_flag_active`, `fallback_enabled`, `block_reason`). Se forem mantidas, salvar em uma chave separada (ex.: `state['storybrand_gate_debug']`).
  - Manter o log estruturado (`logger.info`) com as chaves úteis, mesmo que algumas não estejam mais em `storybrand_gate_metrics`.

## 4. Fallback StoryBrand Pipeline
### 4.3 Completar lógica do `fallback_input_collector`
- **Status atual:** Inconsistência: coleta incompleta
- **Problema observado:** `fallback_input_collector_callback` apenas valida os valores atuais ou retornados pelo LLM. Não tenta inferir `sexo_cliente_alvo` usando `landing_page_context`, nem registra o erro padronizado antes de abortar.
- **Arquivos envolvidos:** app/agents/storybrand_fallback.py
- **Ações necessárias:**
  - Dentro de `fallback_input_collector_callback`, quando `sexo_cliente_alvo` permanecer inválido, analisar `state['landing_page_context']` (pronomes, depoimentos) para tentar inferir o gênero.
  - Caso continue indefinido, registrar no audit trail um evento de erro com detalhes sobre os campos ausentes e interromper a execução levantando exceção com `EventActions(escalate=True)`.
  - Documentar no estado (ex.: em `storybrand_audit_trail`) quais campos foram enriquecidos pelo coletor para facilitar auditoria.

## 5. Configuração das Seções
### 5.1/5.2 Expandir `StoryBrandSectionConfig` e mapeamento de prompts
- **Status atual:** Inconsistência: configuração insuficiente
- **Problema observado:** A dataclass `StoryBrandSectionConfig` só possui `state_key`, `prompt_name` e `narrative_goal`. O plano exige que cada seção traga também display name e caminhos explícitos para prompts de escrita, revisão (por gênero) e correção.
- **Arquivos envolvidos:** app/agents/storybrand_sections.py, app/agents/storybrand_fallback.py
- **Ações necessárias:**
  - Adicionar aos campos da dataclass: `display_name`, `writer_prompt_path`, `review_prompt_paths: dict[str, str]`, `corrector_prompt_path` (e outros que façam sentido, como `narrative_goal`).
  - Atualizar `build_storybrand_section_configs()` para preencher os novos campos apontando para arquivos sob `prompts/storybrand_fallback/`.
  - Modificar `StoryBrandSectionRunner` para usar esses caminhos diretamente ao montar `LlmAgent`s, eliminando o uso de `section.prompt_name`.

## 6. Loop de Revisão Compartilhado
### 6.1/6.2 Reintroduzir `LoopAgent` no fluxo de revisão
- **Status atual:** Inconsistência: arquitetura desviada
- **Problema observado:** O pipeline hoje usa um laço manual (`for iteration in ...`) para controlar writer, reviewer e corrector, em vez do `LoopAgent` com `approval_checker` descrito no plano.
- **Arquivos envolvidos:** app/agents/storybrand_fallback.py
- **Ações necessárias:**
  - Criar um `LoopAgent` (ex.: `section_review_loop`) configurado com os subagentes `section_reviewer`, `approval_checker` (EscalationChecker) e `section_corrector`.
  - Instanciar esses subagentes utilizando os caminhos de prompt vindos de `StoryBrandSectionConfig`.
  - Dentro de `StoryBrandSectionRunner._run_section`, substituir o laço manual por uma chamada a esse `LoopAgent`, garantindo que os estágios `reviewer`, `checker` e `corrector` apareçam na trilha de auditoria.

## 11. Logs e Observabilidade
### 11.1 Emitir logs estruturados no fallback
- **Status atual:** Inconsistência: ausência de logs externos
- **Problema observado:** O gate usa `logger.info`, mas o fallback só atualiza `storybrand_audit_trail`. Não há logs estruturados para monitorar seções/iterações.
- **Arquivos envolvidos:** app/agents/storybrand_fallback.py
- **Ações necessárias:**
  - Adicionar chamadas de logging (`logger.info('storybrand_fallback_section', extra={...})`) ao iniciar cada seção, após revisão e ao finalizar a compilação.
  - Padronizar as chaves (`section_key`, `iteration`, `status`, etc.) de forma semelhante ao que já é logado pelo gate.

### 11.2 Completar o contrato de `storybrand_audit_trail`
- **Status atual:** Inconsistência: eventos faltando
- **Problema observado:** A trilha registra apenas `collector`, `writer`, `reviewer`, `corrector`. Faltam eventos `preparer`, `checker` e `compiler`, conforme a Seção 16.2.
- **Arquivos envolvidos:** app/agents/storybrand_fallback.py, app/agents/fallback_compiler.py
- **Ações necessárias:**
  - Registrar um evento `preparer` antes de montar o contexto da seção, `checker` após a decisão do approval checker e `compiler` na entrada/saída do compilador.
  - Sempre que possível, preencher `duration_ms` para estágios concluídos (ex.: usando timestamps antes/depois da execução).

## 13. Documentação
### 13.3 Atualizar documentação sobre campos obrigatórios
- **Status atual:** Inconsistência: documentação desatualizada
- **Problema observado:** README (e possivelmente docs associados) ainda tratam `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo` como opcionais e aceitam `neutro`.
- **Arquivos envolvidos:** README.md, docs/storybrand_fallback.md
- **Ações necessárias:**
  - Editar a seção de inputs no README para refletir que os campos são obrigatórios com as flags ativas e que `sexo_cliente_alvo` deve ser `masculino` ou `feminino`.
  - Revisar `docs/storybrand_fallback.md` e quaisquer outros documentos para alinhar a terminologia.
