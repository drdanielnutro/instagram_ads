# Plano de Refatoração – Fallback StoryBrand como Padrão

## 1. Mapa do Código

| Caminho | Existe? | Funções / Métodos relevantes | Papel no fluxo |
| --- | --- | --- | --- |
| `app/agent.py` | Sim | `input_processor`, `LandingPageStage._run_async_impl`, `complete_pipeline`, `execution_pipeline` | Extrai campos iniciais, controla pulo da análise de landing page em modo fallback e orquestra a sequência `input_processor → landing_page_stage → storybrand_quality_gate → execution_pipeline`. |
| `app/agents/storybrand_gate.py` | Sim | `StoryBrandQualityGate._run_async_impl` | Decide se executa o fallback com base em score, flags e `force_storybrand_fallback`, preenchendo `storybrand_fallback_meta` e métricas. |
| `app/agents/storybrand_fallback.py` | Sim | `FallbackInputInitializer`, `fallback_input_collector`, `StoryBrandSectionRunner`, `FallbackStorybrandCompiler`, `FallbackQualityReporter`, `fallback_storybrand_pipeline` | Constrói a narrativa StoryBrand, exige `nome_empresa/o_que_a_empresa_faz/sexo_cliente_alvo`, compila e grava auditoria. |
| `app/agents/fallback_compiler.py` | Sim | `FallbackStorybrandCompiler._run_async_impl` | Persiste `storybrand_analysis`, `storybrand_summary`, `storybrand_ad_context` e sincroniza o score com `landing_page_context`. |
| `app/callbacks/landing_page_callbacks.py` | Sim | `process_and_extract_sb7` | Executa web fetch + LangExtract, atualiza estado e aciona fallback quando o fetch falha. |
| `app/callbacks/persist_outputs.py` | Sim | `persist_final_delivery` | Inclui metadados finais, persistindo `storybrand_gate_metrics` e `storybrand_fallback_meta` nos relatórios. |
| `helpers/user_extract_data.py` | Sim | `UserInputExtractor` | Preflight extrai campos do formulário, incluindo novos campos e `force_storybrand_fallback`. |
| `app/config.py` | Sim | `DevelopmentConfiguration`, overrides via env | Define defaults das flags (`enable_new_input_fields`, `enable_storybrand_fallback`, `storybrand_gate_debug`, etc.) e leitura de variáveis. |
| `frontend/src/App.tsx` | Sim | estados, `runPreflight`, `handleSubmit`, parsing SSE | Cria sessões, envia payload único, processa SSE sem distinguir conclusão do fallback. |
| `frontend/src/components/WizardForm/WizardForm.tsx` | Sim | estado do wizard, `handleSubmit`, `renderStepContent` | Wizard coleta todos os campos em uma etapa contínua antes do envio. |
| `frontend/src/constants/wizard.constants.ts` | Sim | `WIZARD_INITIAL_STATE`, `WIZARD_STEPS` | Define ordem dos passos e ativa campos adicionais via `VITE_ENABLE_NEW_FIELDS`. |
| `frontend/src/utils/wizard.utils.ts` | Sim | `formatSubmitPayload`, validações | Serializa todos os campos em uma única string e controla validação passo a passo. |
| `frontend/src/components/WelcomeScreen.tsx` | Sim | Toggle wizard/formulário tradicional | Renderiza wizard quando `VITE_ENABLE_WIZARD` está ativo. |
| `frontend/src/utils/featureFlags.ts` | Sim | `readBooleanFlag`, `isWizardEnabled`, `isPreviewEnabled` | Normaliza flags do Vite para a UI. |

---

## 2. Plano de Refatoração — Backend

