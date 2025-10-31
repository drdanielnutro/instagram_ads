# Plano de Refatoração – StoryBrand como Etapa Primária

## 1. Contexto e Objetivos

- Garantir que a narrativa StoryBrand seja sempre construída e persistida **antes** de qualquer etapa de execução de anúncios.  
- Dividir o fluxo em **duas fases coerentes** (StoryBrand e Campanha) tanto no backend quanto no frontend, incluindo validações específicas e preflight faseado.  
- Manter compatibilidade com sessões/flags existentes, preservando a capacidade de rollback rápido e de auditoria completa.

---

## 2. Visão Arquitetural Atual vs. Alvo

| Aspecto | Situação Atual | Estado Desejado |
| --- | --- | --- |
| Pipeline principal (`app/agent.py`) | `input_processor → landing_page_stage → storybrand_quality_gate → execution_pipeline` (fallback só roda quando gate decide) | `input_processor → storybrand_bootstrap_stage → landing_page_stage → storybrand_quality_gate → execution_pipeline`. Bootstrap garante StoryBrand pronto; gate valida/força reexecução quando necessário. |
| Metadados StoryBrand | `storybrand_fallback_meta` contém apenas `fallback_engaged`, `decision_path`, `trigger_reason`, `timestamp_utc`. | Estrutura estendida com `status`, `completed_at`, `fallback_engaged`, `decision_path`, `trigger_reason`, `timestamp_utc`, `quality_report`, `errors`, `bootstrap_attempts`. |
| Preflight (`/run_preflight`) | Valida todos os campos de uma vez a partir de string única com todos os inputs. | Aceita `phase` (`"storybrand"`, `"campaign"`, `"full"`), aplicando validações específicas por fase e retornando `initial_state` segmentado (`storybrand_inputs`, `campaign_inputs`). |
| UI Wizard | Coleta todos os campos em uma fase; envia payload único. | Fase 1 (StoryBrand) → aguarda `storybrand.completed` → Fase 2 (Campanha). Payloads enviados separadamente, com persistência local e retomada segura. |
| SSE | Sem evento explícito de conclusão StoryBrand. | Evento `storybrand.completed` emitido com `stateDelta.storybrand_fallback_meta.status="completed"` e resumo. |

---

## 3. Estrutura de Dados Planejada

```python
state["storybrand_fallback_meta"] = {
    "status": Literal["pending", "in_progress", "completed", "skipped", "failed"],
    "fallback_engaged": bool,
    "decision_path": str,
    "trigger_reason": str,
    "timestamp_utc": str,       # criação do meta
    "completed_at": str | None, # preenchido quando status=="completed"
    "quality_report": dict | None,
    "errors": list[dict] | None,  # falhas durante bootstrap
    "bootstrap_attempts": int,    # incrementado a cada tentativa
}
```

- Inicializar essa estrutura **antes** do bootstrap para evitar `KeyError`.
- Preservar `fallback_engaged` para leitura legada.
- Documentar novos campos em `persist_outputs.py` e meta final.

---

## 4. Plano de Refatoração – Backend

### 4.1 `app/agent.py`
1. Criar `ensure_storybrand_meta(state)` para inicializar a estrutura acima quando ausente.  
2. Implementar `storybrand_bootstrap_stage` (`SequentialAgent`) imediatamente após `input_processor`.  
   - Entrada: state já com os campos StoryBrand obrigatórios provenientes da fase 1.  
   - Fluxo:  
     ```python
     meta = ensure_storybrand_meta(state)
     if meta["status"] == "completed" and not force_flag:
         return  # StoryBrand já disponível (protege reentrâncias)
     meta.update(status="in_progress", bootstrap_attempts=meta["bootstrap_attempts"] + 1)
     async for event in fallback_storybrand_pipeline.run_async(ctx):
         yield event
     if meta["status"] != "completed":
         meta["status"] = "failed"
         meta.setdefault("errors", []).append({"reason": "bootstrap_failed"})
         raise StoryBrandBootstrapError(...)
     ```
   - Ao concluir com sucesso, preencher `completed_at`, forçar `fallback_engaged=True` e limpar `force_storybrand_fallback` quando `storybrand_gate_debug` estiver desligado.
3. Atualizar `complete_pipeline.sub_agents` para `[input_processor, storybrand_bootstrap_stage, landing_page_stage, storybrand_quality_gate, execution_pipeline]`.
4. Ajustar `LandingPageStage._run_async_impl`:  
   - Se `storybrand_gate_debug` ou `force_storybrand_fallback` estiverem ativos, manter comportamento atual.  
   - Caso contrário, executar análise oficial mesmo após StoryBrand pronto, registrando `landing_page_fetch_failed_after_fallback=True` quando apropriado.

