# Changelog – Referências Visuais

## 2025-10-12

### ✅ Persistência de Seções StoryBrand no Fallback

**Feature**: Sistema agora persiste as 16 seções completas da narrativa StoryBrand antes da consolidação quando fallback é ativado 【F:app/agents/storybrand_fallback.py†L69-L161】

**Artefatos gerados**:
- `artifacts/storybrand/<session_id>.json` - JSON com 16 seções + audit + enriched_inputs
- Upload GCS condicional para `deliveries/{user_id}/{session_id}/storybrand_sections.json`

**Campos adicionados ao meta.json** 【F:app/callbacks/persist_outputs.py†L299-L307】:
- `storybrand_sections_saved_path` (string|null) - Caminho local do artefato
- `storybrand_sections_gcs_uri` (string|null) - URI do GCS se upload bem-sucedido
- `storybrand_sections_present` (boolean) - Indica presença das seções

**Flag de controle**:
- `PERSIST_STORYBRAND_SECTIONS` (padrão: `false`) - Habilita persistência das seções

**Quando é gerado**:
- `PERSIST_STORYBRAND_SECTIONS=true` **E** `ENABLE_STORYBRAND_FALLBACK=true` **E** fallback ativado

**Casos de uso**:
- Auditoria de narrativa completa por seção
- Reconstrução de contexto sem reprocessar análise
- Análise detalhada de qualidade do fallback

> **Ação para consumidores da API**: Consultar `meta.json` obtido via `GET /final/meta` para verificar se sessão tem seções StoryBrand persistidas (`storybrand_sections_present=true`). Usar `storybrand_sections_saved_path` ou `storybrand_sections_gcs_uri` para recuperar artefato completo.

**Cobertura de testes**: 10/10 testes passando, 87% linhas / 82% branches 【F:tests/unit/agents/test_storybrand_fallback.py†L95-L233】【F:tests/unit/callbacks/test_persist_final_delivery.py†L115-L243】

## 2025-10-07
- ✅ **Endpoint `/upload/reference-image`**: valida formatos (`PNG`, `JPEG/JPG`, `WebP`), limite de 5 MB e integra análise do Vertex AI Vision antes de cachear metadados aprovados. 【F:app/server.py†L41-L272】【F:app/utils/gcs.py†L55-L155】
- ✅ **Preflight enriquecido**: `/run_preflight` resolve metadados via cache, popula `initial_state.reference_images` e expõe resumos (`reference_image_*`) consumidos pelos agentes. 【F:app/server.py†L333-L659】
- ✅ **Schema final atualizado**: `ImageAssetsAgent` injeta `visual.reference_assets` e persiste `reference_images` sanitizados no `meta.json`, garantindo rastreabilidade no JSON final. 【F:app/agent.py†L428-L910】【F:app/callbacks/persist_outputs.py†L101-L215】
- ✅ **Flags & TTL**: `ENABLE_REFERENCE_IMAGES` permanece `false` por padrão; TTLs configuráveis para cache (`reference_cache_ttl_seconds`) e URLs assinadas (`image_signed_url_ttl`) documentados para rollout gradual. 【F:app/config.py†L82-L207】【F:app/utils/reference_cache.py†L18-L123】
- ✅ **Auditoria centralizada**: eventos `reference_image_upload_*`, `preflight_reference_images_*` e `image_assets_generation_*` permitem rastrear aprovações/rejeições e o uso obrigatório das referências. 【F:app/server.py†L181-L659】【F:app/agent.py†L582-L910】

> **Ação para consumidores da API**: atualizar clientes que dependem do JSON final para ler `visual.reference_assets` e preparar limpeza periódica dos uploads expirados.
