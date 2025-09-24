# Plano de Correção do Preview de Imagens (Inline-only + Validação Rígida)

## 1) Objetivo
Garantir que o preview do frontend receba SEMPRE o JSON final com URLs de imagens via backend (mesma origem), eliminando CORS e impedindo a entrega de JSON incompleto. JSON sem URLs de imagem é tratado como erro e exige reprocessamento.

## 2) Resumo Executivo
- Backend `/delivery/final/download?inline=1` deve responder sempre com o JSON final inline (`application/json`).
- Se o download inline do GCS falhar, usar fallback local (arquivo persistido) — ainda inline.
- Para `inline=1`, nunca retornar envelope `{ signed_url }`.
- Validar o JSON antes de responder: 3 variações e, em cada uma, `visual.image_estado_atual_url`, `visual.image_estado_intermediario_url` e `visual.image_estado_aspiracional_url` não vazios.
- Se faltar qualquer URL: responder 424 (Failed Dependency) com motivo; não entregar JSON parcial.
- Frontend consome apenas `/api` e não segue `signed_url` (sem CORS). Exibe erro e opção de reprocessar quando 424/409.

## 3) Contrato de Entrega (Preview)
- Resposta esperada (200): lista com 3 objetos `AdVariation`.
- Campos mínimos por variação:
  - `landing_page_url`, `formato`, `copy{headline,corpo,cta_texto}`,
  - `visual{descricao_imagem,prompt_estado_atual,prompt_estado_intermediario,prompt_estado_aspiracional,aspect_ratio}`
  - `visual.image_estado_atual_url`, `visual.image_estado_intermediario_url`, `visual.image_estado_aspiracional_url` (todas não vazias)
  - `cta_instagram`, `fluxo`, `referencia_padroes`, `contexto_landing`.
- Em caso de falha: 424/409 com JSON de erro estruturado (sem HTML).

## 4) Alterações no Backend
Arquivo: `app/routers/delivery.py` — endpoint `GET /delivery/final/download`

- Comportamento para `inline=True`:
  1. Se `meta.final_delivery_gcs_uri` existir, tentar `blob.download_as_bytes()` e retornar `Response(content=payload, media_type="application/json")`.
  2. Em caso de exceção, ler `meta.final_delivery_local_path` e retornar o conteúdo inline.
  3. Em ambos os cenários, ANTES de responder: parse e validação rígida (se falhar → 424).
  4. Nunca retornar `{ signed_url }` quando `inline=True`.
- Comportamento para `inline=False` (inalterado): pode retornar Signed URL (útil para download manual ou integração externa).

Pseudocódigo da seção crítica:
```python
if gcs_uri.startswith("gs://") and inline:
    try:
        payload = blob.download_as_bytes()
        data = json.loads(payload)
    except Exception:
        local_path = meta.get("final_delivery_local_path")
        if not (local_path and Path(local_path).exists()):
            raise HTTPException(status_code=404, detail="No artifact available for download")
        payload = Path(local_path).read_bytes()
        data = json.loads(payload)

    # validação rígida
    if not _has_all_image_urls(data):
        raise HTTPException(status_code=424, detail={
            "message": "Image assets incompletos. Reprocessar sessão.",
            "missing": _report_missing(data)
        })

    return Response(content=json.dumps(data).encode("utf-8"), media_type="application/json")

# inline=False: manter lógica atual (Signed URL ou FileResponse)
```

Funções auxiliares a adicionar em `delivery.py`:
```python
def _has_all_image_urls(data: Any) -> bool:
    if not isinstance(data, list) or len(data) != 3:
        return False
    required = [
        "image_estado_atual_url",
        "image_estado_intermediario_url",
        "image_estado_aspiracional_url",
    ]
    for item in data:
        visual = (item or {}).get("visual", {})
        if not all(visual.get(k) for k in required):
            return False
    return True

def _report_missing(data: Any) -> list[dict[str, Any]]:
    out = []
    if not isinstance(data, list):
        return [{"error": "payload_not_list"}]
    for idx, item in enumerate(data):
        visual = (item or {}).get("visual", {})
        missing = [k for k in [
            "image_estado_atual_url",
            "image_estado_intermediario_url",
            "image_estado_aspiracional_url",
        ] if not visual.get(k)]
        if missing:
            out.append({"variation": idx, "missing": missing})
    return out
```

