# Checklist de Execução – StoryBrand como Etapa Primária

Use esta lista como roteiro operacional para aplicar o plano descrito em `plano_refatoracao_storybrand.md`. Todos os itens devem ser concluídos (ou explicitamente justificados) antes do rollout.

---

## Backend

### Estrutura de estado e utilitários
- [ ] Implementar `ensure_storybrand_meta(state)` inicializando a estrutura completa (`status`, `completed_at`, `fallback_engaged`, `quality_report`, `errors`, `bootstrap_attempts`, etc.).
- [ ] Garantir retrocompatibilidade preenchendo `fallback_engaged` junto com o novo `status`.

### `app/agent.py`
- [ ] Criar `storybrand_bootstrap_stage` (novo `SequentialAgent`) imediatamente após `input_processor`, com controle de `status="in_progress"`/`"completed"` e incremento de `bootstrap_attempts`.
- [ ] Atualizar `complete_pipeline.sub_agents` para `[input_processor, storybrand_bootstrap_stage, landing_page_stage, storybrand_quality_gate, execution_pipeline]`.
- [ ] Ao concluir o bootstrap, registrar `completed_at`, manter `fallback_engaged=True` e limpar `force_storybrand_fallback` somente quando `storybrand_gate_debug` estiver desligado.
- [ ] Ajustar `LandingPageStage._run_async_impl` para permitir análise oficial quando `status="completed"` (sem flags de força) e adicionar `landing_page_fetch_failed_after_fallback` em falhas posteriores.

### `app/agents/storybrand_gate.py`
- [ ] Garantir uso de `ensure_storybrand_meta` no início do método.
- [ ] Pular fallback quando `status="completed"` sem `force_storybrand_fallback`, registrando `decision_path="fallback_precompleted"`.
- [ ] Suportar reexecução (force/debug/erro), atualizando `status="in_progress"` e `completed_at` ao final.
- [ ] Registrar métricas novas (`bootstrap_attempts`, `status`) sem remover as antigas.

### `app/agents/storybrand_fallback.py` & `app/agents/fallback_compiler.py`
- [ ] Validar `REQUIRED_INPUT_KEYS` logo no início; em caso de ausência, marcar `status="failed"` e lançar erro controlado.
- [ ] Emitir evento SSE `storybrand.completed` com `event_type` explícito e `stateDelta` contendo `storybrand_fallback_meta.status="completed"`, `completed_at` e os artefatos StoryBrand.
- [ ] Garantir que o `FallbackQualityReporter` anexe `quality_report` preservando demais campos; remover flags temporárias ao finalizar.
- [ ] Emitir `storybrand.failed` (com detalhes no delta) quando ocorrer erro irrecuperável durante o bootstrap.

### Callbacks e persistência
- [ ] Em `landing_page_callbacks.py`, registrar `landing_page_fetch_failed_after_fallback=True` e detalhes em `storybrand_last_error` sem reativar fallback.
- [ ] Em `persist_outputs.py`, incluir no JSON final e no `meta.json` os novos campos (`status`, `completed_at`, `quality_report`, `bootstrap_attempts`, `landing_page_fetch_failed_after_fallback`).

### Preflight faseado
- [ ] Atualizar `UserInputExtractor` para aceitar `phase="storybrand"|"campaign"|"full"` com validações específicas por fase.
- [ ] Ajustar `/run_preflight` para ler `phase` do payload e retornar `initial_state` com `storybrand_inputs` e/ou `campaign_inputs`.
- [ ] Garantir que o `input_processor` combine os dois conjuntos quando ambos existirem.
- [ ] Adicionar logging específico (`storybrand_preflight_validation_error`) e tratamento de erros por fase.

### Resiliência
- [ ] Implementar timeout configurável para o bootstrap e tratamento de exceções que dispare `storybrand.failed`.
- [ ] Registrar logs estruturados: `storybrand_bootstrap_started`, `storybrand_bootstrap_completed`, `storybrand_bootstrap_failed`.

---

## Frontend

### Tipos, constantes e helpers
- [ ] Atualizar `frontend/src/types/wizard.types.ts` com `phase` e novos tipos de payload (`StorybrandPayload`, `CampaignPayload`).
- [ ] Revisar `frontend/src/constants/wizard.constants.ts` para definir `phase` por passo e exportar `getWizardStepsByPhase`.
- [ ] Implementar `splitWizardPayload` e ajustar `formatSubmitPayload` para lidar com fases distintas.

### Wizard e formulários
- [ ] Em `WizardForm`, exibir apenas passos `phase="storybrand"` inicialmente, bloqueando-os (readonly) após submissão e liberando os de campanha.
- [ ] Retornar `{ storybrandPayload, campaignPayload }` no `handleSubmit` e sinalizar conclusão da fase 1.
- [ ] Adicionar indicadores visuais (ex.: stepper com “História” e “Complemento”).
- [ ] Persistir dados por fase em `localStorage` (namespaced por sessão) para permitir retomada.