### 4.2 `app/agents/storybrand_gate.py`
1. Invocar `ensure_storybrand_meta(state)` no início.  
2. Se `meta["status"] == "completed"` e não houver `force_storybrand_fallback`, pular o fallback, registrar `decision_path="fallback_precompleted"` e garantir que `fallback_engaged` permaneça `True`.  
3. Quando precisar reexecutar (force/debug/erro), atualizar `status="in_progress"`, incrementar `bootstrap_attempts` e propagar novo `completed_at` após a execução.  
4. Enviar métricas legadas (`fallback_engaged`) e novas (`status`, `bootstrap_attempts`) para dashboards.

### 4.3 `app/agents/storybrand_fallback.py` & `app/agents/fallback_compiler.py`
1. No início do pipeline, validar a presença dos campos exigidos (`REQUIRED_INPUT_KEYS`). Caso ausentes, preencher `meta["status"]="failed"` e levantar erro claro (`MissingStoryBrandInputs`).  
2. Ao final do `FallbackStorybrandCompiler`, emitir:
   ```python
   yield Event(
       author=self.name,
       actions=EventActions(
           state_delta={
               "storybrand_fallback_meta": {
                   "status": "completed",
                   "completed_at": timestamp_utc,
                   "fallback_engaged": True,
               },
               "storybrand_analysis": compiled_sections,
               "storybrand_summary": summary,
               "storybrand_ad_context": ad_context,
           },
           event_type="storybrand.completed",
       ),
   )
   ```
3. Garantir que `FallbackQualityReporter` anexe `quality_report` sem remover campos do meta.
4. Remover flags temporárias (`storybrand_fallback_in_progress`, etc.) antes de sair.

### 4.4 `app/callbacks/landing_page_callbacks.py`
- Quando o fetch falhar após StoryBrand pronto, setar `landing_page_fetch_failed_after_fallback=True` e anexar detalhes em `storybrand_last_error`, sem reativar o fallback.

### 4.5 `app/callbacks/persist_outputs.py`
- Incluir os novos campos (`status`, `completed_at`, `quality_report`, `bootstrap_attempts`, `landing_page_fetch_failed_after_fallback`) no JSON final e no `meta.json`.  
- Atualizar documentação inline e garantir compatibilidade com consumidores existentes (campos opcionais).

### 4.6 Preflight faseado – `helpers/user_extract_data.py` & `app/server.py`
1. Atualizar `UserInputExtractor.extract` para aceitar `phase: Literal["storybrand", "campaign", "full"] = "full"`.  
2. Validações:  
   - `phase="storybrand"`: somente `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`, `force_storybrand_fallback`.  
   - `phase="campaign"`: `landing_page_url`, `formato_anuncio`, `objetivo_final`, `perfil_cliente`, campos adicionais do pipeline principal.  
   - `phase="full"`: mantém comportamento atual (compatibilidade).  
3. Resposta do preflight:
   ```json
   {
     "initial_state": {
       "storybrand_inputs": {...},   // presente na fase storybrand/full
       "campaign_inputs": {...},     // presente na fase campaign/full
       "flags": {...}
     },
     "plan_summary": {...}
   }
   ```
4. No backend, garantir que `input_processor` combine `storybrand_inputs` e `campaign_inputs` quando ambos existirem.  
5. Ajustar `/run_preflight` para ler `phase` do payload (body) e encaminhar ao extractor. Quando omitido → `"full"`.  
6. Introduzir helper `merge_initial_state_from_phases` para reutilização em testes.

### 4.7 Tratamento de Erros e Resiliência
- Implementar timeout configurável para o bootstrap; se excedido, registrar `meta["status"]="failed"` e retornar SSE de falha específico (`storybrand.failed`) para a UI.  
- Registrar logs estruturados (`storybrand_bootstrap_started`, `storybrand_bootstrap_completed`, `storybrand_bootstrap_failed`).  
- Garantir que exceções durante bootstrap não avancem para o pipeline principal; retornar resposta adequada ao frontend.

---

## 5. Plano de Refatoração – Frontend

### 5.1 Estrutura de Dados & Tipos
1. Atualizar `frontend/src/types/wizard.types.ts` com `phase: "storybrand" | "campaign"` e novos tipos `StorybrandPayload`, `CampaignPayload`.  
2. Ajustar `frontend/src/constants/wizard.constants.ts` para incluir `phase` em cada passo e criar `getWizardStepsByPhase(phase: "storybrand" | "campaign")`.

