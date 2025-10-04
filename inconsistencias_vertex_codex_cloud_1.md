# Revisão das correções críticas

## Tarefa 1 — Saturação do Vertex AI (erro 429 RESOURCE_EXHAUSTED)
- **Status:** Conforme implementado. A utilidade `app/utils/vertex_retry.py` encapsula as chamadas com backoff exponencial, honra `Retry-After`, registra métricas de 429 e limita a concorrência via semáforo configurável (`VERTEX_CONCURRENCY_LIMIT`).
- **Evidências:**
  - Retentativas com backoff e respeito ao cabeçalho `Retry-After` em `call_with_vertex_retry`, incluindo registro de métricas e lançamento de `VertexRetryExceededError` após o número máximo de tentativas.【F:app/utils/vertex_retry.py†L25-L164】
  - Limite de concorrência global aplicado por `_semaphore` e usado em todas as chamadas ao Vertex dentro do contexto `limit_vertex_concurrency`.【F:app/utils/vertex_retry.py†L41-L74】【F:app/utils/vertex_retry.py†L94-L135】
  - Truncagem adaptativa head+tail antes de chamar a API e cache local opcional baseados em hash do input na `StoryBrandExtractor`.【F:app/tools/langextract_sb7.py†L456-L609】

## Tarefa 2 — Falha de permissão no bucket GCS (erro 403 storage.buckets.get)
- **Status:** Conforme implementado. O exporter de tracing trata erros de permissão/not found, desativa novas tentativas e respeita a flag `TRACING_DISABLE_GCS`; a documentação de IAM foi adicionada no `deployment/README.md` e o README principal orienta o uso da flag em ambientes locais.
- **Evidências:**
  - Tratamento resiliente de `Forbidden` durante verificação e upload, desabilitando o uso de GCS após a primeira falha e retornando mensagens explícitas.【F:app/utils/tracing.py†L41-L110】
  - Orientação operacional para conceder as roles necessárias via `gcloud storage buckets add-iam-policy-binding` no guia de deployment.【F:deployment/README.md†L13-L29】
  - Referência à flag `TRACING_DISABLE_GCS` para ambientes sem permissão no README principal.【F:README.md†L101-L110】

## Tarefa 3 — Melhor resposta ao frontend durante falhas Vertex
- **Status:** Conforme implementado. A falha persistida pelo callback injeta `final_delivery_status`, grava sidecar de erro e força fallback; o endpoint `/delivery/final/meta` retorna 503 com payload detalhado quando encontra o sidecar, e o frontend exibe mensagem orientando o usuário a aguardar.
- **Evidências:**
  - `_mark_storybrand_failure` atualiza `state['final_delivery_status']`, preenche métricas de gate, liga o fallback e persiste o sidecar da falha para consulta posterior.【F:app/callbacks/landing_page_callbacks.py†L18-L86】
  - Endpoint `/delivery/final/meta` devolve 503 com o detalhe armazenado sempre que existe sidecar de falha para o `session_id` requisitado.【F:app/routers/delivery.py†L71-L94】
  - A UI interpreta a resposta 503, armazena a mensagem de erro e apresenta um banner informando o usuário sobre a saturação do Vertex AI.【F:frontend/src/App.tsx†L210-L240】【F:frontend/src/App.tsx†L694-L723】

## Tarefa 4 — Observabilidade e Alertas
- **Status:** Implementação parcial. As métricas customizadas foram adicionadas e instrumentadas, porém não há evidências de criação ou documentação das políticas de alerta no Cloud Monitoring solicitadas (ausência de Terraform, scripts `gcloud` ou instruções específicas para os contadores `storybrand.vertex429.count` e `storybrand.delivery_failure.count`).
- **Evidências:**
  - Contadores `storybrand.vertex429.count`, `storybrand.fallback.triggered` e `storybrand.delivery_failure.count` definidos e utilizados pelo código.【F:app/utils/metrics.py†L7-L38】【F:app/utils/vertex_retry.py†L25-L164】【F:app/agents/storybrand_gate.py†L12-L115】【F:app/callbacks/landing_page_callbacks.py†L18-L106】
  - Ausência de instruções ou infraestrutura para alertas após varredura do repositório (`rg "alert" -g"*.md"` sem referências às métricas específicas e inexistência de Terraform relacionado a políticas de monitoramento).【dda983†L1-L18】【3b9a26†L1-L1】