### `frontend/src/App.tsx`
- [ ] Criar estados `storybrandInputs`, `campaignInputs`, `pendingCampaignPayload`, `isStorybrandReady`, `storybrandError`.
- [ ] Executar `runPreflight` com `phase="storybrand"` na fase 1 e criar sessão usando apenas os campos StoryBrand.
- [ ] Processar `storybrand.completed` atualizando estados, liberando fase 2 e disparando envio automático se houver payload pendente.
- [ ] Validar fase 2 com `runPreflight(..., phase="campaign")` antes de enviar ao pipeline principal.
- [ ] Bloquear preview e ações dependentes até `isStorybrandReady` e envio da fase 2 estarem completos.
- [ ] Tratar `storybrand.failed` exibindo mensagem ao usuário, oferecendo retry/manual abort.

### SSE e monitoramento
- [ ] Atualizar `handleStreamEvent` para diferenciar `storybrand.completed`, `storybrand.failed` e outros eventos; ignorar duplicatas.
- [ ] Adicionar logs condicionais à flag `VITE_DEBUG_STORYBRAND`.
- [ ] Garantir que o fluxo legado (`VITE_ENABLE_WIZARD=false`) continue enviando payload único (`phase="full"`).

### UI adicional
- [ ] Em `WelcomeScreen`, mostrar loader “Gerando StoryBrand” e desabilitar ações até `isStorybrandReady`.
- [ ] Atualizar outros componentes que dependem de dados StoryBrand para ler do novo estado.

---

## Flags, Migração e Rollout
- [ ] Introduzir `ENABLE_STORYBRAND_BOOTSTRAP` (backend) e `STORYBRAND_BOOTSTRAP_ROLLOUT_PERCENTAGE` para rollout progressivo.
- [ ] Adicionar `VITE_DEBUG_STORYBRAND` (frontend) para logs adicionais durante QA.
- [ ] Detectar sessões legadas sem `storybrand_fallback_meta.status`, inicializando como `"unknown"` e permitindo fluxo antigo.
- [ ] Definir playbook de rollout gradual (ex.: 10% → 50% → 100%) com critérios de sucesso.
- [ ] Atualizar `README.md`, `AGENTS.md` e `storybrand_gcs.md` com o novo fluxo e flags.

---

## Testes Automatizados

### Backend
- [ ] `test_storybrand_bootstrap_runs_once` – garante execução única quando `status="pending"`.
- [ ] `test_storybrand_bootstrap_missing_fields` – valida falha controlada e `status="failed"`.
- [ ] `test_storybrand_gate_reuses_completed_storybrand` – gate pula fallback e registra `fallback_precompleted`.
- [ ] `test_storybrand_gate_force_flag` – reexecução com atualização de `completed_at`.
- [ ] `test_preflight_storybrand_phase` e `test_preflight_campaign_phase` – validações separadas.
- [ ] `test_persist_outputs_includes_new_fields` – JSON final com novos campos.

### Frontend
- [ ] Tests unitários para `splitWizardPayload` e helpers de fase.
- [ ] Teste do wizard garantindo bloqueio/desbloqueio correto entre fases e persistência local.
- [ ] Teste de SSE simulando `storybrand.completed`/`storybrand.failed` verificando `isStorybrandReady`.
- [ ] Teste de regressão do fluxo legado (`VITE_ENABLE_WIZARD=false`).

### Integração / E2E
- [ ] Cenário feliz: fase 1 → evento `storybrand.completed` → fase 2 → pipeline final reutiliza StoryBrand.
- [ ] Cenário de falha no bootstrap: UI oferece retry e não avança para fase 2.
- [ ] Cenário de falha no fetch pós-bootstrap: `landing_page_fetch_failed_after_fallback=True` e logs conferidos.

---

## Observabilidade e Resiliência
- [ ] Configurar métricas/alertas para taxa de `storybrand.failed` e tempo médio do bootstrap.
- [ ] Incluir campos novos nos dashboards (status, completed_at, bootstrap_attempts).
- [ ] Revisar sanitização de logs para novos eventos.

---

## Rollback
- [ ] Documentar procedimento para setar `ENABLE_STORYBRAND_BOOTSTRAP=false` e/ou `STORYBRAND_BOOTSTRAP_ROLLOUT_PERCENTAGE=0`.
- [ ] Reverter frontend para formulário único (`VITE_ENABLE_WIZARD=false`) e garantir que preflight volte a `phase="full"`.
- [ ] Disponibilizar script/manual para limpar `storybrand_fallback_meta.status` de artefatos caso algum consumidor não suporte o campo.

---

## QA Manual
- [ ] Executar manualmente o fluxo completo verificando: criação da narrativa antes da campanha, transição na UI e persistência dos novos dados.
- [ ] Validar reentrância (reiniciar a fase 1 após erro, repetir fase 2 com dados editados).
- [ ] Conferir que refresh da página entre fases restaura o estado a partir de `localStorage`.

---

## Artefatos Finais
- [ ] Evento SSE `storybrand.completed` documentado e consumido.
- [ ] Evento SSE `storybrand.failed` disponível para UX/observabilidade.
- [ ] Novo campo `landing_page_fetch_failed_after_fallback` persistido e documentado.
- [ ] Helpers (`ensure_storybrand_meta`, `splitWizardPayload`, `getWizardStepsByPhase`) versionados e cobertos por testes.
