# Plano Estendido — Referências Visuais de Personagem e Produto/Serviço

## 0. Visão Geral & Metas
- **Objetivo**: habilitar uploads opcionais de imagens de personagem e produto/serviço, reaproveitando os metadados (SafeSearch + labels) em todo o pipeline de geração de anúncios (copy + visual + imagens finais).
- **Abordagem**: introduzir novos schemas e cache compartilhado, estender endpoints/backend e atualizar agentes e prompts, mantendo compatibilidade quando nenhuma referência for enviada.
- **Princípios chave**: distinguir entregas novas vs. código existente, garantir sanitização de dados sensíveis e cobrir o fluxo completo com testes automatizados.

---
## Fase 1 – Schemas e Cache de Referências

### Entregáveis
- Criar `app/schemas/reference_assets.py` com:
  - `ReferenceImageMetadata` (campos: `id`, `type`, `gcs_uri`, `signed_url`, `labels`, `safe_search_flags`, `user_description | None`, `uploaded_at`).
  - Métodos `model_dump(mode="json")` e `to_state_dict()` para garantir serialização.
- Criar `app/utils/reference_cache.py` com funções:
  - `cache_reference_metadata(metadata: ReferenceImageMetadata) -> None`.
  - `resolve_reference_metadata(reference_id: str | None) -> ReferenceImageMetadata | None`.
  - `merge_user_description(metadata: ReferenceImageMetadata | None, description: str | None) -> dict | None`.
  - `build_reference_summary(reference_images: dict[str, dict | None], payload: dict) -> dict[str, str | None]`.
  - Implementar cache em memória com TTL configurável (`config.reference_cache_ttl_seconds`) e ganchos para futura troca por Redis/Datastore.
- Criar módulo `app/utils/vision.py` com helper assíncrono `analyze_reference_image(..., type: Literal["character", "product"]) -> ReferenceImageMetadata` encapsulando chamadas ao Vertex AI Vision (SafeSearch + labels).
- Criar helper `upload_reference_image` em `app/utils/gcs.py` (novo) que utilizará `analyze_reference_image` (criado nesta fase) antes de devolver o ID ao cliente.

### Dependências existentes
- `BaseModel` (Pydantic) disponível em `app/agent.py:63`.
- Utilitário `resolve_state` em `app/utils/session_state.py:13-78` (já utilizado por callbacks).
- Configurações genéricas em `app/config.py` (feature flags e tempo de TTL).

### Integrações planejadas
1. `/run_preflight` (Fase 2) consumirá `resolve_reference_metadata` e `build_reference_summary` (criados nesta fase).
2. Endpoint `/upload/reference-image` (Fase 2) chamará `upload_reference_image` e `analyze_reference_image` (ambos criados nesta fase).
3. `ImageAssetsAgent` (Fase 4) reidratará `ReferenceImageMetadata` a partir dos dicionários retornados pelas funções desta fase.

### Critérios de aceitação
- [ ] Arquivo `app/schemas/reference_assets.py` criado com classes tipadas e métodos helper.
- [ ] Cache em `app/utils/reference_cache.py` suporta `cache`, `resolve`, `merge` e `build_summary` com TTL configurável.
- [ ] Módulo `app/utils/vision.py` exporta `analyze_reference_image` e trata respostas/erros do Vertex AI Vision.
- [ ] Helper `upload_reference_image` em `app/utils/gcs.py` integra-se ao módulo de visão sem expor dados sensíveis.
- [ ] Testes unitários cobrindo cache e visão (Fase 6) executados com sucesso.

---
## Fase 2 – Backend: Upload & Preflight

### Entregáveis
- Implementar endpoint `POST /upload/reference-image` em `app/server.py`:
  - Assinatura com `UploadFile`, `type: Literal["character", "product"]`, `user_id | None`, `session_id | None`.
  - Passos: validar content-type/tamanho, enviar ao GCS (`upload_reference_image`), analisar via Vision (`analyze_reference_image`), aplicar SafeSearch e `cache_reference_metadata` (Fase 1), devolver `{ "id", "signed_url", "labels" }`.
