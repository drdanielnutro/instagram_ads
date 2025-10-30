# Checklist de Execução – Refatoração Fallback StoryBrand

Este checklist consolida todas as ações descritas em `plano_refatoracao_storybrand.md`. Conclua cada item para garantir que o fallback StoryBrand opere como estágio padrão, preservando telemetria, UX e fluxos legados.

## Backend

### `app/agent.py` – Pipeline e estágios
- [ ] Introduzir `storybrand_bootstrap_stage` (novo `SequentialAgent`) imediatamente após `input_processor`, executando `fallback_storybrand_pipeline` quando o status não for `"completed"` e as flags de fallback estiverem ativas.
- [ ] Atualizar `complete_pipeline.sub_agents` para incluir `[input_processor, storybrand_bootstrap_stage, landing_page_stage, storybrand_quality_gate, execution_pipeline]`, mantendo a ordem global.
- [ ] No bootstrap, registrar `storybrand_fallback_meta.status="completed"`, `storybrand_fallback_meta.completed_at` (UTC) e, se aplicável, `fallback_completed_at` antes de liberar o próximo estágio.
- [ ] Limpar `state["force_storybrand_fallback"]` apenas quando `storybrand_gate_debug` estiver desabilitado, evitando loops involuntários.

### `StoryBrandQualityGate`
- [ ] Atualizar `_run_async_impl` para detectar `storybrand_fallback_meta.status="completed"` e, sem `force_storybrand_fallback`, pular a reexecução registrando `decision_path="fallback_precompleted"`.
- [ ] Garantir reexecução do fallback quando `force_storybrand_fallback` ou `storybrand_gate_debug` estiverem ativos.
- [ ] Preservar `completed_at`, `quality_report` e demais campos já preenchidos pelo bootstrap ao consolidar a decisão do gate.

### `FallbackStorybrandCompiler` e `FallbackQualityReporter`
- [ ] Emitir evento SSE `storybrand.completed` a partir do compilador com `stateDelta` incluindo `storybrand_fallback_meta.status="completed"`, timestamp UTC e resumo StoryBrand.
- [ ] Ajustar o reporter para anexar `storybrand_fallback_meta.quality_report` sem sobrescrever status, timestamps ou dados emitidos pelo compilador.
- [ ] Eliminar flags temporárias que indicam fallback em andamento ao final do pipeline.

### `LandingPageStage` (`app/agent.py`)
- [ ] Revisar `_run_async_impl` para permitir a análise oficial quando o fallback já estiver concluído e `force_storybrand_fallback` estiver desligado.
- [ ] Manter o tratamento de falhas (`landing_page_analysis_failed=True` e `storybrand_last_error`) quando o web fetch falhar, mesmo após o fallback.

### `app/callbacks/landing_page_callbacks.py`
- [ ] Ao detectar falha de fetch posterior ao fallback, registrar `landing_page_fetch_failed_after_fallback=True` sem reativar `force_storybrand_fallback`.
- [ ] Persistir detalhes completos em `storybrand_last_error` para diagnóstico independente do status do fallback.

### `app/callbacks/persist_outputs.py`
- [ ] Incluir em `persist_final_delivery` os campos `storybrand_fallback_meta.status`, `storybrand_fallback_meta.completed_at`, `storybrand_fallback_meta.quality_report` e `landing_page_fetch_failed_after_fallback`.
- [ ] Documentar `decision_path` atualizado no payload final para uso em dashboards e auditorias.

### `helpers/user_extract_data.py`
- [ ] Separar a saída do preflight em `storybrand_inputs` e `campaign_inputs` sempre que `ENABLE_NEW_INPUT_FIELDS` estiver ativo.
- [ ] Continuar propagando `force_storybrand_fallback=True` quando solicitado, mantendo compatibilidade com sessões legadas.

### Cobertura de testes backend
- [ ] Adicionar teste garantindo que o gate não reexecuta o fallback quando o status é `"completed"` e não há `force_storybrand_fallback`.
- [ ] Adicionar teste cobrindo o cenário com `force_storybrand_fallback=True`, incluindo a atualização de `completed_at`.
- [ ] Validar via teste que `decision_path="fallback_precompleted"` é registrado quando o fallback já está pronto.
- [ ] Criar teste para `storybrand_bootstrap_stage`, confirmando o `stateDelta` com `storybrand_fallback_meta.status="completed"`.

## Frontend

### `frontend/src/constants/wizard.constants.ts`
- [ ] Adicionar atributo `phase` aos passos do wizard, classificando-os como `"storybrand"` ou `"campaign"`.
- [ ] Exportar `getWizardStepsByPhase()` retornando listas distintas para uso no wizard e na preparação de payloads.

### `frontend/src/utils/wizard.utils.ts`
- [ ] Atualizar `formatSubmitPayload` para receber a fase corrente e serializar apenas os campos correspondentes.
- [ ] Implementar helper `splitWizardPayload(formState)` que retorne `{ storybrand, campaign }` para consumo em `App.tsx`.
- [ ] Ajustar validações para bloquear somente os campos da fase ativa, mantendo os demais intactos.

