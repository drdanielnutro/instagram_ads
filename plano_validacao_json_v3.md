# Plano v3 — Validação Determinística do JSON Final de Ads

## Visão Geral
- **Objetivo**: instaurar validação determinística e auditoria completa sobre o JSON final de anúncios antes de qualquer etapa semântica ou geração de imagens.
- **Resultados esperados**: reduzir falsos positivos de LLM, garantir contratos mínimos, sincronizar estado/persistência e manter compatibilidade com o fluxo legado por meio de feature flag.
- **Princípios**: distinguir claramente entregas vs. dependências, preservar comportamento atual quando a flag estiver desabilitada e fornecer observabilidade rastreável.

---
## Fase 1 – Fundamentos (Schemas, Auditoria e Configuração)

### Entregáveis
- Criar `app/schemas/final_delivery.py` com modelos estritos `StrictAdCopy`, `StrictAdVisual`, `StrictAdItem` e funções auxiliares (`model_dump`, `from_state`) tratando `contexto_landing: str | dict[str, Any]`.
- Criar `app/utils/audit.py` com helper `append_delivery_audit_event(state: dict, *, stage: str, status: str, detail: str | None = None, **extras) -> None` reutilizável por guard/validator/persistência.
- Modificar `app/agent.py:120-150` (faixa aproximada) para estender `collect_code_snippets_callback` registrando `snippet_type`, `status`, `approved_at`, `snippet_id` (SHA-256) e popular `state['approved_visual_drafts']`.
- Modificar `app/utils/session-state.py:33-138` para preservar os novos campos persistidos (`snippet_type`, `approved_at`, `snippet_id`, `approved_visual_drafts`) quando a flag determinística estiver ativa.
- Modificar `app/config.py:120-215` adicionando:
  - Flag `enable_deterministic_final_validation: bool = False` com suporte a `ENABLE_DETERMINISTIC_FINAL_VALIDATION`.
  - Config `fallback_storybrand_max_iterations` (se ainda não existir) e centralização dos limites utilizados pelo schema.
- Atualizar `requirements.txt` se novos pacotes forem necessários para hashing ou validação adicional (não previsto nesta fase).

### Dependências existentes
- `AdVisual`/`AdItem` definidos em `app/agent.py:63-130` (servem de referência para o schema estrito).
- Utilitário `hashlib.sha256` (biblioteca padrão).
- Estrutura atual de sessão (classe `CodeSnippet`, helpers `get_session_state`, `add_approved_snippet`) em `app/utils/session-state.py:33-138`.

### Integrações planejadas
1. Fase 2 consumirá `StrictAd*` e o helper de auditoria para o `FinalDeliveryValidatorAgent`.
2. Fase 3 usará `approved_visual_drafts` para o guard e o normalizer do assembler.
3. Flag `enable_deterministic_final_validation` controlará o novo builder do pipeline (Fase 3) e os testes de alternância (Fase 5).

### Critérios de aceitação
- [ ] Arquivo `app/schemas/final_delivery.py` criado com modelos estritos e métodos auxiliares.
- [ ] `append_delivery_audit_event` grava eventos sem duplicar lógica existente.
- [ ] `collect_code_snippets_callback` registra metadados adicionais e mantém compatibilidade com consumidores atuais.
- [ ] `session-state` persiste e recupera os novos campos sem perdas quando a flag estiver ativa.
- [ ] Flag `enable_deterministic_final_validation` disponível em `config` e via variável de ambiente.

---
## Fase 2 – Validador Determinístico e Gating Utilities

### Entregáveis
- Criar `app/validators/final_delivery_validator.py` contendo `FinalDeliveryValidatorAgent` que:
  - Faz parsing único de `state['final_code_delivery']`.
  - Valida contra `StrictAd*`, limites de `app/format_specifications.py` e `config.CTA_BY_OBJECTIVE`.
  - Detecta duplicidades (tuplas `headline`, `corpo`, prompts) e registra resultado em `state['deterministic_final_validation']` com `grade`, `issues`, `normalized_payload`, `source="validator"`.
  - Chama `append_delivery_audit_event` para sucesso/falha.