- Criar schema `RunPreflightRequest` (novo módulo `app/schemas/run_preflight.py`) substituindo parse manual atual.
- Modificar `run_preflight` em `app/server.py:163-395`:
  - Reutilizar `RunPreflightRequest`.
  - Resolver metadados via `resolve_reference_metadata` (criada na Fase 1).
  - Construir `initial_state["reference_images"]`, `reference_image_summary`, `reference_image_character_summary`, `reference_image_product_summary`.
  - Devolver `initial_state` enriquecido sem manipulações externas.
- Registrar logs estruturados (`logger.log_struct`) para uploads e preflight.

### Dependências existentes
- Função `run_preflight` atual em `app/server.py:163-395` (retorna `initial_state`).
- Logging estruturado (`logger.log_struct`) já usado em preflight (`app/server.py:299-320`).
- Configs `ENABLE_NEW_INPUT_FIELDS` e `ENABLE_STORYBRAND_FALLBACK` (`app/config.py:120-170`).

### Modificações planejadas (resumo/diff)
```diff
# app/server.py
+@app.post("/upload/reference-image")
+async def upload_reference_image(...):
+    metadata = analyze_reference_image(...)
+    cache_reference_metadata(metadata)
+    return {"id": metadata.id, ...}
 
-async def run_preflight(payload: dict = Body(...)) -> dict:
+@app.post("/run_preflight")
+async def run_preflight(request: RunPreflightRequest) -> dict:
     ...
-    initial_state = {...}
+    reference_images = request.reference_images or {}
+    initial_state["reference_images"] = {
+        "character": merge_user_description(
+            resolve_reference_metadata(reference_images.get("character", {}).get("id")),
+            reference_images.get("character", {}).get("user_description"),
+        ),
+        ...
+    }
```

### Critérios de aceitação
- [ ] `/upload/reference-image` retorna 200 com ID válido e bloqueia imagens `LIKELY` em SafeSearch.
- [ ] `/run_preflight` enriquece `initial_state` quando IDs válidos são enviados; mantém comportamento atual quando não há referências.
- [ ] Logs estruturados registram uploads e uso de cache.
- [ ] Teste de integração (Fase 6) cobre upload → cache → preflight.

---
## Fase 3 – Frontend (React + Vite)

### Entregáveis
- Criar componente `frontend/src/components/ReferenceUpload.tsx` com props `type="character" | "product"`, validações de extensão e tamanho (máx. 5 MB).
- Criar hook/store `useReferenceImages` em `frontend/src/state/referenceImages.ts` para gerenciar IDs e descrições.
- Atualizar `frontend/src/App.tsx` (linhas ~420-520):
  - Submeter uploads imediatamente para `/upload/reference-image` (Fase 2) via `FormData`.
  - No `handleSubmit`, incluir `reference_images` no payload com `{ id, user_description }` apenas quando houver upload.
- Atualizar `frontend/src/components/InputForm.tsx` para usar o novo componente e capturar descrições.
- Adicionar mensagens de feedback (sucesso/erro) relacionadas ao upload de referências.

### Dependências existentes
- Função `handleSubmit` em `frontend/src/App.tsx:423-498`.
- Campo `foco` já presente em `frontend/src/components/InputForm.tsx:250-270`.

### Integrações planejadas
- Payload submetido continuará compatível com `/run` atual, apenas adicionando `reference_images` (consumido na Fase 2).
- Hooks serão usados na Fase 6 (testes de frontend).

### Critérios de aceitação
- [ ] Uploads exibem progresso, validam extensões e retornos do backend.
- [ ] `handleSubmit` envia `reference_images` somente quando disponíveis.
- [ ] Plano de testes de frontend (RTL/Cypress) cobre cenários com e sem uploads.
- [ ] UX mantém comportamento original quando recursos não são usados.

---
## Fase 4 – Integração no Pipeline de Agents & Prompts

### Entregáveis
- Atualizar prompts em `app/agent.py`:
  - **VISUAL_DRAFT** (linhas ~880-930): adicionar placeholders `{reference_image_character_summary}` e `{reference_image_product_summary}` (criados na Fase 2) com instruções condicionais.
  - **COPY_DRAFT** (linhas ~830-880): permitir menção ao produto real utilizando labels do cache.
  - **final_assembler** (`app/agent.py:1030-1075`):
    - Injetar `reference_images.character.gcs_uri`, `reference_images.character.labels`, `reference_images.product.gcs_uri`, `reference_images.product.labels`.
    - Pós-processar saída para preencher `visual.reference_assets` com valores factuais quando presentes.