### 2.1 `app/agent.py`
- **Ação:** modificar / adicionar novo estágio.
- **Trechos:** definição de `complete_pipeline`, implementação de `LandingPageStage._run_async_impl`.
- **Passos:**
  1. Criar `storybrand_bootstrap_stage` (novo `SequentialAgent`) imediatamente após `input_processor`, invocando `fallback_storybrand_pipeline` quando `storybrand_fallback_meta.status != "completed"` e flags `enable_storybrand_fallback`/`enable_new_input_fields` estiverem ativas.
  2. Atualizar `complete_pipeline.sub_agents` para `[input_processor, storybrand_bootstrap_stage, landing_page_stage, storybrand_quality_gate, execution_pipeline]` preservando a ordem global exigida.
  3. Dentro do bootstrap, ao fim do fallback, definir `state["storybrand_fallback_meta"]["status"] = "completed"`, registrar `state["storybrand_fallback_meta"]["completed_at"]` (UTC) e opcionalmente `state["fallback_completed_at"]` para auditoria.
  4. Limpar `state["force_storybrand_fallback"]` somente quando não estiver em modo debug (`storybrand_gate_debug`), evitando loops involuntários.
- **Justificativa:** garante StoryBrand pronto antes das demais etapas sem alterar a assinatura do pipeline.
- **Flags:** `ENABLE_STORYBRAND_FALLBACK`, `ENABLE_NEW_INPUT_FIELDS`, `STORYBRAND_GATE_DEBUG` (mantidas, sem rename).
- **SSE/Auditoria:** encaminhar evento de conclusão definido no item 2.3.

### 2.2 `app/agents/storybrand_gate.py`
- **Ação:** modificar `StoryBrandQualityGate._run_async_impl`.
- **Passos:**
  1. Antes de calcular score, verificar `state.get("storybrand_fallback_meta", {}).get("status") == "completed"`. Quando verdadeiro e sem `force_storybrand_fallback`, pular reexecução do fallback e registrar `decision_path = "fallback_precompleted"`.
  2. Manter reexecução quando `force_storybrand_fallback` ou `storybrand_gate_debug` estiverem ativos.
  3. Propagar `completed_at` e outros campos já preenchidos no bootstrap, sem sobrescrever `quality_report` criado no reporter.
- **Justificativa:** evita reprocessamento, prepara reuso do StoryBrand e mantém métricas.
- **Flags:** mesmas anteriores.
- **SSE/Auditoria:** garantir que `storybrand_fallback_meta` permaneça consistente para dashboards e relatórios persistidos.

### 2.3 `app/agents/storybrand_fallback.py` & `app/agents/fallback_compiler.py`
- **Ação:** modificar trechos finais do pipeline.
- **Passos:**
  1. Em `FallbackStorybrandCompiler._run_async_impl`, após persistir `storybrand_analysis/storybrand_summary/storybrand_ad_context`, emitir `Event(actions=EventActions(state_delta={"storybrand_fallback_meta": {"status": "completed", "timestamp_utc": <now>}}, author="fallback_storybrand_compiler"))` e incluir o resumo no delta.
  2. Ajustar `FallbackQualityReporter` para anotar `state["storybrand_fallback_meta"]["quality_report"] = report` sem remover `status`/`timestamp`.
  3. Garantir que o pipeline remova flags temporárias que marcavam fallback em andamento.
- **Justificativa:** cria marcador inequívoco consumido pela UI e preserva auditoria.
- **Flags:** nenhuma nova.
- **SSE/Auditoria:** novo evento `storybrand.completed` via `stateDelta` (status `completed`).

### 2.4 `LandingPageStage` em `app/agent.py`
- **Ação:** modificar `_run_async_impl`.
- **Passos:**
  1. Substituir early-return por fallback forçado apenas quando `force_storybrand_fallback` estiver ativo explicitamente; se o StoryBrand já estiver concluído (`status == "completed"`) e não houver flag de força, permitir execução da análise oficial para manter logs.
  2. Continuar marcando `landing_page_analysis_failed=True` e preenchendo `storybrand_last_error` se o fetch falhar.
- **Justificativa:** não mascarar erros reais enquanto o fallback vira padrão.
- **Flags:** `ENABLE_STORYBRAND_FALLBACK`, `ENABLE_NEW_INPUT_FIELDS`, `STORYBRAND_GATE_DEBUG`.
- **SSE/Auditoria:** manter logs atuais (`storybrand_landing_page_skipped`).