- Criar utilitário `RunIfPassed` em `app/agents/gating.py` (novo) com parâmetros `review_key`, `expected_grade="pass"`, executando agente encapsulado apenas quando a avaliação determinística (ou semântica) passar.
- Criar utilitário `ResetDeterministicValidationState` em `app/agents/gating.py` para limpar chaves (`approved_visual_drafts`, `deterministic_final_validation`, `deterministic_final_blocked`, `final_code_delivery_parsed`).
- Modificar `app/agent.py:1180-1235` para usar `RunIfPassed`/`ResetDeterministicValidationState` no pipeline (flag desabilitada vs habilitada).
- Atualizar `app/utils/delivery_status.py:12-60` se necessário para expor helpers usados pelo validador.

### Dependências existentes
- Base class `BaseAgent` exposta por `google.adk.agents` e utilitários de gating já disponíveis.
- `config.CTA_BY_OBJECTIVE` ou mapa equivalente (criar se ainda não existir; caso ausente, incluí-lo nesta fase).
- Função `write_failure_meta` definida em `app/utils/delivery_status.py:20-47` e helper `make_failure_handler` em `app/agent.py:178-185`.

### Integrações planejadas
1. Fase 3 usará `FinalDeliveryValidatorAgent` dentro de `deterministic_validation_stage`.
2. `RunIfPassed` encapsulará `semantic_validation_loop`, `image_assets_agent` e `persist_final_delivery_agent` (Fase 3).
3. Tests (Fase 5) validarão sucesso/falha do validador e gating.

### Critérios de aceitação
- [ ] `FinalDeliveryValidatorAgent` normaliza a carga e popula `state['deterministic_final_validation']` corretamente.
- [ ] `RunIfPassed` trata ausência de chave como falha e registra evento via `append_delivery_audit_event`.
- [ ] `ResetDeterministicValidationState` limpa todos os artefatos quando a flag estiver desativada.
- [ ] Nenhum agente existente quebra quando a flag permanece `False`.

---
## Fase 3 – Reorquestração do Pipeline de Execução

### Entregáveis
- Implementar `build_execution_pipeline(flag_enabled: bool)` em `app/agent.py` retornando duas versões do pipeline (determinístico vs legado) sem mutação em runtime.
- Criar `FinalAssemblyGuardPre` (`app/agent.py`) para validar presença/qualidade de snippets `VISUAL_DRAFT`, preenchendo `state['approved_visual_drafts']`, atualizando `state['deterministic_final_validation']` em caso de bloqueio e emitindo `EventActions(escalate=True)`.
- Extrair o prompt LLM atual do `final_assembler` para um novo agente `FinalAssemblerLLM` (mesmo arquivo), responsável exclusivamente por chamar o modelo e retornar as três variações (mantém instruções atuais).
- Modificar `final_assembler` para rodar como estágio composto: `FinalAssemblyGuardPre` → `FinalAssemblerLLM` (novo) → `FinalAssemblyNormalizer` (novo) que sincroniza JSON final com snippet aprovado e define `state['deterministic_final_validation'] = {grade: "pending", source: "normalizer"}`.
- Introduzir `deterministic_validation_stage = SequentialAgent([...])` contendo `FinalDeliveryValidatorAgent + make_failure_handler("deterministic_final_validation", ...)`.
- Converter `final_validation_loop` em `semantic_validation_loop` (apenas coerência narrativa) seguido por `EscalationBarrier` dedicado.
- Encadear `RunIfPassed` em série:
  - `RunIfPassed(review_key="deterministic_final_validation", agent=semantic_validation_stage)`.
  - `RunIfPassed(review_key="semantic_visual_review", agent=image_assets_agent)`.
- Criar `PersistFinalDeliveryAgent` (`app/agent.py` ou módulo dedicado) que invoca `persist_final_delivery` exatamente uma vez, atualiza audit trail e publica status; encadear com `RunIfPassed(review_key="image_assets_review", agent=persist_final_delivery_agent)`.
- Inserir `ResetDeterministicValidationState` antes do assembler no caminho legado (`flag=False`).

### Dependências existentes
- `SequentialAgent` e `LoopAgent` exportados por `google.adk.agents` (importados em `app/agent.py:24-33`).
- `EscalationBarrier` e `EscalationChecker` implementados em `app/agent.py:202-238`.
- `ImageAssetsAgent` (`app/agent.py:300-577`).
- `persist_final_delivery` callback em `app/callbacks/persist_outputs.py:35-141` (será encapsulado pelo novo agente).

