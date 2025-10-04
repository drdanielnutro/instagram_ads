# Checklist — Plano de Validação Determinística do JSON Final de Ads

> Convenção: `[ ]` pendente · `[>]` em andamento · `[x]` concluído
> Referência principal: `plano_validacao_json.md`

## 1. Fase 1 – Estruturas de Base (Etapa 5.1)
### 1.1 Schema de validação compartilhado
- [ ] Criar `app/schemas/final_delivery.py` com modelos estritos (`StrictAdCopy`, `StrictAdVisual`, `StrictAdItem`).
- [ ] Permitir `contexto_landing` como `dict[str, Any] | str` com `min_length=1`, relaxando campos quando condições de fallback forem verdadeiras e registrando `schema_relaxation_reason` em `deterministic_final_validation`.
- [ ] Reutilizar enums de `app/format_specifications.py`/`config.py` sem duplicar valores e centralizando limites de caracteres no schema.

### 1.2 Helper de auditoria e metadados
- [ ] Criar `app/utils/audit.py` contendo `append_delivery_audit_event` e funções de logging, mantendo mapeamentos de CTA fora do módulo.
- [ ] Revisar `app/utils/delivery_status.py` apenas para expor helpers comuns necessários sem assumir responsabilidade por enums.

### 1.3 Metadados StoryBrand e landing page
- [ ] Atualizar `StoryBrandQualityGate` para preencher `state['storybrand_fallback_meta'] = {"decision_path", "trigger_reason", "fallback_engaged"}` e manter `storybrand_audit_trail` como lista de eventos.
- [ ] Garantir que o analisador de landing page defina `state['landing_page_analysis_failed']` como booleano em vez de chaves livres.

### 1.4 Enriquecimento dos snippets aprovados
- [ ] Estender `collect_code_snippets_callback` com `snippet_type`, `status="approved"`, `approved_at` (UTC) e `snippet_id` = SHA-256 de `task_id::snippet_type::payload`.
- [ ] Criar `state['approved_visual_drafts']` mapeando `variation_id -> snippet` para uso dos guards sem quebrar consumidores atuais.
- [ ] Atualizar `app/utils/session-state.py` (modelo `CodeSnippet` e helpers `get_session_state`/`add_approved_snippet`) para preservar os novos campos.

### 1.5 Feature flag de ativação
- [ ] Adicionar `enable_deterministic_final_validation` em `config.py` (default `False`) com suporte à env `ENABLE_DETERMINISTIC_FINAL_VALIDATION`.
- [ ] Documentar que o pipeline legado permanece ativo enquanto a flag estiver `False` e que o fluxo determinístico substitui o legado quando `True`.
- [ ] Registrar que a flag é avaliada na inicialização, exigindo restart para alternância, e emitir log estruturado via `log_config_flag`.
- [ ] Atualizar README e docs operacionais com orientações de rollout controlado e ambientes canário.

## 2. Fase 2 – Validador Determinístico (Etapa 5.2)
### 2.1 `FinalDeliveryValidatorAgent`
- [ ] Implementar `app/validators/final_delivery_validator.py` importando os schemas criados na Fase 1.
- [ ] Carregar `final_code_delivery` (string/list/objeto) realizando parsing único antes das validações.
- [ ] Validar usando o schema estrito, aplicando regras por formato (`app/format_specifications.py`) e verificando `cta_instagram` conforme `state["objetivo_final"]` com mapa `CTA_BY_OBJECTIVE` em `config.py`.
- [ ] Detectar duplicidades entre variações usando tuplas normalizadas (`headline`, `corpo`, `prompt_estado_*`).
- [ ] Persistir `deterministic_final_validation = {"grade", "issues", "normalized_payload", "source": "validator"}` e sincronizar `state["final_code_delivery"]` para o JSON normalizado.
- [ ] Registrar falhas sem exceções customizadas, preenchendo `deterministic_final_validation` como `fail` e chamando `append_delivery_audit_event`.
- [ ] Configurar `after_agent_callback=make_failure_handler("deterministic_final_validation", "JSON final não passou na validação determinística.")` e acionar `write_failure_meta` quando necessário.
- [ ] Atualizar `state["final_code_delivery"]` com a versão normalizada aprovada (string JSON) após validação bem-sucedida.