### 2.5 `app/callbacks/landing_page_callbacks.py`
- **Ação:** modificar `process_and_extract_sb7`.
- **Passos:**
  1. Quando o fetch falhar após fallback concluído, setar `state["landing_page_fetch_failed_after_fallback"] = True` (novo campo) ao invés de reativar `force_storybrand_fallback`.
  2. Registrar `storybrand_last_error` com detalhes do fetch mesmo que o fallback esteja pronto.
- **Justificativa:** diferencia falhas reais pós-fallback e preserva diagnóstico.
- **Flags:** sem alteração.

### 2.6 `app/callbacks/persist_outputs.py`
- **Ação:** modificar `persist_final_delivery`.
- **Passos:**
  1. Incluir no payload final os campos `storybrand_fallback_meta.status`, `completed_at`, `quality_report` e `landing_page_fetch_failed_after_fallback`.
  2. Documentar o novo `decision_path` para consumo em dashboards.
- **Justificativa:** manter rastreabilidade do fallback obrigatório.

### 2.7 `helpers/user_extract_data.py`
- **Ação:** modificar `UserInputExtractor.extract` e helpers.
- **Passos:**
  1. Continuar populando campos do fallback quando `ENABLE_NEW_INPUT_FIELDS` for `True`, mas separar a saída em `storybrand_inputs` e `campaign_inputs` (novo formato no `initial_state`).
  2. Propagar `force_storybrand_fallback=True` como hoje, garantindo compatibilidade com sessões legadas.
- **Justificativa:** prepara backend para receber payload parcial da fase 1 sem perder dados da fase 2.

### 2.8 Testes (`tests/unit/agents/test_storybrand_gate.py` e novos)
- **Ação:** adicionar casos.
- **Passos:**
  1. Cobrir cenário `status="completed"` → gate não reexecuta fallback.
  2. Cobrir `force_storybrand_fallback=True` → fallback executa novamente.
  3. Validar emissão de `decision_path="fallback_precompleted"`.
  4. Criar teste para `storybrand_bootstrap_stage` garantindo `stateDelta` com `status="completed"`.
- **Justificativa:** assegurar comportamento previsto e telemetria correta.

---

## 3. Plano de Refatoração — Frontend

### 3.1 `frontend/src/constants/wizard.constants.ts`
- **Ação:** modificar.
- **Passos:**
  1. Adicionar atributo `phase` aos passos (`"storybrand"` para `nome_empresa`, `o_que_a_empresa_faz`, `sexo_cliente_alvo`; `"campaign"` para demais).
  2. Exportar utilitário `getWizardStepsByPhase()` retornando listas separadas para consumo pelo wizard e pelo envio.
- **Justificativa:** define fonte única de verdade para as duas fases.

### 3.2 `frontend/src/utils/wizard.utils.ts`
- **Ação:** modificar helpers de payload/validação.
- **Passos:**
  1. Alterar `formatSubmitPayload` para receber `phase` e montar string apenas com campos da fase correspondente.
  2. Expor helper `splitWizardPayload(formState)` retornando `{ storybrand, campaign }` para `App.tsx`.
  3. Atualizar validações para travar somente campos da fase atual.
- **Justificativa:** permite envio parcial e evita repetir campos da fase 1 na fase 2.

### 3.3 `frontend/src/components/WizardForm/WizardForm.tsx`
- **Ação:** modificar estrutura do wizard.
- **Passos:**
  1. Utilizar `phase` para renderizar passos da fase 1 primeiro; após submissão, exibir resumo bloqueado desses campos e continuar com passos da fase 2.
  2. Adaptar `handleSubmit` para devolver `{ storybrandPayload, campaignPayload }` e sinalizar ao componente pai quando a fase 1 terminar.
  3. Incluir indicadores visuais (ex.: Stepper) destacando “Momento 1 – História” e “Momento 2 – Complemento”.
- **Justificativa:** separa UX em dois momentos sem duplicar componentes.