### Modificações planejadas (diff resumido)
```diff
# app/agent.py (execução principal)
-if config.enable_deterministic_final_validation:
-    execution_pipeline = SequentialAgent([...])
-else:
-    execution_pipeline = SequentialAgent([...])
+execution_pipeline = build_execution_pipeline(
+    flag_enabled=config.enable_deterministic_final_validation
+)
```

### Critérios de aceitação
- [ ] Pipeline determinístico bloqueia agentes posteriores quando `deterministic_final_validation.grade != "pass"`.
- [ ] Fluxo legado permanece funcional quando a flag estiver `False`.
- [ ] Guard/Normalizer/FinalAssemblerLLM atualizam `state` e audit trail apropriadamente.
- [ ] `PersistFinalDeliveryAgent` encapsula o callback e respeita o gating por `RunIfPassed`.
- [ ] `build_execution_pipeline` é testável isoladamente (Fase 5).

---
## Fase 4 – Observabilidade e Persistência

### Entregáveis
- Modificar `make_failure_handler` (`app/agent.py:178-185`) para lidar com chaves determinísticas sem sobrescrever resultados do caminho legado.
- Atualizar `write_failure_meta`/`clear_failure_meta` (`app/utils/delivery_status.py`) para persistir status `deterministic_final_validation`, `semantic_visual_review`, `image_assets_review`.
- Modificar `persist_final_delivery` (`app/callbacks/persist_outputs.py:35-141`) para:
  - Gravar JSON normalizado (pós-validador) e limpar chaves legadas quando o pipeline determinístico estiver ativo.
  - Popular `state['final_delivery_status']` com origem determinística (campos `stage`, `grade`).
- Popular `state['storybrand_audit_trail']`, `state['storybrand_gate_metrics']` e `state['storybrand_fallback_meta']` nos pontos atuais (confirmar dependências da Fase 1) e anexar novas entradas na validação determinística.
- Atualizar `EnhancedStatusReporter` e endpoints `/delivery/final/*` para expor status determinístico e mensagens diferenciadas.

### Dependências existentes
- Logs estruturados (`logger.log_struct`) e telemetria já expostos em `app/utils/tracing.py:62-105` e nos endpoints principais de `app/server.py:129-410`.
- `StoryBrandQualityGate` (`app/agents/storybrand_gate.py:70-140`) já preenchendo `storybrand_fallback_meta`.
- Mensagens do `FeatureOrchestrator` e streaming SSE alinhados em `app/agent.py:1911-1955` e `app/server.py:129-410`.

### Critérios de aceitação
- [ ] Audit trail registra eventos para guard, validador, loop semântico e persistência.
- [ ] Metas de falha diferenciam pipeline determinístico vs legado.
- [ ] Status API e SSE refletem novos campos sem quebrar consumidores antigos.

---
## Fase 5 – Testes Automatizados & QA

### Entregáveis
- **Unitários**:
  - `tests/unit/schemas/test_final_delivery_schema.py` cobrindo relaxamento de fallback.
  - `tests/unit/validators/test_final_delivery_validator.py` (casos pass/fail, duplicidade, CTA incoerente, fallback engajado).
  - `tests/unit/agents/test_final_assembly_guard.py` e `test_final_assembly_normalizer.py` (cenários happy-path/falha).
  - `tests/unit/agents/test_run_if_passed.py` e `test_reset_deterministic_validation_state.py`.
  - `tests/unit/callbacks/test_persist_final_delivery.py` (status determinístico, sanitização).
- **Integração**:
  - `tests/integration/pipeline/test_deterministic_flow.py`: assembler → guard → normalizer → validador → loop semântico → imagens → persistência, com mocks de agentes LLM.
  - `tests/integration/pipeline/test_flag_toggle.py`: habilita flag → gera entrega → desabilita flag → confirma limpeza de estado.
- **Regressão**:
  - Atualizar suites existentes que assumem fluxo legado (ex.: `tests/integration/test_agent.py`, `tests/integration/test_server_e2e.py`) ou criar cobertura equivalente se o cenário não estiver contemplado.
- **QA manual**:
  - Cenários com JSON válido, JSON inválido, fallback StoryBrand engajado e pipeline legado (flag off).

