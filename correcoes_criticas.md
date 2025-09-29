# Plano de Correções Críticas

## 1. Saturação do Vertex AI (erro 429 RESOURCE_EXHAUSTED)
- **Erro detectado:** `google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED` ao executar o pipeline StoryBrand (logs apontam para chamadas Vertex AI em `app/tools/langextract_sb7.py`).
- **Correção proposta:**
  1. **Limitar concorrência**: adicionar controle de concorrência (semáforo/asyncio.Lock) nas chamadas de geração dentro de `app/tools/langextract_sb7.py` e/ou `app/agents/storybrand_gate.py` para garantir um número máximo de requisições ativas ao Vertex AI (ex.: configurable via `VERTEX_CONCURRENCY_LIMIT`).
  2. **Retry com backoff**: encapsular as chamadas em um utilitário (ex.: `app/utils/vertex_retry.py`) que aplique `retry` exponencial com jitter, respeite `Retry-After` do cabeçalho e desista após N tentativas, disparando fallback StoryBrand.
  3. **Truncagem adaptativa**: revisar `StoryBrand` HTML/prompt em `app/tools/langextract_sb7.py` para aplicar truncagem dinâmica baseada no tamanho do HTML recebido, evitando exceder limites de tokens.
  4. **Cache local opcional**: usar `functools.lru_cache` ou persistência leve em `app/utils/cache.py` para reutilizar respostas do Vertex AI quando `landing_page_url` + parâmetros forem iguais.
- **Justificativa técnica:**
  - O 429 decorre de excesso de requisições ou insumos grandes; controlar concorrência resolve a causa imediata reduzindo pressão na API.
  - Retries com backoff são recomendados pelo Vertex AI para lidar temporariamente com limits, evitando falhas definitivas.
  - Truncagem e cache reduzem payloads enviados e reutilizam resultados, diminuindo consumo de quota.
- **Estratégia escolhida:** A combinação ataque-causa (controle + truncagem) + mitigação temporária (retry/backoff) garante estabilização do sistema e melhora resiliência sem depender de expansão de quota. Também respeita restrições de custo/latência.

## 2. Falha de permissão no bucket GCS (erro 403 storage.buckets.get)
- **Erro detectado:** `google.api_core.exceptions.Forbidden: ... does not have storage.buckets.get access` durante exportação de spans (`app/utils/tracing.py` linha ~108).
- **Correção proposta:**
  1. **Ajustar IAM**: conceder à service account `instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com` as roles mínimas `roles/storage.objectCreator` e `roles/storage.objectViewer` (ou role custom equivalente) no bucket `instagram-ads-472021-facilitador-logs-data`. Terraform/CLI: `gcloud storage buckets add-iam-policy-binding gs://instagram-ads-472021-facilitador-logs-data --member=serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com --role=roles/storage.objectCreator`.
  2. **Tratamento resiliente**: atualizar `CloudTraceLoggingSpanExporter.store_in_gcs` (`app/utils/tracing.py`) para capturar exceções `Forbidden`/`NotFound` e registrar aviso sem tentar revalidar continuamente, incluindo flag `TRACING_DISABLE_GCS=true` caso o bucket não esteja configurado.
  3. **Documentar credenciais**: registrar no README e/ou `deployment/README.md` os passos de IAM para ambientes locais, evitando configuração incompleta.
- **Justificativa técnica:**
  - Sem permissão adequada, o exporter nunca conseguirá criar/ver blobs, gerando exceções e poluindo logs. Ajustar IAM é a correção definitiva.
  - Tratamento resiliente evita quedas/tentativas repetidas enquanto a permissão não é liberada, melhorando DX.
  - Documentação formal previne regressões em novos ambientes.
- **Estratégia escolhida:** Conceder permissões mínimas resolve a raiz (impossibilidade de acessar o bucket). O fallback no código protege ambientes onde o bucket não será habilitado (desenvolvimento isolado) sem comprometer monitoramento em produção.

## 3. Melhor resposta ao frontend durante falhas Vertex
- **Erro detectado:** Polling contínuo do frontend para `/delivery/final/meta` retornando 404, mesmo após falha do pipeline devido ao 429.
- **Correção proposta:**
  1. **Propagar falha ao estado**: quando o Vertex AI retornar erro definitivo, atualizar `state['storybrand_gate_metrics']` e `state['final_delivery_status']` em `app/agent.py` para refletir `failed` e incluir motivo.
  2. **Endpoint 404 inteligente**: ajustar `app/server.py` (handler de `/delivery/final/meta`) para responder 503 com payload explicativo quando a sessão terminou em erro conhecido, evitando retries intermináveis.
  3. **UI feedback**: no frontend (`frontend/src/pages/App/`), consumir status `failed` e exibir mensagem orientando usuário a tentar novamente mais tarde.
- **Justificativa técnica:**
  - Sem sinalização explícita, o frontend assume que o artefato ainda será produzido, causando spam no endpoint.
  - Propagar estado de erro melhora UX e reduz carga no backend.
- **Estratégia escolhida:** Atualizar fluxo de estado garante comunicação robusta entre backend e frontend, alinhado ao tratamento de quotas Vertex.

## 4. Observabilidade e Alertas
- **Erro relacionado:** Ausência de visibilidade pró-ativa sobre saturação do Vertex AI e falhas de logging.
- **Correção proposta:**
  1. **Métricas customizadas**: instrumentar contadores `storybrand.vertex429.count`, `storybrand.fallback.triggered` em `app/utils/metrics.py` e exportá-los via OpenTelemetry.
  2. **Alerting**: criar política no Cloud Monitoring alertando quando `storybrand.vertex429.count` ultrapassar limiar e quando `delivery_failure` ocorrer repetidamente.
- **Justificativa técnica:**
  - Monitoramento permite agir antes de impactos críticos, alinhado a operações confiáveis.
- **Estratégia escolhida:** Completa o ciclo de melhoria, garantindo que novas saturações/permissões sejam detectadas rapidamente.

---
**Proprietário sugerido:** Time GêneroStoryBrand
**Dependências externas:** Ajuste de IAM GCS, quota Vertex AI
**Status:** pending