### 2.2 Utilitários de gating/reset
- [ ] Implementar `RunIfPassed` em `app/agents/gating.py` com `review_key`, `expected_grade` default `"pass"` e tratamento explícito para chaves ausentes registrando evento de reprovação.
- [ ] Implementar `ResetDeterministicValidationState` para limpar `approved_visual_drafts`, `deterministic_final_validation`, `deterministic_final_blocked`, `final_code_delivery_parsed` e artefatos correlatos quando o pipeline legado estiver ativo.

## 3. Fase 3 – Reorquestração do Pipeline (Etapas 5.3–5.5)
### 3.1 Reordenar o `execution_pipeline`
- [ ] Centralizar a criação do pipeline em `build_execution_pipeline(flag_enabled: bool)` retornando versões determinística e legado sem mutação em runtime.
- [ ] Converter `final_validation_loop` em `semantic_validation_loop` focado em coerência narrativa e manter `EscalationBarrier` após `EscalationChecker` no fluxo com flag ativa.
- [ ] Substituir `final_assembler` por estágio `SequentialAgent` composto com `FinalAssemblyGuardPre`, `final_assembler_llm` e `FinalAssemblyNormalizer` conforme responsabilidades do plano.
- [ ] Inserir `deterministic_validation_stage` logo após o assembler composto.
- [ ] Introduzir `RunIfPassed` para gatear o loop semântico, agentes de imagens e persistência, tratando ausência de chave como falha explícita.
- [ ] Manter `RunIfFailed` disponível para loops corretivos semânticos.
- [ ] Ajustar `make_failure_handler` para só manipular `deterministic_final_validation_*` quando o `state_key` corresponder, mantendo compatibilidade com resultados legados.
- [ ] Encadear `RunIfPassed` com loop semântico, `image_assets_agent` e `persist_final_delivery_agent`, envolvendo o loop com `EscalationBarrier` dedicado.
- [ ] Inserir `ResetDeterministicValidationState` antes do `final_assembler` no caminho legado (`flag=False`) para limpar resíduos ao alternar pipelines.
- [ ] Remover `after_agent_callback` do `final_assembler` e a chamada direta a `persist_final_delivery` no `ImageAssetsAgent` quando a flag estiver ativa, delegando persistência ao novo agente.
- [ ] Manter callbacks atuais no fluxo legado garantindo compatibilidade quando a flag estiver desativada.
- [ ] Revisar `ImageAssetsAgent` para sempre preencher `state["image_assets_review"]`, tratando `grade="skipped"` como passagem válida para persistência via `RunIfPassed`.
- [ ] Atualizar `FeatureOrchestrator` e endpoints de entrega para observar `deterministic_final_validation_failed`, `semantic_visual_review_failed` e `image_assets_review_failed`, mantendo compatibilidade com `final_validation_result_failed`.

### 3.2 Ajustes no `final_assembler`
- [ ] Implementar `FinalAssemblyGuardPre` para checar snippets `VISUAL_DRAFT` em `approved_code_snippets`, validar unicidade/legibilidade e popular `state['approved_visual_drafts']`.
- [ ] Reforçar o prompt de `final_assembler_llm` exigindo reutilização do snippet aprovado e retorno de JSON pronto.
- [ ] Fazer `FinalAssemblyNormalizer` gerar JSON canônico, alinhar com snippet reutilizado e atualizar `state["final_code_delivery"]` e `state["deterministic_final_validation"]` com `grade="pending"`/`source="normalizer"` antes do validador.

