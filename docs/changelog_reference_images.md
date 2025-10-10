# Changelog – Referências Visuais

## 2025-10-07
- ✅ **Endpoint `/upload/reference-image`**: valida formatos (`PNG`, `JPEG/JPG`, `WebP`), limite de 5 MB e integra análise do Vertex AI Vision antes de cachear metadados aprovados. 【F:app/server.py†L41-L272】【F:app/utils/gcs.py†L55-L155】
- ✅ **Preflight enriquecido**: `/run_preflight` resolve metadados via cache, popula `initial_state.reference_images` e expõe resumos (`reference_image_*`) consumidos pelos agentes. 【F:app/server.py†L333-L659】
- ✅ **Schema final atualizado**: `ImageAssetsAgent` injeta `visual.reference_assets` e persiste `reference_images` sanitizados no `meta.json`, garantindo rastreabilidade no JSON final. 【F:app/agent.py†L428-L910】【F:app/callbacks/persist_outputs.py†L101-L215】
- ✅ **Flags & TTL**: `ENABLE_REFERENCE_IMAGES` permanece `false` por padrão; TTLs configuráveis para cache (`reference_cache_ttl_seconds`) e URLs assinadas (`image_signed_url_ttl`) documentados para rollout gradual. 【F:app/config.py†L82-L207】【F:app/utils/reference_cache.py†L18-L123】
- ✅ **Auditoria centralizada**: eventos `reference_image_upload_*`, `preflight_reference_images_*` e `image_assets_generation_*` permitem rastrear aprovações/rejeições e o uso obrigatório das referências. 【F:app/server.py†L181-L659】【F:app/agent.py†L582-L910】

> **Ação para consumidores da API**: atualizar clientes que dependem do JSON final para ler `visual.reference_assets` e preparar limpeza periódica dos uploads expirados.