### 3.4 `frontend/src/App.tsx`
- **Ação:** modificar fluxo principal.
- **Passos:**
  1. Introduzir estados `storybrandInputs`, `campaignInputs`, `isStorybrandReady`, `pendingCampaignPayload`.
  2. Ao receber submissão da fase 1, executar `runPreflight` e `handleSubmit` enviando apenas `storybrandPayload`, armazenando `campaignPayload` localmente.
  3. Ajustar `extractDataFromSSE` para detectar `event.actions.stateDelta.storybrand_fallback_meta.status === "completed"` e então setar `isStorybrandReady = true`.
  4. Após `isStorybrandReady` ser verdadeiro, habilitar UI da fase 2 e enviar payload complementar (automático ou mediante confirmação do usuário).
  5. Bloquear previews/ações (`VITE_ENABLE_ADS_PREVIEW`) até que `isStorybrandReady` seja verdadeiro.
- **Justificativa:** sincroniza com backend e evita interação prematura.

### 3.5 `frontend/src/components/WelcomeScreen.tsx`
- **Ação:** modificar apresentação inicial.
- **Passos:**
  1. Mostrar indicador “Gerando StoryBrand” enquanto `isStorybrandReady` é falso.
  2. Desabilitar botões que iniciam pipeline principal até receber o sinal de conclusão.
- **Justificativa:** comunica claramente os dois momentos ao usuário.

### 3.6 SSE e estado (`frontend/src/App.tsx`)
- **Ação:** extender handlers.
- **Passos:**
  1. Garantir que `handleStreamEvent` não duplique eventos; ao ver `storybrand.completed`, marcar `storybrandInputs` como finalizados.
  2. Registrar logs de debug (apenas em dev) para facilitar QA da transição.
- **Justificativa:** mantém experiência de streaming e facilita depuração.

### 3.7 Testes (unitários/componentes)
- **Ação:** adicionar testes.
- **Passos:**
  1. Testar `splitWizardPayload` garantindo separação correta.
  2. Testar `App` (ou hooks) simulando SSE `storybrand.completed` e verificando desbloqueio da fase 2.
  3. Garantir que `VITE_ENABLE_WIZARD=false` continue enviando payload único (fallback para fluxo legado).
- **Justificativa:** evita regressões na jornada principal e legada.

---

## 4. Glossário de Flags

| Chave | Tipo / Default | Onde é lida | Efeito | Ação |
| --- | --- | --- | --- | --- |
| `ENABLE_NEW_INPUT_FIELDS` | bool / `False` (override `True` em `app/.env`) | `app/config.py`, `helpers/user_extract_data.py` | Libera campos StoryBrand (backend) | Manter |
| `ENABLE_STORYBRAND_FALLBACK` | bool / `False` (override `True`) | `app/config.py`, `app/agent.py`, `StoryBrandQualityGate` | Controla execução do fallback | Manter |
| `STORYBRAND_GATE_DEBUG` | bool / `False` (override `True`) | `app/config.py`, `LandingPageStage`, `StoryBrandQualityGate` | Força fallback mesmo com StoryBrand pronto | Manter |
| `PREFLIGHT_SHADOW_MODE` | bool / `True` | `app/config.py`, `helpers/user_extract_data.py` | Extrai novos campos sem persistir | Manter; documentar interação com fases |
| `ENABLE_DETERMINISTIC_FINAL_VALIDATION` | bool / `False` (override `True`) | `app/config.py`, `execution_pipeline` | Liga validador determinístico | Manter |
| `ENABLE_IMAGE_GENERATION` | bool / `True` | `app/config.py`, pipelines de imagem | Controla criação de imagens | Manter |
| `ENABLE_REFERENCE_IMAGES` | bool / `False` (override `True`) | `app/config.py`, manipuladores de imagem | Habilita uploads de referência | Manter |
| `VITE_ENABLE_WIZARD` | bool / `.env.local: true` | `frontend/src/utils/featureFlags.ts`, `WelcomeScreen` | Ativa wizard | Manter |
| `VITE_ENABLE_NEW_FIELDS` | bool / `.env.local: true` | `frontend/src/constants/wizard.constants.ts` | Exibe campos StoryBrand | Manter |
| `VITE_ENABLE_PREFLIGHT` | bool / `.env.local: true` | `frontend/src/App.tsx` | Ativa preflight | Manter (deve aceitar payload parcial) |
| `VITE_ENABLE_ADS_PREVIEW` | bool / `.env.local: true` | `frontend/src/utils/featureFlags.ts`, `App.tsx` | Libera preview | Manter (bloquear até fase 2) |