### 3.3 Revisor semântico e agentes auxiliares
- [ ] Criar `semantic_visual_reviewer` e `semantic_fix_agent` reutilizando o schema `Feedback`.
- [ ] Ajustar prompts para remover checagens estruturais e focar em coerência narrativa e aderência às especificações de formato.
- [ ] Garantir que o loop consuma o JSON normalizado em `state["final_code_delivery"]`, substituído pelo validador antes do revisor.
- [ ] Impedir execução do revisor quando `RunIfPassed` detectar falha do validador determinístico.
- [ ] Tratar ausência de chave de review como falha explícita em `RunIfPassed`, registrando evento via `append_delivery_audit_event`.
- [ ] Documentar o contrato de saída do `semantic_visual_reviewer` (`grade`, `issues`, `fix_instructions`) e limitar `semantic_fix_agent` a correções narrativas.
- [ ] Documentar endpoints afetados (`/delivery/final/meta`, `/delivery/final/download`, SSE, mensagens do `FeatureOrchestrator`) em planilha/checklist interno.
- [ ] Ajustar consumidores para checar flags `deterministic_final_validation_failed`, `semantic_visual_review_failed` e `image_assets_review_failed` antes de solicitar imagens.
- [ ] Garantir que `LandingPageStage` inicialize `state["landing_page_analysis_failed"] = False` e atualize para `True` quando aplicável, e que `StoryBrandQualityGate` preencha `state["storybrand_fallback_meta"] = {fallback_engaged, decision_path, trigger_reason, timestamp}`.

### 3.4 Observabilidade e persistência
- [ ] Registrar eventos estruturados via `append_delivery_audit_event` em guard, validador, revisor e persistência.
- [ ] Atualizar `persist_final_delivery_agent` para chamar `persist_final_delivery` uma vez, decidir anexos com base em `state["image_assets"]` e popular `state["image_assets_review"]` com `grade`/`issues` antes de liberar persistência; manter fluxo legado quando flag desativada.
- [ ] Propagar `deterministic_final_validation`, `semantic_visual_review` e `image_assets_review` para `write_failure_meta`/`clear_failure_meta`, preservando contrato de `final_delivery_status`.
- [ ] Atualizar `EnhancedStatusReporter` para divulgar novas etapas somente com a flag habilitada, preservando mensagens atuais quando desativada.
- [ ] Definir contrato dos eventos de auditoria (`stage`, `status`, `detail`, `deterministic_grade`, `storybrand_fallback_engaged`) e métricas associadas para monitoramento paralelo.
- [ ] Registrar e limpar `deterministic_final_blocked` para distinguir falhas do guard/normalizer de reprovações do LLM.

## 4. Fase 4 – Testes, Documentação e Qualidade (Etapas 5.6–6)
### 4.1 Testes unitários
- [ ] Criar `tests/unit/validators/test_final_delivery_validator.py` cobrindo sucesso/falha, inclusive cenários de fallback (`force_storybrand_fallback`/`storybrand_fallback_meta.fallback_engaged`).
- [ ] Adicionar testes para `FinalAssemblyNormalizer` garantindo reutilização do snippet aprovado, serialização de `contexto_landing` e falha para payloads parciais.
- [ ] Testar `collect_code_snippets_callback` enriquecendo metadados (`snippet_id`, `approved_at`).
- [ ] Validar comportamento de `FinalAssemblyGuardPre` para ausência/duplicidade de `VISUAL_DRAFT`, verificando `EventActions.escalate` e `deterministic_final_validation`.
- [ ] Testar comparações de unicidade entre variações (`headline`, `corpo`, `prompt_estado_*`).
- [ ] Cobrir `RunIfPassed`/`ResetDeterministicValidationState` em cenários pass/fail/ausente.

### 4.2 Testes de integração/regressão
- [ ] Simular pipeline (`final_assembler` → validador → loop semântico → imagens) exercitando `RunIfPassed`, `EscalationBarrier` e o novo agente de persistência.
- [ ] Incluir cenários com `force_storybrand_fallback=True`, `storybrand_fallback_meta` populado e objetivos distintos para garantir compatibilidade.
- [ ] Cobrir alternância da flag (`True`→`False`) assegurando limpeza de estado e restauração do fluxo legado.
- [ ] Adicionar verificações automáticas para divergências entre enums de CTA, specs e configurações (`config.py` vs `format_specifications`).
- [ ] Utilizar fakes de `LlmAgent`/`BaseAgent` (ex.: `FakeAgent`) para orquestrar `RunIfPassed`, `EscalationBarrier` e `SequentialAgent` sem chamadas reais ao LLM.
- [ ] Garantir que falha determinística bloqueie `ImageAssetsAgent` e registre motivo no audit trail.
- [ ] Exercitar `ImageAssetsAgent` com geração desativada ou JSON ausente produzindo `grade="skipped"` e liberando persistência conforme contrato.
- [ ] Verificar rollback da flag garantindo que `deterministic_final_validation`/`approved_visual_drafts` sejam limpos e evitando callbacks duplicados.
- [ ] Assegurar que `persist_final_delivery` seja chamado exatamente uma vez por execução e que `image_assets_review` reflita `pass`/`skipped` em cenários sem imagens.
- [ ] Cobrir cenários StoryBrand fallback avaliando `storybrand_fallback_meta` e `landing_page_analysis_failed` para validar relaxamento do schema.

