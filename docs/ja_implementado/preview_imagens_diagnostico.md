# Diagnóstico: Imagens não exibidas no Preview (Wizard)

## Sintoma
- Com o preview ativado (Wizard) e variações carregadas, as descrições e prompts aparecem, mas as imagens não.

## Hipóteses consideradas
- A) JSON consumido pelo preview não é a versão final com URLs de imagens (envelope ou versão pré-imagens).
- B) Mapeamento entre nomes de campos do JSON e do componente está incorreto.
- C) JSON e mapeamento corretos, mas falta permissão/CORS para carregar as imagens.

## Diagnóstico
- Hipótese A confirmada: o preview chama `/api/delivery/final/download?inline=1`. Quando o backend não consegue baixar o artefato diretamente do GCS no modo inline, ele retorna um envelope `{ ok, signed_url, expires_in }`. O componente `AdsPreview` não segue esse `signed_url` para buscar o JSON final; tenta normalizar o envelope como se fosse a lista de variações — portanto, não recebe os campos `visual.image_estado_*_url` e não mostra imagens.
- Mapeamento (Hipótese B) está correto: o componente procura `visual.images[]` ou `visual.image_estado_atual_url`, `visual.image_estado_intermediario_url`, `visual.image_estado_aspiracional_url`, que são exatamente os campos preenchidos pelo backend quando a geração de imagens tem sucesso.
- Permissões/CORS (Hipótese C) não são a causa principal aqui. Abrir a URL assinada da imagem no navegador funciona; o problema é o preview não estar de fato consumindo o JSON final com essas URLs quando recebe apenas o envelope.

## Evidências rápidas
- Frontend busca inline e não segue signed_url do envelope:
```
// frontend/src/components/AdsPreview.tsx
const response = await fetch(baseUrl);
const contentType = response.headers.get("content-type") ?? "";
let payload: unknown;
if (contentType.includes("application/json")) {
  payload = await response.json();  // pode ser { ok, signed_url, expires_in }
} else {
  payload = safeJsonParse(await response.text());
}
const parsedVariations = normalizeVariations(payload);
```
- Mapeamento das imagens no componente (correto):
```
// frontend/src/components/AdsPreview.tsx
if (visual.image_estado_atual_url) images.push(visual.image_estado_atual_url);
if (visual.image_estado_intermediario_url) images.push(visual.image_estado_intermediario_url);
if (visual.image_estado_aspiracional_url) images.push(visual.image_estado_aspiracional_url);
```
- Backend devolvendo envelope quando inline falha (download do GCS em dev pode falhar com ADC):
```
// app/routers/delivery.py (excerto)
if gcs_uri.startswith("gs://"):
  if inline:
    try:
      payload = blob.download_as_bytes()
      return Response(content=payload, media_type="application/json")
    except Exception:
      pass  # cai para baixo
  url = blob.generate_signed_url(...)
  return {"ok": True, "signed_url": url, "expires_in": 600}
```

## Como resolver (sem CORS, preferível)
Garantir que o frontend receba SEMPRE o JSON final inline pela mesma origem (`/api`).

1) Backend: fallback local quando `inline=True` falhar
- Ajustar `app/routers/delivery.py` para, ao capturar exceção no `download_as_bytes()` com `inline=True`, tentar ler o arquivo local apontado por `meta['final_delivery_local_path']` e retornar inline como `application/json` ANTES de devolver `{ signed_url }`.

Exemplo (pseudocódigo indicando o ponto):
```
if gcs_uri.startswith("gs://"):
  if inline:
    try:
      payload = blob.download_as_bytes()
      return Response(content=payload, media_type="application/json")
    except Exception:
      local_path = meta.get("final_delivery_local_path")
      if local_path and Path(local_path).exists():
        return Response(content=Path(local_path).read_bytes(), media_type="application/json")
  # somente se não houve inline nem local, retornar signed_url
  url = blob.generate_signed_url(...)
  return {"ok": True, "signed_url": url, "expires_in": 600}
```

Efeito: o preview continuará consumindo pelo endpoint `/api` e sempre receberá o JSON final (com `visual.image_estado_*_url`), sem CORS.

2) (Opcional) Frontend: seguir signed_url (se decidir manter envelope)
- Em `AdsPreview.tsx`, se `payload.signed_url` existir, fazer uma segunda requisição para esse URL e usar o conteúdo retornado como `finalPayload` antes de chamar `normalizeVariations(finalPayload)`.
- Atenção: baixar JSON diretamente do GCS via fetch requer CORS configurado no bucket. Para evitar CORS, crie um endpoint proxy no backend que receba o `signed_url`, baixe server-side e retorne inline.

## Validação
- Linha de comando:
```
curl -s "http://localhost:8000/delivery/final/download?user_id=<uid>&session_id=<sid>&inline=1" | jq .
```
- Esperado: uma lista de 3 variações com `visual.image_estado_atual_url`, `image_estado_intermediario_url`, `image_estado_aspiracional_url` preenchidos para as variações que tiveram geração bem-sucedida.
- No preview: variações bem-sucedidas exibem imagens; variações com erro de geração mostram somente descrições/prompts (conforme log).

## Observações sobre CORS
- Exibir imagem com `<img src="<signed_url>" />` não requer CORS.
- Fazer `fetch` de JSON diretamente no bucket GCS requer CORS no bucket — por isso preferimos o fluxo "inline pelo backend".

## Itens relacionados
- Metadado local confirma o arquivo final: `artifacts/ads_final/meta/<session_id>.json` aponta para o JSON completo em `artifacts/ads_final/<timestamp>_<session>_<formato>.json`.
- Exemplo de imagem acessível por URL assinada (funciona no navegador):
  - `https://storage.googleapis.com/.../images/estado_atual_0.png?...`

## Checklist de correção
- [ ] Ajustar fallback inline no backend (download local quando GCS inline falhar).
- [ ] (Se necessário) Implementar proxy no backend para seguir `signed_url` e retornar inline.
- [ ] (Opcional) Frontend: dar suporte a envelope `{ signed_url }` (com proxy) se mantido.
- [ ] Validar com `curl` e no preview (duas variações com imagem, uma sem, conforme log).