- Atualizar `ImageAssetsAgent` (`app/agent.py:300-577`):
  - Carregar `state["reference_images"]` (dicionários), reidratar com `ReferenceImageMetadata.model_validate` (criado na Fase 1).
  - Registrar no summary flags `character_reference_used`, `product_reference_used`.
- Estender `generate_transformation_images` (`app/tools/generate_transformation_images.py:180-330`):
  - Novos parâmetros `reference_character: ReferenceImageMetadata | None` e `reference_product: ReferenceImageMetadata | None`.
  - Helper `_load_reference_image(metadata: ReferenceImageMetadata) -> Image.Image`.
  - Ajustar prompts de estágio atual/aspiracional quando referências estiverem presentes.
- Atualizar templates em `app/config.py`:
  - `image_current_prompt_template` e `image_aspirational_prompt_template_with_product` conforme plano original (usados quando houver referências).

### Dependências existentes
- `ImageAssetsAgent` atual (`app/agent.py:300-577`).
- Função `generate_transformation_images` (`app/tools/generate_transformation_images.py:180-330`).
- Config `image_signed_url_ttl` (`app/config.py:240`).

### Modificações planejadas (resumo)
```diff
# app/agent.py (final_assembler)
-    "visual": {..., "referencia_padroes": "..."}
+    "visual": {...,
+        "referencia_padroes": "...",
+        "reference_assets": {
+            "character": <valores do state>,
+            "product": <valores do state>
+        }
+    }
```

### Critérios de aceitação
- [ ] Prompts utilizam placeholders condicionais; plano feliz sem referências permanece intacto.
- [ ] `ImageAssetsAgent` gera flags de uso de referência e mantém fallback quando dados ausentes.
- [ ] `generate_transformation_images` aceita novos parâmetros sem quebrar assinaturas existentes (ver testes Fase 6).
- [ ] JSON final inclui `visual.reference_assets` apenas quando metadados existem.

---
## Fase 5 – Observabilidade, Persistência e Sanitização

### Entregáveis
- Refatorar `persist_final_delivery(callback_context)` (`app/callbacks/persist_outputs.py:35-141`):
  - Criar helper `sanitize_reference_images(state: dict[str, Any]) -> dict[str, Any]` removendo `signed_url`, tokens e payloads crus da Vision.
  - Persistir metadados sanitizados em `meta["reference_images"]` e nos logs.
  - Manter assinatura atual (usa `resolve_state(callback_context)`).
- Adicionar logs estruturados (`logger.log_struct`) nos pontos-chave:
  - Upload (Fase 2), preflight (Fase 2), pipeline de agentes (Fase 4) e persistência (esta fase).
- Avaliar TTL curto para `signed_url` via `config.image_signed_url_ttl` e documentar política.

### Dependências existentes
- `resolve_state` (`app/utils/session_state.py:13-78`).
- `clear_failure_meta` (`app/utils/delivery_status.py:12-40`).
- Logging com `logger.log_struct` já usado nos endpoints principais.

### Critérios de aceitação
- [ ] `persist_final_delivery` salva metadados sem campos sensíveis e mantém compatibilidade com callbacks existentes (`ImageAssetsAgent` e `final_assembler`).
- [ ] Logs estruturados exibem referências usadas e decisões do SafeSearch.
- [ ] Documentação de TTL e limpeza de signed URLs atualizada (Fase 7).

---
## Fase 6 – Testes Automatizados & QA

### Entregáveis
- **Unit Tests**:
  - `tests/unit/utils/test_reference_cache.py` (cache, TTL, merge com descrições).
  - `tests/unit/utils/test_vision.py` (mocks do SafeSearch e labels).
  - `tests/unit/tools/test_generate_transformation_images.py` (parâmetros com referências vs. fallback).
  - `tests/unit/agents/test_image_assets_agent.py` (reidratação de metadados e flags de summary).
  - `tests/unit/callbacks/test_persist_outputs.py` (sanitização de `reference_images`).
- **Integração**:
  - `tests/integration/api/test_reference_upload.py`: upload → análise → cache → `/run_preflight` recuperando metadados no `initial_state`.
  - `tests/integration/agents/test_reference_pipeline.py`: pipeline parcial com referências, verificando JSON final e `reference_assets`.
