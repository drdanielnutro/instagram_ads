# Checklist — Plano v3 de Validação Determinística do JSON Final

> Convenção: `[ ]` pendente · `[>]` em andamento · `[x]` concluído
> Referência principal: `plano_validacao_json_v3.md`

## 1. Fase 1 – Fundamentos (Schemas, Auditoria, Config)
### 1.1 Schema e utilidades compartilhadas
- [x] Criar `app/schemas/final_delivery.py` com `StrictAdCopy`, `StrictAdVisual`, `StrictAdItem` (Pydantic estrito) e helpers `model_dump`/`from_state` (entrega em `app/schemas/final_delivery.py`).
- [x] Garantir suporte a `contexto_landing: str | dict[str, Any]` com validações e normalização apropriadas.
- [x] Centralizar limites/enums importando de `app/format_specifications.py`/`app/config.py`, evitando duplicação.

### 1.2 Auditoria e metadados de snippets
- [x] Criar `app/utils/audit.py` com `append_delivery_audit_event` reutilizável em guard, validador e persistência.
- [x] Estender `collect_code_snippets_callback` em `app/agent.py` para registrar `snippet_type`, `status`, `approved_at`, `snippet_id` e preencher `state['approved_visual_drafts']`.
- [x] Atualizar `app/utils/session-state.py` (classe `CodeSnippet`, `get_session_state`, `add_approved_snippet`) preservando os novos campos.

### 1.3 Configuração e dependências
- [x] Adicionar `enable_deterministic_final_validation` em `app/config.py` (default `False`) com suporte à env `ENABLE_DETERMINISTIC_FINAL_VALIDATION`.
- [x] Introduzir/centralizar `fallback_storybrand_max_iterations` e limites usados pelo schema conforme `plano_validacao_json_v3.md`.
- [x] Avaliar necessidade de atualizar `requirements.txt` para hashing/validação adicional (caso novos pacotes sejam requeridos). Nenhum pacote novo necessário.

> Notas Fase 1: Schema estrito reutiliza limites do `FORMAT_SPECS`, `contexto_landing` aceita texto ou dicionário normalizado e os snippets aprovados agora mantêm `snippet_type`/hash/`approved_visual_drafts`. Flag determinística disponível em `config` com `CTA_BY_OBJECTIVE` consolidado. Nenhuma dependência extra exigida.

## 2. Fase 2 – Validador Determinístico e Gating
### 2.1 `FinalDeliveryValidatorAgent`
- [x] Criar `app/validators/final_delivery_validator.py` realizando parsing único de `state['final_code_delivery']`.
- [x] Validar contra `StrictAd*`, limites de `app/format_specifications.py` e `config.CTA_BY_OBJECTIVE`, detectando duplicidades entre variações.
- [x] Popular `state['deterministic_final_validation']` com `{grade, issues, normalized_payload, source="validator"}` e sincronizar `state['final_code_delivery']` normalizado.
- [x] Registrar sucesso/falha via `append_delivery_audit_event` e acionar `make_failure_handler("deterministic_final_validation", ...)`/`write_failure_meta` quando necessário.

### 2.2 Utilitários de gating/reset
- [x] Criar `RunIfPassed` em `app/agents/gating.py` com `review_key` e `expected_grade="pass"`, realizando logging quando a chave estiver ausente/inválida.
- [x] Criar `ResetDeterministicValidationState` para limpar `approved_visual_drafts`, `deterministic_final_validation`, `deterministic_final_blocked`, `final_code_delivery_parsed` e correlatos.
- [x] Ajustar `app/agent.py` (faixa 1180-1235) para utilizar `RunIfPassed`/`ResetDeterministicValidationState` e preparar o pipeline para a flag.
- [x] Atualizar `app/utils/delivery_status.py` caso novos helpers sejam necessários ao validador.

> Notas Fase 2: Validador determinístico normaliza e audita `final_code_delivery`, grava meta de falha quando necessário e bloqueia pipeline por meio de `RunIfPassed`. Pipeline legado limpa estados determinísticos via `ResetDeterministicValidationState`; nenhum helper adicional exigido em `delivery_status` nesta etapa.

## 3. Fase 3 – Reorquestração do Pipeline de Execução
### 3.1 Montagem do pipeline
- [x] Implementar `build_execution_pipeline(flag_enabled: bool)` em `app/agent.py`, retornando versões determinística e legado sem mutação runtime.
- [x] Substituir `final_validation_loop` por `semantic_validation_loop` e manter `EscalationBarrier` após `EscalationChecker` quando a flag estiver ativa.
- [x] Introduzir `deterministic_validation_stage = SequentialAgent([...])` com `FinalDeliveryValidatorAgent` + `make_failure_handler` dedicado.
- [x] Encadear `RunIfPassed` para `semantic_validation_stage`, `image_assets_agent` e `PersistFinalDeliveryAgent`.
- [x] Inserir `ResetDeterministicValidationState` antes do assembler no caminho legado (flag desativada).

### 3.2 Guard, assembler e normalização
- [x] Criar `FinalAssemblyGuardPre` verificando snippets `VISUAL_DRAFT`, preenchendo `approved_visual_drafts` e emitindo `EventActions(escalate=True)` quando necessário.
- [x] Extrair `FinalAssemblerLLM` (agente dedicado ao prompt atual) e criar `FinalAssemblyNormalizer` para gerar JSON canônico, definindo `state['deterministic_final_validation'] = {grade: "pending", source: "normalizer"}`.
- [x] Garantir que `FinalAssembler` composto reutilize snippets aprovados e alimente o validador determinístico.

