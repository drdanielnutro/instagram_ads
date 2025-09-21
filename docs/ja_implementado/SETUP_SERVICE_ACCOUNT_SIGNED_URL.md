# Configurar Service Account para Vertex + Signed URLs (Dev Local)

## Objetivo
Usar a service account `instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com` (chave `sa-key.json`) tanto para invocar Gemini via Vertex quanto para gerar Signed URLs dos artefatos.

## Passos a Executar (uma única vez)

### 1. Conceder permissões necessárias à service account
```bash
gcloud projects add-iam-policy-binding instagram-ads-472021 \
  --member="serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding instagram-ads-472021 \
  --member="serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"

gcloud projects add-iam-policy-binding instagram-ads-472021 \
  --member="serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

> Observação: se quiser restringir `storage.objectAdmin`, aplique diretamente aos buckets com `gsutil iam ch`.

### 2. Garantir que o backend use a chave
- No arquivo `app/.env`, manter: `GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json`
- Reiniciar o backend (`make dev`) após adicionar/remover a chave para garantir que seja recarregada.

### 3. (Opcional) Ativar a SA no gcloud CLI
```bash
gcloud auth activate-service-account instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com \
  --key-file=sa-key.json
gcloud auth application-default set-quota-project instagram-ads-472021
```

### 4. Testar
- Executar `make dev`.
- Gerar um anúncio completo.
- Verificar se o botão "Baixar JSON" retorna uma URL assinada (sem cair no fallback local).

## Observações
- **Segurança**: nunca versionar `sa-key.json`. Armazenar com segurança e rotacionar quando necessário.
- **Produção**: usar uma SA similar (ou a mesma) no Cloud Run, com as mesmas permissões.
- **Fallback**: se a assinatura falhar, o backend agora faz stream local, mas o ideal é habilitar a SA para testar o fluxo idêntico ao de produção.