### 5.2 Wizard e Formulários
1. Em `WizardForm`, renderizar apenas passos `phase="storybrand"` inicialmente; após sucesso da fase 1, bloquear campos StoryBrand (readonly) e liberar passos `phase="campaign"`.  
2. Atualizar `handleSubmit` para retornar `{ storybrandPayload, campaignPayload }`, com `campaignPayload` vazio durante a fase 1.  
3. Exibir indicadores visuais dos dois momentos (Stepper ou banner).  
4. Persistir os dados de ambas as fases em `localStorage` (chave namespaced por sessão) para tolerar refresh.

### 5.3 `frontend/src/App.tsx`
1. Novos estados: `storybrandInputs`, `campaignInputs`, `pendingCampaignPayload`, `isStorybrandReady`, `storybrandError`.  
2. Fluxo fase 1:
   - Chamar `runPreflight(text, referenceImagesPayload, phase="storybrand")`.  
   - Criar sessão inicial via `createSession(initial_state=storybrand_initial_state)`.  
   - Iniciar SSE imediatamente após bootstrap começar; exibir spinner “Gerando StoryBrand”.  
3. Ao receber evento `storybrand.completed`, atualizar:  
   ```ts
   setStorybrandArtifacts({
     analysis: delta.storybrand_analysis,
     summary: delta.storybrand_summary,
     adContext: delta.storybrand_ad_context,
   });
   setStorybrandMeta((prev) => ({ ...prev, ...delta.storybrand_fallback_meta }));
   setIsStorybrandReady(true);
   ```
   e, se houver payload da campanha pendente, executar automaticamente `runCampaignPhase()`.
4. Fluxo fase 2:
   - Ao submeter os campos extras, validar com `runPreflight(..., phase="campaign")`.  
   - Enviar ao backend via `/run` reutilizando `sessionId` já criado.  
   - Habilitar previews somente após `isStorybrandReady` e envio da fase 2.
5. Tratar erros:
   - Se receber `storybrand.failed`, exibir mensagem, permitir retry da fase 1 ou cancelar sessão.  
   - Tempo limite: se bootstrap exceder N segundos, mostrar call-to-action de retry.

### 5.4 SSE e Eventos
1. Atualizar `handleStreamEvent` para detectar `event.eventType === "storybrand.completed"` ou checar `stateDelta.storybrand_fallback_meta?.status`.  
2. Ignorar eventos duplicados; somente primeira transição `!isStorybrandReady` → `true` deve disparar a habilitação da fase 2.  
3. Registrar logs (em dev) com `console.debug` controlado por flag (`VITE_DEBUG_STORYBRAND`).

### 5.5 `frontend/src/components/WelcomeScreen.tsx`
- Mostrar skeleton/loader durante bootstrap.  
- Desabilitar ações que iniciem o pipeline principal até `isStorybrandReady` ser verdadeiro.

### 5.6 Manutenção do Fluxo Legado
- Quando `VITE_ENABLE_WIZARD=false` ou `VITE_ENABLE_NEW_FIELDS=false`, manter envio único:
  - `runPreflight` em modo `"full"`.  
  - Sem `storybrand_bootstrap_stage` (controlado por flag no backend).  
- Adicionar testes assegurando que o fluxo legado continua operacional.

---

## 6. Migração, Compatibilidade e Flags

1. **Novas Flags**  
   - `ENABLE_STORYBRAND_BOOTSTRAP` (backend, default `True`): mantém o novo estágio ativo por padrão; pode ser desativado manualmente apenas em cenários de rollback controlado.  
   - `STORYBRAND_BOOTSTRAP_ROLLOUT_PERCENTAGE` (0–100): percentual de sessões que entram no novo fluxo (utilizar para rollout progressivo sem alterar o default da flag principal).  
   - `VITE_DEBUG_STORYBRAND` (frontend, default `false`): habilita logs extras durante testes.
2. **Sessões em andamento**  
   - Detectar ausência de `storybrand_fallback_meta.status` e inicializar como `"unknown"` ao carregar estado.  
   - Permitir que o gate legado continue executando o fallback nesses casos.
3. **Rollout gradual**  
   - Habilitar bootstrap para 10% das sessões; monitorar métricas (`bootstrap duration`, `storybrand.failed`).  
   - Escalar para 100% após 48h de estabilidade.
4. **Compatibilidade**  
   - Persistir tanto `storybrand_fallback_meta.status` quanto `fallback_engaged` para que relatórios atuais continuem válidos.  
   - Documentar novas chaves em `README`/`AGENTS`.

---

## 7. Observabilidade e Resiliência

- Logs estruturados adicionais: `storybrand_bootstrap_started`, `storybrand_bootstrap_completed`, `storybrand_bootstrap_failed`, `storybrand_preflight_validation_error`.  
- Métricas: tempo do bootstrap, taxa de falha, número médio de tentativas.  
- Alertas: criar regra em dashboards quando `storybrand.failed` > X% em 30 minutos.  
- Telemetria frontend: enviar evento analítico quando a fase 2 habilitar (para medir latência percebida).