- **Frontend**:
  - RTL tests para `ReferenceUpload` e `handleSubmit` com/sem uploads.
  - Cenários Cypress (se suite existir) para formulário completo.
- **QA manual**: roteiro com quatro cenários (nenhuma referência, apenas personagem, apenas produto, ambos) para validar UX e resultados.

### Critérios de aceitação
- [ ] `make test` cobre novas suites sem regressões.
- [ ] Testes de integração validam ciclo completo (incluindo sanitização).
- [ ] Roteiro manual documenta prints/logs de cada cenário.

---
## Fase 7 – Documentação & Rollout

### Entregáveis
- Atualizar `README.md` (seção de geração de imagens) com fluxo de uploads, limitações (5 MB, formatos) e política de TTL.
- Criar/atualizar playbooks internos (`docs/`) descrevendo auditoria (`state['image_generation_audit']`) e monitoramento.
- Adicionar notas de migração (changelog) destacando schema `reference_images` no JSON final e novos endpoints.
- Planejar estratégia de rollout (flag `ENABLE_REFERENCE_IMAGES` opcional em `app/config.py`) para ativar gradualmente.

### Critérios de aceitação
- [ ] Documentação revisada pelo time.
- [ ] Plano de rollback inclui desativar flag e limpar cache/GCS de uploads não usados.

---
## Dependências Externas e Configuração
- `google-cloud-vision>=3.4.0` — adicionar a `requirements.txt` (linha nova) e `uv.lock`.
- `google-cloud-storage` já presente (`requirements.txt:15`) – reutilizado.
- Configurações novas em `app/config.py`:
  - `reference_cache_ttl_seconds` (int, default 3600).
  - `enable_reference_images` (bool, default `False` para rollout).

## Riscos & Mitigações
| Risco | Mitigação |
|-------|-----------|
| Indisponibilidade do Vision AI | Capturar exceções em `analyze_reference_image`, retornar erro amigável ao usuário e registrar log estruturado; fallback permite continuar sem referências. |
| Latência adicional de upload/análise | Medir tempos (logs de duração), ajustar `config.image_generation_timeout` e permitir operação sem referências. |
| Inconsistência narrativa entre copy/visual | Prompts (Fase 4) reforçam uso das labels; QA manual cobre cenários com e sem referências. |
| Crescimento de arquivos no GCS | Incluir job de limpeza (planejado em docs de rollout) para remover uploads não utilizados após TTL; documentação explicita política. |
| Cache em memória entre múltiplos workers | Abstrair utilitário permitindo futura troca por Redis/Datastore; documentar limitação e recomendar afinidade de sessão até adoção do backend compartilhado. |

---
## Checklist Final do Plano
- [ ] Entregáveis usam verbos declarativos (Criar/Implementar/Modificar/Estender).
- [ ] Dependências existentes possuem caminho e, quando relevante, intervalo de linhas.
- [ ] Itens referenciados em fases posteriores indicam “(criado na Fase X)”.
- [ ] Diffs ou resumos de modificações em arquivos existentes estão presentes.
- [ ] Critérios de aceitação definidos para cada fase.
- [ ] Dependências externas e flags documentadas.
- [ ] Fluxo de testes cobre unitário, integração, frontend e QA manual.
- [ ] Plano pode ser validado pelo `plan-code-validator` sem falsos P0.

---
## Resumo Executivo da Implementação
1. **Fase 1 (Fundação)**: schemas e cache para metadados de referência.
2. **Fase 2 (Backend)**: endpoint de upload + `/run_preflight` enriquecido.
3. **Fase 3 (Frontend)**: componentes de upload e payload estendido.
4. **Fase 4 (Pipeline)**: prompts, agentes e ferramenta de imagens incorporando referências.
5. **Fase 5 (Observabilidade)**: sanitização de persistência e logs.
6. **Fase 6 (Qualidade)**: testes automatizados e QA manual asseguram fluxo ponta a ponta.
7. **Fase 7 (Docs/Rollout)**: documentação e estratégia de ativação gradual.

Sequenciar dessa forma evita dependências circulares (schemas e cache devem existir antes de endpoints, que precisam estar prontos antes dos agentes, etc.) e garante rastreabilidade completa para validação automática e implementação por múltiplos times ou agentes.