### 3.3 Persistência e agentes auxiliares
- [x] Criar `PersistFinalDeliveryAgent` encapsulando `persist_final_delivery`, atualizando audit trail e status.
- [x] Ajustar `ImageAssetsAgent` para cooperar com `RunIfPassed` e preencher `state['image_assets_review']` (incluindo `grade="skipped"`).
- [x] Atualizar `FeatureOrchestrator` e endpoints afetados para lidar com chaves `deterministic_final_validation_failed`, `semantic_visual_review_failed`, `image_assets_review_failed` mantendo compatibilidade legada.

> Notas Fase 3: Pipeline determinístico reconstruído com guard/normalizer, `build_execution_pipeline` entrega caminhos independentes e gating sequencial (`RunIfPassed`) cobre revisão semântica, imagens e persistência. Guard e normalizer alimentam `deterministic_final_validation`; `ImageAssetsAgent` fornece `image_assets_review` com suporte a `grade="skipped"` e persistência fica centralizada no novo agente.

## 4. Fase 4 – Observabilidade e Persistência
- [ ] Modificar `make_failure_handler` em `app/agent.py` para suportar chaves determinísticas sem sobrescrever fluxo legado.
- [ ] Atualizar `write_failure_meta`/`clear_failure_meta` em `app/utils/delivery_status.py` para incluir `deterministic_final_validation`, `semantic_visual_review`, `image_assets_review`.
- [ ] Ajustar `persist_final_delivery` (`app/callbacks/persist_outputs.py`) para gravar JSON normalizado, limpar chaves legadas e popular `state['final_delivery_status']` com origem determinística.
- [ ] Garantir preenchimento consistente de `state['storybrand_audit_trail']`, `state['storybrand_gate_metrics']`, `state['storybrand_fallback_meta']` e novos eventos de auditoria determinística.
- [ ] Atualizar `EnhancedStatusReporter` e endpoints `/delivery/final/*` para exibir status determinístico sem quebrar consumidores existentes.

## 5. Fase 5 – Testes Automatizados & QA
### 5.1 Testes unitários
- [ ] Adicionar `tests/unit/schemas/test_final_delivery_schema.py` cobrindo cenários de relaxamento/fallback.
- [ ] Criar `tests/unit/validators/test_final_delivery_validator.py` (pass/fail, duplicidade, CTA incoerente, fallback engajado).
- [ ] Criar `tests/unit/agents/test_final_assembly_guard.py` e `tests/unit/agents/test_final_assembly_normalizer.py` (happy-path/falha).
- [ ] Criar `tests/unit/agents/test_run_if_passed.py` e `tests/unit/agents/test_reset_deterministic_validation_state.py`.
- [ ] Criar `tests/unit/callbacks/test_persist_final_delivery.py` validando status determinístico e sanitização.

### 5.2 Integração, regressão e QA manual
- [ ] Adicionar `tests/integration/pipeline/test_deterministic_flow.py` cobrindo assembler → guard → normalizer → validador → loop semântico → imagens → persistência.
- [ ] Adicionar `tests/integration/pipeline/test_flag_toggle.py` validando alternância da flag e limpeza de estado.
- [ ] Atualizar ou criar testes de regressão para fluxos legados afetados (ex.: `tests/integration/test_agent.py`, `tests/integration/test_server_e2e.py`).
- [ ] Executar QA manual com JSON válido, inválido, fallback StoryBrand engajado e fluxo legado (flag off) registrando evidências.
- [ ] Confirmar que `make test` cobre novas suítes sem regressões.

## 6. Fase 6 – Documentação, Rollout e Observabilidade Externa
- [ ] Atualizar `README.md` e playbooks com ordem de validação, novos estados (`deterministic_final_validation`, `deterministic_final_blocked`, `image_assets_review`), flag `ENABLE_DETERMINISTIC_FINAL_VALIDATION` e estratégia de rollback.
- [ ] Criar/atualizar dashboards e alertas para `storybrand_gate_metrics`, `deterministic_final_validation`, `semantic_visual_review`, `image_assets_review` (Grafana/Looker conforme stack).
- [ ] Documentar impactos nos endpoints `/delivery/final/meta`, `/delivery/final/download` e SSE (novas mensagens/chaves).
- [ ] Planejar rollout gradual: ativar flag em ambiente canário, monitorar métricas e expandir após validação.
- [ ] Validar/documentar plano de rollback (desativar flag + limpeza de estado) e responsáveis pelos indicadores.

## 7. Checklist Final do Plano
- [ ] Verificar que todas as entregas distinguem criação vs. modificação conforme plano.
- [ ] Confirmar que dependências existentes citam caminhos/linhas relevantes.
- [ ] Registrar referências cruzadas indicando fases de criação quando aplicável.
- [ ] Consolidar resumos/diffs para arquivos modificados chave.
- [ ] Validar que critérios de aceitação por fase foram atendidos.
- [ ] Registrar riscos e mitigação conforme seção dedicada do plano.
- [ ] Certificar compatibilidade com o validador automático (`plan-code-validator`).