## 5) Regras de Validação (Rígidas)
- Exigir 3 variações exatamente.
- Exigir as 3 URLs de imagem por variação.
- Em caso de falha: 424 (ou 409) com motivo e lista de campos faltantes; nunca retornar JSON incompleto.

## 6) Ajustes no Pipeline (Opcional, mais rigor)
- Adicionar flag `REQUIRE_IMAGE_ASSETS=true` (env) usada pelo `image_assets_agent` para:
  - Se qualquer variação falhar a geração de imagens, marcar falha da sessão (não persistir o JSON final até ter imagens nas 3 variações) e reportar no `FeatureOrchestrator`.

## 7) Alterações no Frontend
- Consumir apenas `/api/delivery/final/download?inline=1`.
- Se 200: processar normalmente.
- Se 424/409: exibir estado “em processamento/falha de assets” com botão de reprocessar.
- Não seguir `signed_url`; não buscar JSON direto do GCS (evita CORS).
- Mapping permanece: `visual.images[]` (se existir) ou `image_estado_*_url` (estado atual, intermediário, aspiracional).

## 8) Observabilidade
- `delivery.py`: log estruturado ao servir inline (origem: gcs/local; validação: ok/fail; session_id, user_id, filename).
- `image_assets_agent`: manter resumo `state["image_assets"]` com status por variação e salvar em meta para diagnóstico.

## 9) Rollout
1. Implementar validação e fallback inline.
2. Testar local com sessão recente (ver abaixo) e com sessão com imagens faltando (esperar 424).
3. Staging: validar permissão da service account para `download_as_bytes` e Signed URL.
4. Produção: liberar; monitorar 4xx no endpoint e tempo de resposta.

## 10) Testes
- Linha de comando (dev):
```
# 1) meta
curl -s "http://localhost:8000/delivery/final/meta?user_id=<uid>&session_id=<sid>" | jq .

# 2) inline
curl -s "http://localhost:8000/delivery/final/download?user_id=<uid>&session_id=<sid>&inline=1" | jq . > /tmp/inline.json

# 3) checar urls
jq '.[].visual | {a:.image_estado_atual_url, i:.image_estado_intermediario_url, s:.image_estado_aspiracional_url}' /tmp/inline.json
jq 'map(select(.visual.image_estado_atual_url=="" or .visual.image_estado_intermediario_url=="" or .visual.image_estado_aspiracional_url==""))|length' /tmp/inline.json

# 4) comparar com arquivo local
jq -S . /tmp/inline.json > /tmp/a.json
jq -S . artifacts/ads_final/<arquivo_da_meta>.json > /tmp/b.json
diff -u /tmp/a.json /tmp/b.json
```
- Unit tests: funções `_has_all_image_urls`, `_report_missing` e rota quando inline=True (mock GCS/local).
- Integração: sessão com 2/3 variações bem-sucedidas deve retornar 424.
- E2E: abrir preview e verificar imagens nas 3 etapas por variação.

## 11) Riscos & Mitigações
- Permissões GCS (ADC/SA): configurar `Storage Object Admin` + `Service Account Token Creator`.
- Artefato local faltando: rota retorna 404 (corrigível reprocessando). Processo de persistência já grava local + meta.
- TTL de Signed URLs das imagens: controlado por `IMAGE_SIGNED_URL_TTL` (no upload). O JSON inline sempre será servido pelo backend; `<img src>` consumirá as URLs assinadas sem CORS.

## 12) Checklist
- [ ] Implementar fallback inline e validação rígida em `delivery.py`.
- [ ] Adicionar helpers `_has_all_image_urls` e `_report_missing`.
- [ ] (Opcional) `REQUIRE_IMAGE_ASSETS=true` no `image_assets_agent` para falhar sessão sem 3 imagens por variação.
- [ ] Atualizar documentação de API (`README.md`) sobre 424/409.
- [ ] Testes unitários/integrados e validação manual via `curl`.

---

Decisão: JSON sem URLs de imagem é inválido para preview e deve resultar em 424/409 solicitando reprocessamento. O preview nunca deve renderizar conteúdo com imagens ausentes.