---

## 8. Plano de Rollback

1. Desativar `ENABLE_STORYBRAND_BOOTSTRAP` (ou definir rollout para 0%).  
2. Frontend: setar `VITE_ENABLE_WIZARD=false` e `VITE_DEBUG_STORYBRAND=false` para retornar ao formulário único.  
3. Limpeza opcional: script que remove `storybrand_fallback_meta.status` de `meta.json` se consumidores não estiverem preparados (documentar no repositório).  
4. Confirmar que `/run_preflight` com `phase` desconhecida volta a `"full"` como fallback.

---

## 9. Testes Automatizados

### 9.1 Backend
- `test_storybrand_bootstrap_runs_once` – garante que `storybrand_bootstrap_stage` executa quando `status="pending"` e não repete quando `"completed"`.  
- `test_storybrand_bootstrap_missing_fields` – assegura que falta de campos gera erro controlado e `meta["status"]="failed"`.  
- `test_storybrand_gate_reuses_completed_storybrand` – gate pula fallback quando `status="completed"`.  
- `test_storybrand_gate_force_flag` – força reexecução, atualizando `completed_at`.  
- `test_preflight_storybrand_phase` e `test_preflight_campaign_phase` – validam nova API com fases distintas.  
- `test_persist_outputs_includes_new_fields` – checa nova estrutura no JSON final.  
- Fixures auxiliares (`mock_storybrand_state`, `fake_preflight_payload`) centralizadas em `tests/unit/conftest.py`.

### 9.2 Frontend
- `splitWizardPayload.test.ts` – separa corretamente StoryBrand vs campanha.  
- `App.storybrand-flow.test.tsx` – simula SSE `storybrand.completed` e desbloqueio da fase 2.  
- `WizardForm.phase-switch.test.tsx` – bloqueios corretos entre fases e persistência local.  
- `App.legacy-flow.test.tsx` – garante que, sem wizard, fluxo antigo funciona.  
- Mocks de SSE (ex.: `tests/utils/mockSSE.ts`) para reproduzir `storybrand.completed` e `storybrand.failed`.

### 9.3 Integração/E2E
- Rodar cenário completo com `ENABLE_STORYBRAND_BOOTSTRAP=true` validando persistência dos novos campos.  
- Simular falha no bootstrap (mock de exceção) e garantir que UI apresenta retry sem avançar para a fase 2.

---

## 10. Checklist de Execução (resumo)

1. **Backend**  
   - `storybrand_bootstrap_stage` implementado e integrado.  
   - Gate atualizado, callbacks e persistência ajustados.  
   - Preflight faseado funcionando com `phase`.  
   - Logs, métricas e tratamento de erros completos.
2. **Frontend**  
   - Wizard com fases, persistência local e eventos SSE.  
   - Novos estados em `App.tsx` e tratamento de erros.  
   - Fluxo legado preservado.
3. **Documentação & Ops**  
   - Atualizar `README`, `AGENTS`, `storybrand_gcs.md` com novo fluxo.  
   - Checklist (`checklist_refatoracao_storybrand.md`) alinhado aos novos itens.  
   - Plano de rollout/migração revisado com time de operações.
4. **Testes**  
   - Suites unitárias, integração e E2E atualizadas.  
   - Cobertura específica para manejo de fases, SSE e persistência.

---

## 11. Riscos e Mitigações

| Risco | Mitigação |
| --- | --- |
| Falha no bootstrap impede usuários de avançar | Eventos `storybrand.failed`, retry controlado e rollback rápido via flag |
| Sessões legadas sem `status` | Inicialização com `"unknown"` e fallback para gate atual |
| Perda de dados na transição entre fases | Persistência local + reenvio automático quando sessão restaurada |
| Aumento de latência perceptível | Telemetria específica e possibilidade de pré-carregar prompts/recursos assíncronos |
| Integridade do preflight | Testes unitários + logging dedicado por fase (`phase`, `errors`, `payload_size`) |

---

## 12. Referências Cruzadas

- `AGENTS.md` – atualizar componentes críticos e flags.  
- `README.md` – revisar seções “Persistência”, “Feature Flags”, “Fluxo StoryBrand”.  
- `storybrand_gcs.md` – alinhar passo de upload com novo estágio obrigatório.  
- `checklist_refatoracao_storybrand.md` – sincronizar itens com o plano revisado.

---

Com este plano, o StoryBrand deixa de ser fallback e passa a ser a base do pipeline, com responsabilidades claras por fase, validações alinhadas e suporte operacional completo.