### Critérios de aceitação
- [ ] `make test` cobre novas suites sem regressões.
- [ ] Testes de integração garantem bloqueio apropriado do pipeline quando a validação falha.
- [ ] Roteiro manual documentado com evidências.

---
## Fase 6 – Documentação, Rollout e Observabilidade Externa

### Entregáveis
- Atualizar `README.md` e playbooks internos com: ordem de validação, novos estados (`deterministic_final_validation`, `deterministic_final_blocked`, `image_assets_review`), variável `ENABLE_DETERMINISTIC_FINAL_VALIDATION` e estratégia de rollback.
- Criar/atualizar dashboards/alertas para `storybrand_gate_metrics`, `deterministic_final_validation`, `semantic_visual_review` e `image_assets_review` (Grafana/Looker, conforme stack atual).
- Documentar impacto nos endpoints `/delivery/final/meta`, `/delivery/final/download` e SSE (mensagens novas, chaves adicionais).
- Planejar rollout gradual: ativar flag em ambiente canário, monitorar métricas, expandir para produção.

### Critérios de aceitação
- [ ] Documentação revisada/validadas pelo time.
- [ ] Plano de rollback definido (desativar flag + limpeza de estado).
- [ ] Indicadores/alertas configurados ou backlogados com responsáveis.

---
## Dependências Externas & Configurações
- `pydantic` já disponível (`pyproject.toml`).
- `hashlib` (stdlib) para geração de `snippet_id`.
- `make test`, `make lint` já configurados no `Makefile:120-180`.
- Feature flags existentes: `ENABLE_STORYBRAND_FALLBACK`, `ENABLE_NEW_INPUT_FIELDS` (mantidas).

---
## Riscos & Mitigações
| Risco | Mitigação |
|-------|-----------|
| Schema rígido bloqueando cenários legítimos | Implementar condicionais de relaxamento (fallback StoryBrand) e cobrir com fixtures reais nos testes. |
| Duplicação de regras com prompts | Centralizar limites/enums em `app/format_specifications.py` e importar tanto no schema quanto nos prompts/validator. |
| Impacto de performance com validação extra | Validador opera sobre 3 variações; monitorar métricas e otimizar se necessário. |
| Inconsistência com `final_validation_loop` legado | `RunIfPassed` e `ResetDeterministicValidationState` asseguram compatibilidade e limpeza; testes de alternância cobrem rollback. |
| Observabilidade insuficiente | `append_delivery_audit_event` e atualizações de status/alertas (Fase 4/6) fornecem rastreabilidade. |

---
## Fase 7 – Consolidação e Evidências

### Entregas validadas (criação vs. modificação)
| Item | Fase | Tipo | Evidência |
| --- | --- | --- | --- |
| `app/schemas/final_delivery.py` | Fase 1 | Criação | Modelos estritos (`StrictAdItem`, `StrictAdCopy`, `StrictAdVisual`) e helpers de normalização. `app/schemas/final_delivery.py:1-181` |
| `app/utils/audit.py` | Fase 1 | Criação | `append_delivery_audit_event` registra eventos com metadados e timestamp. `app/utils/audit.py:1-41` |
| `app/utils/session_state.py` / `session-state.py` | Fase 1 | Modificação | Persistência de `approved_visual_drafts` e metadados de snippets. `app/utils/session_state.py:10-90`; `app/utils/session-state.py:131-176` |
| `app/validators/final_delivery_validator.py` | Fase 2 | Criação | Validação determinística popula `state['deterministic_final_validation']` e normaliza payload. `app/validators/final_delivery_validator.py:26-192` |
| `app/agents/gating.py` | Fase 2 | Criação | `RunIfPassed` e `ResetDeterministicValidationState` aplicam gating e limpeza do estado. `app/agents/gating.py:19-124` |
| `app/agent.py` | Fases 3-4 | Modificação | Guard, normalizer, pipeline determinístico e `FeatureOrchestrator` atualizados. `app/agent.py:1237-1888` |
| `app/callbacks/persist_outputs.py` | Fase 4 | Modificação | Persistência escreve `final_delivery_status` determinístico e sidecar `meta`. `app/callbacks/persist_outputs.py:35-189` |

