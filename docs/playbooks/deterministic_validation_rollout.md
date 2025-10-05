# Playbook — Validação Determinística do JSON Final

## Visão Geral
A flag `ENABLE_DETERMINISTIC_FINAL_VALIDATION` liga um pipeline que monta, valida e persiste o JSON final somente após passar por guardas determinísticos. Quando ativa, a execução segue guard → normalizer → validador → revisão semântica → revisão de imagens → persistência; caso contrário, o fluxo legado com `final_validation_loop` continua disponível. 【F:app/config.py†L44-L85】【F:app/agent.py†L1834-L1883】

## Ordem de validação e estados-chave
1. **FinalAssemblyGuardPre** valida snippets `VISUAL_DRAFT` aprovados, bloqueando o pipeline se nada estiver disponível e anotando `deterministic_final_validation` com `grade="fail"`/`deterministic_final_blocked=True`. 【F:app/agent.py†L1288-L1316】
2. **FinalAssemblyNormalizer** reserializa o JSON, verifica campos críticos e publica `grade="pending"` até o validador completar, mantendo `deterministic_final_blocked=False` apenas quando tudo estiver consistente. 【F:app/agent.py†L1343-L1524】
3. **FinalDeliveryValidatorAgent** aplica o schema estrito e sincroniza `deterministic_final_validation`/`deterministic_final_blocked`, gravando issues e `failure_reason` em caso de reprovação. 【F:app/validators/final_delivery_validator.py†L71-L93】
4. **RunIfPassed** garante que somente execuções aprovadas avancem para revisão semântica, imagens e persistência (`expected_grade` aceita `"pass"` e `"skipped"` para imagens). 【F:app/agent.py†L1850-L1883】【F:app/agents/gating.py†L19-L81】
5. **PersistFinalDeliveryAgent** chama `persist_final_delivery` uma vez, atualizando `final_delivery_status` e sidecar `meta.json` com `deterministic_final_validation`, `semantic_visual_review`, `image_assets_review` e metadados StoryBrand. 【F:app/agent.py†L1537-L1569】【F:app/callbacks/persist_outputs.py†L98-L185】

Estados expostos:
- `deterministic_final_validation`, `deterministic_final_blocked`, `deterministic_final_validation_failed`, `deterministic_final_validation_failure_reason`.
- `semantic_visual_review`, `semantic_visual_review_failed`, `image_assets_review`, `image_assets_review_failed`.
- `delivery_audit_trail` com eventos de guard/validador/gates. 【F:app/agent.py†L1293-L1524】【F:app/agents/gating.py†L19-L81】【F:app/callbacks/persist_outputs.py†L98-L185】

## Observabilidade (Dashboards & Alertas)
Recomendações para Grafana/Looker:
- **Painel de estados determinísticos**: percentuais de sessões com `deterministic_final_validation.grade` = `pass`/`fail`/`pending`, tempo entre guard → validador usando `delivery_audit_trail`. 【F:app/callbacks/persist_outputs.py†L120-L185】
- **Monitor de bloqueios**: contagem de execuções com `deterministic_final_blocked=True` e motivo (`failure_reason`). 【F:app/agent.py†L1293-L1352】
- **Revisão semântica e imagens**: métricas para `semantic_visual_review.grade` e `image_assets_review.grade` (incluindo `skipped`) para distinguir falhas operacionais vs. toleradas. 【F:app/agent.py†L1850-L1883】【F:app/callbacks/persist_outputs.py†L98-L185】
- **Alertas**:
  - Criticidade alta se `deterministic_final_validation_failed` > 5% por 10 minutos.
  - Criticidade média para `image_assets_review.grade = fail` ou ausência de `image_assets_review` (indicando regressão do agente).
  - Criticidade baixa quando `storybrand_gate_metrics` deixa de ser persistido junto ao `final_delivery_status` (indicativo de callback quebrado). 【F:app/callbacks/persist_outputs.py†L120-L185】

**Responsáveis**:
- Squad Ads Backend → monitoria de `deterministic_final_validation`/`image_assets_review` e manutenção da flag.
- DataOps/Observability → manutenção de dashboards/alertas e tuning de thresholds.

## Endpoints e SSE
- `/delivery/final/meta` agora retorna `stage`, `grade`, `deterministic_final_validation`, `semantic_visual_review`, `image_assets_review` e metadados StoryBrand, retornando 503 quando só existe `failure_meta`. 【F:app/callbacks/persist_outputs.py†L98-L185】【F:app/routers/delivery.py†L63-L92】
- `/delivery/final/download` valida inline que todas as variações tenham URLs de imagem antes de responder, emitindo 424 em caso de lacunas. 【F:app/routers/delivery.py†L93-L173】
- SSE do `FeatureOrchestrator` inclui mensagens específicas para falhas determinísticas, semânticas e de imagens; consumidores devem mostrar o aviso apropriado e consultar os campos `*_failure_reason`. 【F:app/agent.py†L1917-L1955】

## Rollout Gradual
1. **Dev/QA** – ativar a flag apenas para squads internos, validar eventos SSE e sidecar `meta.json` após cenários pass/fail; ajustar dashboards/alertas antes de seguir. 【F:app/config.py†L44-L85】【F:app/callbacks/persist_outputs.py†L98-L185】
2. **Canário de produção** – ativar para <10% das sessões (via variável de ambiente por instância) e monitorar métricas críticas (`deterministic_final_validation_failed`, `image_assets_review.grade`) por 48h.
3. **Staging/Produção completa** – promover gradualmente garantindo que `RunIfPassed` mantenha gating adequado e que `clear_failure_meta` limpe resíduos após sucesso. 【F:app/agent.py†L1850-L1883】【F:app/callbacks/persist_outputs.py†L167-L185】

## Plano de Rollback
1. **Desativar flag** – ajustar `ENABLE_DETERMINISTIC_FINAL_VALIDATION=false` e reiniciar o serviço. 【F:app/config.py†L44-L85】
2. **Limpeza automática** – confirmar via logs de `ResetDeterministicValidationState` que chaves determinísticas foram removidas na primeira execução do pipeline legado. 【F:app/agent.py†L1874-L1883】【F:app/agents/gating.py†L83-L124】
3. **Verificação pós-rollback** – garantir que `/delivery/final/meta` continua respondendo (sem os novos campos) e que SSE volta a usar mensagens do `final_validation_loop`. Monitore se `image_assets_review` deixa de ser preenchido; isso é esperado no modo legado mas deve ser comunicado ao frontend.
4. **Responsáveis** – Squad Ads Backend coordena o toggle e validação; SRE confirma que alertas retornaram ao baseline.