### 4.3 Documentação e comunicação
- [ ] Atualizar README/playbooks com a nova ordem de validação e impactos nas APIs de entrega.
- [ ] Registrar notas de migração (remoção do `after_agent_callback` no `final_assembler`) e requisitos de testes para novos formatos/CTAs.
- [ ] Documentar a flag `ENABLE_DETERMINISTIC_FINAL_VALIDATION` com valores por ambiente, passos de rollout e plano de rollback.
- [ ] Atualizar guias de observabilidade e SSE com novas chaves (`deterministic_final_validation`, `deterministic_final_blocked`, `image_assets_review` com `skipped`) e mensagens do `FeatureOrchestrator`.

## 5. Checklist Operacional do Plano
- [ ] Fase 1 concluída com schema compartilhado, regras de fallback e helper de auditoria disponíveis sem duplicar enums.
- [ ] Fase 2 entregue com `FinalDeliveryValidatorAgent` atualizando `final_code_delivery`, produzindo audit/failure meta e respeitando exceções de fallback.
- [ ] Fase 3 finalizada com guard do assembler, `RunIfPassed`, pipeline reorquestrado, persistência única e endpoints/orchestrator ajustados.
- [ ] Fase 4 completa com testes (unitários, integração, regressão) e documentação cobrindo cenários de fallback e monitoramento de enums.
- [ ] Feature flag `enable_deterministic_final_validation` documentada, default `False`, com checklist de rollout e observabilidade definidos.

## 6. Estratégia de Testes (Detalhamento adicional)
### 6.1 Testes unitários adicionais
- [ ] Cobrir JSON válido com três variações completas.
- [ ] Garantir falha para `prompt_estado_intermediario` vazio.
- [ ] Garantir falha para `aspect_ratio` fora do permitido por formato.
- [ ] Validar rejeição de CTA incompatível com objetivo usando fixtures de `format_specifications`.
- [ ] Garantir falha para strings contendo apenas espaços.

### 6.2 Testes de integração adicionais
- [ ] Simular pipeline parcial (`final_assembler` → validador) com estado mockado.
- [ ] Confirmar bloqueio do `ImageAssetsAgent` quando a validação determinística falhar, com evento registrado.
- [ ] Exercitar `ImageAssetsAgent` produzindo `grade="skipped"`/`issues=[]` quando geração estiver desativada ou JSON ausente.
- [ ] Validar sessões com `force_storybrand_fallback=True` e `storybrand_fallback_meta.fallback_engaged=True`, confirmando normalização posterior.
- [ ] Exercitar estados da flag (`True`/`False`) garantindo ativação correta do pipeline novo e limpeza via `reset_deterministic_validation_state`.
- [ ] Verificar rollback da flag (habilitar → gerar entrega → desabilitar) confirmando limpeza de estado e ausência de callbacks duplicados.
- [ ] Verificar chamada única de `persist_final_delivery` por execução com `image_assets_review` refletindo `pass`/`skipped`.
- [ ] Cobrir cenários de fallback StoryBrand garantindo aceitação de campos vazios esperados pelo schema relaxado.

### 6.3 Regressão contínua
- [ ] Atualizar testes existentes que assumem ausência de validação determinística.
- [ ] Cobrir mapeamentos de CTA para objetivos suportados, detectando divergências futuras entre enums e specs.

## 7. Entregáveis
- [ ] Entregar código do validador determinístico integrado ao pipeline.
- [ ] Entregar novo agente revisor semântico com prompts revisados.
- [ ] Entregar ajustes no `final_assembler`/instruções conforme plano.
- [ ] Entregar helper de auditoria e persistência atualizada (`append_delivery_audit_event`, `persist_final_delivery_agent`).
- [ ] Entregar testes unitários e de integração previstos.
- [ ] Entregar atualização de documentação (README e playbooks internos quando aplicável).