### Dependências existentes auditadas
- Logs estruturados e telemetria conferidos nos módulos referenciados (`app/utils/tracing.py:62-105`, `app/server.py:129-410`).
- Gate StoryBrand reutilizado conforme previsto (`app/agents/storybrand_gate.py:70-140`).
- `FeatureOrchestrator` e mensagens SSE existentes garantem compatibilidade com novos estados (`app/agent.py:1911-1955`).

### Referências cruzadas entre fases
- Modelos estritos da Fase 1 são consumidos pelo validador determinístico da Fase 2 (`app/validators/final_delivery_validator.py:17-71`).
- Auditoria (`append_delivery_audit_event`) criada na Fase 1 alimenta guard, normalizer e persistência nas Fases 3-4 (`app/agent.py:1301-1568`).
- Gating utilitário da Fase 2 controla pipeline montado na Fase 3 (`app/agent.py:1843-1888`).
- Persistência atualizada na Fase 4 expõe dados usados por documentação e rollout (README/playbook). `app/callbacks/persist_outputs.py:120-189`.

### Resumo de arquivos modificados chave
| Arquivo | Destaques | Linhas |
| --- | --- | --- |
| `app/agent.py` | `FinalAssemblyGuardPre`, normalizer, `PersistFinalDeliveryAgent` e `build_execution_pipeline` reorganizam o fluxo determinístico antes da revisão semântica/imagens. | `app/agent.py:1237-1888` |
| `app/validators/final_delivery_validator.py` | Normaliza variações, detecta duplicidades e sincroniza flags/falhas determinísticas. | `app/validators/final_delivery_validator.py:26-195` |
| `app/callbacks/persist_outputs.py` | Persiste JSON normalizado, grava meta com estados determinísticos/StoryBrand e limpa indicadores legados. | `app/callbacks/persist_outputs.py:35-189` |
| `tests/integration/pipeline/test_deterministic_flow.py` | Exercita guard → normalizer → validador → gating → persistência com checagem de `final_delivery_status`. | `tests/integration/pipeline/test_deterministic_flow.py:80-136` |
| `tests/integration/pipeline/test_flag_toggle.py` | Confirma alternância do pipeline e limpeza do estado determinístico. | `tests/integration/pipeline/test_flag_toggle.py:27-54` |

### Critérios de aceitação verificados
- Suites de teste cobrem pipelines determinístico e legado (`tests/integration/pipeline/test_deterministic_flow.py:80-136`, `tests/integration/pipeline/test_flag_toggle.py:27-54`).
- QA manual registra cenários válido/inválido/fallback/legado conforme requerido na Fase 5 (`docs/qa_manual_fase5.md:5-21`).
- Documentação e playbook descrevem estados, endpoints e rollout (`README.md:436-469`, `docs/playbooks/deterministic_validation_rollout.md:1-45`).
- Riscos permanecem atualizados sem novas descobertas durante a revisão (ver tabela acima).

### Compatibilidade com `plan-code-validator`
- Última execução do validador registrou alinhamento sem achados (`validation_report_plano_v3.json`).
- Relatório em Markdown espelha cobertura e métricas (`validation_report_plano_v3.md`).

---
## Checklist Final do Plano
- [x] Entregas usam verbos declarativos e distinguem criação/modificação.
- [x] Dependências existentes citam caminho/linhas quando relevante.
- [x] Referências cruzadas indicam fase de criação (“criado na Fase X”).
- [x] Diffs/resumos fornecidos para arquivos modificados.
- [x] Critérios de aceitação definidos por fase.
- [x] Riscos documentados com mitigação.
- [x] Plano compatível com validação automática (`plan-code-validator`).

---
## Linha do Tempo Sugerida
1. **Fase 1** – Fundamentos (schemas, audit trail, flag) – Semana 1.
2. **Fase 2** – Validador determinístico & gating – Semana 1/2.
3. **Fase 3** – Reorquestração do pipeline – Semana 2/3.
4. **Fase 4** – Observabilidade/persistência – Semana 3.
5. **Fase 5** – Testes automatizados & QA – Semana 3/4.
6. **Fase 6** – Documentação & rollout – Semana 4, antes do canário.

Sequenciar dessa forma garante que os utilitários estejam disponíveis antes de integrar com o pipeline e que as validações/documentação estejam concluídas antes do rollout restrito.
