# Inconsistências na Implementação do Plano StoryBrand Fallback v2 (Codex CLI)

## 1. Coletor não realiza inferência suplementar nem log de erro padronizado
- **Local:** `app/agents/storybrand_fallback.py:102-148`
- **Problema:** O `fallback_input_collector_callback` apenas reaproveita valores existentes ou o JSON retornado pelo prompt. Ele não consulta `landing_page_context` para uma última inferência, nem registra o evento `{"stage": "collector", "status": "error", "details": "Pré-requisito crítico sexo_cliente_alvo não pôde ser determinado."}` antes de abortar, como exige a Seção 4 do plano.
- **Impacto:** O pipeline interrompe sem registrar diagnósticos completos, dificultando auditoria e desrespeitando o contrato da Seção 16.2.
- **Correção Sugerida:**
  1. Ler sinais suplementares de `landing_page_context` (pronomes, depoimentos) quando o gênero permanecer inválido.
  2. A registrar explicitamente o evento de erro no `storybrand_audit_trail` com a mensagem definida no plano.
  3. Lançar exceção com `EventActions(escalate=True)` após o registro, alinhando-se ao comportamento observado.

## 2. Loop de seções implementado manualmente
- **Local:** `app/agents/storybrand_fallback.py:192-338`
- **Problema:** O plano (Seção 6) prevê um `section_review_loop` reutilizável (`LoopAgent`) com agentes dedicados (`section_reviewer`, `approval_checker`, `section_corrector`). A implementação atual instancia e executa `LlmAgent`s inline, sem `LoopAgent` nem estágio `checker`.
- **Impacto:** Fica mais difícil controlar iterações, auditar estágios e reaproveitar lógica; também quebra o contrato de auditoria que cita o estágio `checker`.
- **Correção Sugerida:**
  1. Criar um `LoopAgent` nomeado `section_review_loop` com os subagentes descritos (revisor → checker → corrector) respeitando `config.fallback_storybrand_max_iterations`.
  2. Adaptar `StoryBrandSectionRunner` para acionar esse loop, mantendo registros de auditoria por estágio.

## 3. `StoryBrandSectionConfig` incompleto
- **Local:** `app/agents/storybrand_sections.py`
- **Problema:** A dataclass guarda apenas `state_key`, `prompt_name` e `narrative_goal`. O plano solicita `display_name`, caminhos explícitos para writer/corrector, e mapeamento de prompts de revisão por gênero.
- **Impacto:** Seções não conseguem carregar prompts diferenciados (writer/reviewer/corrector) sem recriar agentes dinamicamente, e o pipeline fica menos configurável.
- **Correção Sugerida:**
  1. Estender a dataclass com os campos listados no plano.
  2. Inicializar `StoryBrandSectionRunner` usando essas informações para montar agentes ou recuperar prompts via `PromptLoader`.

## 4. Trilha de auditoria incompleta
- **Local:** `app/agents/storybrand_fallback.py:217-334` e `app/agents/fallback_compiler.py:72-126`
- **Problema:** A Seção 16.2 exige eventos para `preparer`, `checker` e `compiler`. Atualmente são registrados somente `collector`, `writer`, `reviewer` e `corrector`. O compilador não adiciona nenhum evento antes/depois de executar.
- **Impacto:** Auditoria não cobre todas as etapas, dificultando monitoramento e violando o contrato acordado.
- **Correção Sugerida:**
  1. Inserir chamadas a `_append_audit_event` para `preparer` (antes de preparar contexto por seção) e `checker` (resultado do approval checker).
  2. No compilador, adicionar eventos `stage="compiler"` com status `started`/`completed` e detalhes da síntese.

## 5. Cobertura de testes insuficiente
- **Local:** `tests/unit/agents/test_storybrand_fallback.py` e suite geral
- **Problema:** Não existem testes que cubram `StoryBrandSectionRunner`, execução integrada do fallback com LLMs mocked, nem o caminho “force fallback” descrito na Seção 12 — apenas normalização, coleta e compilação isoladas são testadas.
- **Impacto:** Regressões no loop de seções ou na integração gate→fallback podem passar despercebidas.
- **Correção Sugerida:**
  1. Adicionar testes unitários para `StoryBrandSectionRunner`, validando iterações e auditoria.
  2. Criar teste de integração simulando `StoryBrandQualityGate` acionando o fallback com agentes fake.
  3. Exercitar cenário `force_storybrand_fallback=True` com score alto para garantir métricas corretas e pipeline coerente.

## 6. Checklist marcado como concluído prematuramente
- **Local:** `checklist.md:20-83`
- **Problema:** Itens 4–12 constam como `[x] done`, mas as implementações descritas ainda apresentam lacunas (itens 1–5 desta lista).
- **Impacto:** O controle operacional perde confiabilidade e tarefas pendentes podem ser ignoradas.
- **Correção Sugerida:** Revisar o checklist, reabrindo itens que exigem correção, e atualizar somente após validação completa.

---
Este relatório consolida as divergências observadas entre o plano oficial (`aprimoramento_plano_storybrand_v2.md`) e a implementação atual para priorização de correções.
