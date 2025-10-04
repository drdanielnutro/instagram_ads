# Inconsistências na execução do "Plano de Correções Críticas"

## 1. Saturação do Vertex AI (erro 429 RESOURCE_EXHAUSTED)
**Resultado da revisão:** não implementado conforme especificação.

- Não existe o utilitário `app/utils/vertex_retry.py` nem outro módulo dedicado a retentativas com backoff, indicando que o item (1) do plano não foi executado.【5ac2ea†L1-L4】【12346a†L1-L2】
- O método `StoryBrandExtractor.extract` continua invocando `lx.extract` diretamente, sem qualquer lógica de retry, controle de concorrência (semáforos/locks), leitura de cabeçalho `Retry-After` ou fallback específico. Também não há semáforos ou limites configuráveis de concorrência, contrariando o item (2).【343fc8†L438-L497】
- A rotina não implementa truncagem adaptativa baseada no tamanho do HTML; apenas lê valores fixos de ambiente (`STORYBRAND_MAX_CHAR_BUFFER`) antes de chamar o LangExtract, sem ajuste dinâmico proporcional ao payload recebido, descumprindo o item (3).【343fc8†L457-L493】
- Não foi criado cache local opcional: não há `app/utils/cache.py` ou qualquer decorator/cache ligado às respostas do Vertex, portanto o item (4) também não foi cumprido.【12346a†L1-L2】

## 2. Falha de permissão no bucket GCS (erro 403 storage.buckets.get)
**Resultado da revisão:** não implementado conforme especificação.

- `CloudTraceLoggingSpanExporter.store_in_gcs` segue chamando `bucket.exists()` e `blob.upload_from_string` diretamente, sem capturar exceções `Forbidden`/`NotFound`, sem marcar estado degradado ou consultar a flag `TRACING_DISABLE_GCS`, violando o item (2) da correção proposta.【991c25†L100-L151】【866347†L1-L1】
- O repositório não contém atualizações de documentação orientando o ajuste de IAM (`roles/storage.objectCreator` e `roles/storage.legacyBucketReader`); os únicos registros dessas roles permanecem no plano original, indicando que o item (1) não foi formalizado em README/terraformas.【b23d4f†L1-L6】【3c6741†L305-L319】
- Não há qualquer configuração ou flag que permita desabilitar o uso do bucket em ambientes locais, contrariando a orientação de tratamento resiliente (item 2) e documentação (item 3).【866347†L1-L1】【991c25†L100-L119】

## 3. Melhor resposta ao frontend durante falhas Vertex
**Resultado da revisão:** não implementado conforme especificação.

- O backend não propaga estado de falha: não há ocorrências de `final_delivery_status` ou lógica que registre falhas do Vertex em `state['storybrand_gate_metrics']` além da decisão padrão do gate, descumprindo o item (1).【9df995†L1-L1】【663985†L38-L95】
- O endpoint `/delivery/final/meta` continua retornando apenas `404` quando o artefato não existe, sem diferenciar falhas conhecidas com resposta `503`, logo o item (2) não foi implementado.【93e5ce†L97-L111】
- O frontend apenas considera respostas `ok` e ignora estados de erro; a tipagem `DeliveryMeta` não prevê status `failed` e `checkDeliveryMeta` descarta quaisquer respostas sem `ok`, impedindo a exibição de mensagens orientativas, em desacordo com o item (3).【e742f6†L42-L46】【be552d†L206-L222】

## 4. Observabilidade e alertas
**Resultado da revisão:** não implementado conforme especificação.

- O projeto não possui `app/utils/metrics.py` nem contadores nomeados `storybrand.vertex429.count` ou `storybrand.fallback.triggered`; as únicas referências a esses nomes estão no plano de correções, evidenciando que os itens (1) e (2) não foram materializados.【12346a†L1-L2】【689b00†L1-L4】
