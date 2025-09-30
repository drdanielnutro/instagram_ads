# Auditoria das correções críticas (correcoes_criticas.md)

## 1. Saturação do Vertex AI (erro 429 RESOURCE_EXHAUSTED)
**Conclusão:** Implementada conforme especificação.

**Justificativa:**
- O utilitário `app/utils/vertex_retry.py` aplica backoff exponencial com jitter, respeita `Retry-After` e limita concorrência com `threading.Semaphore`, satisfazendo os itens 1.1 e 1.2 (`VERTEX_CONCURRENCY_LIMIT`). Referências: `app/utils/vertex_retry.py:32-161`.
- A truncagem adaptativa head+tail está em `_prepare_input`, usada antes de chamar o LangExtract (`app/tools/langextract_sb7.py:446-495`), atendendo ao item 1.3.
- O cache opcional, chaveado por hash e controlado por `STORYBRAND_CACHE_ENABLED`, é inicializado e consultado antes das chamadas ao Vertex e persistido após sucesso (`app/tools/langextract_sb7.py:552-580`; `app/utils/cache.py:1-55`).
- O pipeline propaga `VertexRetryExceededError` para o callback, que converte a falha em estado e métricas (`app/tools/langextract_sb7.py:571-586`; `app/callbacks/landing_page_callbacks.py:212-220`), garantindo o fallback descrito na estratégia.

## 2. Falha de permissão no bucket GCS (erro 403 storage.buckets.get)
**Conclusão:** Implementação parcial; requisitos 2.2 e 2.3 foram cumpridos, mas não há evidência do ajuste IAM (2.1).

**Justificativa:**
- O exporter agora trata `Forbidden`/falhas de bucket, desabilita novas tentativas e respeita `TRACING_DISABLE_GCS`, conforme solicitado no item 2.2 (`app/utils/tracing.py:68-153`).
- A documentação explica como conceder `roles/storage.objectCreator` e `roles/storage.legacyBucketReader`, além de instruir a usar `TRACING_DISABLE_GCS` em ambientes sem acesso (`deployment/README.md:13-27`).
- Não há como verificar no repositório se as permissões IAM foram efetivamente aplicadas no projeto GCP (item 2.1). Ausência de artefatos de automação ou registros implica que esse subitem permanece não comprovado.

## 3. Melhor resposta ao frontend durante falhas Vertex
**Conclusão:** Funcionalidade entregue, porém o ponto 3.1 diverge do local indicado no plano.

**Justificativa:**
- A propagação de falha (`final_delivery_status`, `storybrand_gate_metrics.vertex_error`, `force_storybrand_fallback`) ocorre no callback `process_and_extract_sb7` (`app/callbacks/landing_page_callbacks.py:21-62`), não em `app/agent.py` como descrito. Embora o efeito seja equivalente, o local difere do documento e pode impactar a rastreabilidade pretendida.
- O endpoint `/delivery/final/meta` devolve 503 e inclui o payload de erro quando existe sidecar de falha, cumprindo o item 3.2 (`app/routers/delivery.py:99-116`; `app/utils/delivery_status.py:22-61`).
- O frontend trata respostas 503, exibe mensagem ao usuário e evita polling infinito (`frontend/src/App.tsx:207-235` e `frontend/src/App.tsx:680-719`), alinhando-se ao item 3.3.

## 4. Observabilidade e Alertas
**Conclusão:** Incompleta; métricas foram adicionadas, mas não há evidência das políticas de alerta do item 4.2.

**Justificativa:**
- Os contadores `storybrand.vertex429.count`, `storybrand.fallback.triggered` e `storybrand.delivery_failure.count` foram definidos e usados nos pontos do fluxo correspondentes (`app/utils/metrics.py:7-43`; `app/utils/vertex_retry.py:142-147`; `app/agents/storybrand_gate.py:14-125`; `app/callbacks/landing_page_callbacks.py:21-62`).
- O repositório não contém Terraform, scripts ou documentação específica que crie as políticas de alerta em Cloud Monitoring pedidas no item 4.2; apenas recomendações genéricas aparecem em `vertex_doc_limites.md`, sem configurar os contadores personalizados. Portanto, esse subitem permanece não evidenciado.