---

## 5. Matriz de Testes Automatizados

| Cenário | Camada | Entrada / Setup | Sinal esperado | Saída / Verificação |
| --- | --- | --- | --- | --- |
| Fallback obrigatório ao iniciar | Backend | Sessão nova com `ENABLE_STORYBRAND_FALLBACK=true`, `ENABLE_NEW_INPUT_FIELDS=true` | SSE/stateDelta com `storybrand_fallback_meta.status="completed"` | `storybrand_analysis` populado, `decision_path="fallback_precompleted"` |
| Forçar reexecução do fallback | Backend | Estado com `status="completed"` + `force_storybrand_fallback=True` | Novo ciclo do fallback e `decision_path="fallback"` | `completed_at` atualizado |
| Falha no web fetch após fallback | Backend | Simular erro em `web_fetch_tool` | Log `landing_page_analysis_failed`, `storybrand_last_error` preenchido | Campo `landing_page_fetch_failed_after_fallback=True` |
| UI fase 1 → fase 2 | Frontend | Wizard conclui campos StoryBrand | SSE `storybrand.completed` → `isStorybrandReady=true` | Passos da fase 2 desbloqueados, campos fase 1 bloqueados |
| Envio fase 2 com StoryBrand reutilizado | Full-stack | Submeter campos da fase 2 após evento | Sem novo `storybrand.completed` | JSON final reutiliza StoryBrand persistido |
| Pré-flight parcial | Backend/Frontend | Chamar `/run_preflight` com StoryBrand payload | Resposta com `storybrand_inputs` populados e `campaign_inputs` vazios | Campos armazenados para fase 2 |
| Fluxo legado (wizard off) | Frontend | `VITE_ENABLE_WIZARD=false` | N/A | Form tradicional envia payload único sem travas |

---

## 6. Checklist Sequencial de Execução

1. **Backend**
   - Implementar `storybrand_bootstrap_stage` e ajustes no pipeline (`app/agent.py`).
   - Atualizar `StoryBrandQualityGate`, `FallbackStorybrandCompiler` e reporter para emitir `storybrand.completed`.
   - Revisar `LandingPageStage`, callbacks e persistência (`landing_page_callbacks.py`, `persist_outputs.py`).
   - Adequar `UserInputExtractor` ao formato separado e criar testes unitários.
2. **Frontend**
   - Atualizar constantes/utilitários do wizard para fases distintas.
   - Refatorar `WizardForm` e `App.tsx` para envio faseado e tratamento de SSE.
   - Ajustar `WelcomeScreen` e feedbacks visuais; garantir compatibilidade com flags.
   - Escrever testes cobrindo separação de fases e sinal SSE.
3. **Integração**
   - Executar fluxo end-to-end local verificando que o fallback roda primeiro, UI aguarda sinal e pipeline principal conclui com StoryBrand reutilizado.

---

## 7. Plano de Observabilidade e Rollback

- **Observabilidade:**
  - Manter logs existentes (`storybrand_gate_decision`, `storybrand_landing_page_skipped`).
  - Adicionar log `storybrand.completed` com timestamp e identificador da sessão.
  - Persistir `storybrand_fallback_meta.status/completed_at/quality_report` e novo campo `landing_page_fetch_failed_after_fallback` nos relatórios finais para dashboards.
- **Rollback:**
  - Desativar `ENABLE_STORYBRAND_FALLBACK` e `STORYBRAND_GATE_DEBUG` para retornar ao comportamento anterior no backend.
  - No frontend, ajustar `.env.local` para `VITE_ENABLE_WIZARD=false` revertendo para formulário único (payload combinado).
  - As alterações mantêm compatibilidade com flags existentes, permitindo reversão sem deploy adicional.

---

## 8. ✅ Planned Creations (não validar no código)

- `storybrand_bootstrap_stage` (novo estágio em `app/agent.py`).
- Campo `landing_page_fetch_failed_after_fallback` no estado.
- Evento SSE `storybrand.completed` emitido pelo fallback.
- Helpers `getWizardStepsByPhase`, `splitWizardPayload` e novos estados em `App.tsx`.