### `frontend/src/components/WizardForm/WizardForm.tsx`
- [ ] Renderizar a fase StoryBrand antes da fase de campanha, exibindo um resumo bloqueado dos campos da fase 1 após a submissão.
- [ ] Adaptar `handleSubmit` para retornar `{ storybrandPayload, campaignPayload }` e sinalizar ao componente pai quando a fase 1 estiver concluída.
- [ ] Introduzir indicadores visuais (ex.: stepper) destacando “Momento 1 – História” e “Momento 2 – Complemento”.

### `frontend/src/App.tsx`
- [ ] Criar estados `storybrandInputs`, `campaignInputs`, `isStorybrandReady` e `pendingCampaignPayload`.
- [ ] Ao concluir a fase 1, acionar `runPreflight`/`handleSubmit` com apenas o payload StoryBrand, armazenando localmente o payload da campanha.
- [ ] Atualizar o handler de SSE para identificar `storybrand_fallback_meta.status==="completed"` e definir `isStorybrandReady=true`.
- [ ] Habilitar a fase 2 (e enviar o payload complementar) somente após `isStorybrandReady` estar verdadeiro, conforme UX definida.
- [ ] Bloquear pré-visualizações (`VITE_ENABLE_ADS_PREVIEW`) e demais ações dependentes até receber o sinal de conclusão do StoryBrand.

### `frontend/src/components/WelcomeScreen.tsx`
- [ ] Exibir indicador “Gerando StoryBrand” enquanto `isStorybrandReady` for falso.
- [ ] Desabilitar botões de início do pipeline principal até o recebimento do evento `storybrand.completed`.

### SSE e depuração (`frontend/src/App.tsx`)
- [ ] Garantir que `handleStreamEvent` ignore duplicações e marque `storybrandInputs` como finalizados ao processar `storybrand.completed`.
- [ ] Registrar logs de depuração (limitados a desenvolvimento) para acompanhar a transição entre fases.

### Cobertura de testes frontend
- [ ] Testar `splitWizardPayload` assegurando separação correta entre StoryBrand e campanha.
- [ ] Testar o componente (ou hook) responsável por SSE simulando `storybrand.completed` e verificando o desbloqueio da fase 2.
- [ ] Garantir via teste que, com `VITE_ENABLE_WIZARD=false`, o fluxo legado continua enviando um único payload combinado.

## Testes End-to-End e Cenários Cobertos
- [ ] Automatizar cenário em que o fallback roda obrigatoriamente no início, validando `storybrand_fallback_meta.status="completed"` e `decision_path="fallback_precompleted"`.
- [ ] Cobrir via testes que `force_storybrand_fallback=True` provoca uma nova execução do fallback e atualiza `completed_at`.
- [ ] Simular falha de web fetch após o fallback e validar `landing_page_fetch_failed_after_fallback=True` e `storybrand_last_error` preenchido.
- [ ] Garantir que a UI transite da fase 1 para a fase 2 apenas após `storybrand.completed`, bloqueando o fluxo até então.
- [ ] Verificar que o envio da fase 2 reutiliza o StoryBrand previamente gerado, sem gerar novo evento de conclusão.
- [ ] Validar que `/run_preflight` aceita payload parcial da fase 1 e retorna `storybrand_inputs` populados com `campaign_inputs` vazios.
- [ ] Confirmar que o fluxo legado (wizard desativado) permanece operacional com envio único de payload.

## Integração e QA Manual
- [ ] Executar fluxo end-to-end local confirmando que o fallback ocorre antes dos demais estágios, a UI aguarda o sinal `storybrand.completed` e o pipeline final reutiliza o StoryBrand produzido.

## Observabilidade
- [ ] Manter logs existentes (`storybrand_gate_decision`, `storybrand_landing_page_skipped`) após a refatoração.
- [ ] Registrar novo log `storybrand.completed` com timestamp e identificador da sessão.
- [ ] Persistir `storybrand_fallback_meta.status`, `storybrand_fallback_meta.completed_at`, `storybrand_fallback_meta.quality_report` e `landing_page_fetch_failed_after_fallback` nos relatórios finais para consumo analítico.

## Rollback Planejado
- [ ] Documentar a reversão via flags desativando `ENABLE_STORYBRAND_FALLBACK` e `STORYBRAND_GATE_DEBUG`, retornando ao comportamento atual no backend.
- [ ] Registrar o procedimento de desativar `VITE_ENABLE_WIZARD` em `.env.local` para retornar ao formulário tradicional.
- [ ] Validar que a combinação de flags fornece rollback completo sem necessidade de novo deploy.

## Artefatos e Componentes Novos
- [ ] Implementar e versionar o novo `storybrand_bootstrap_stage` descrito no plano.
- [ ] Adicionar o campo `landing_page_fetch_failed_after_fallback` ao estado e documentá-lo.
- [ ] Disponibilizar o evento SSE `storybrand.completed` consumido pelo frontend.
- [ ] Criar os helpers `getWizardStepsByPhase` e `splitWizardPayload`, além dos novos estados necessários em `App.tsx`.
