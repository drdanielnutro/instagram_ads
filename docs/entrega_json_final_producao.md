# Entrega do JSON Final em Produção (DELIVERIES_BUCKET + Signed URL)

## Objetivo
Garantir download seguro e simples do JSON final em produção:
- Dev: salvar sempre em `artifacts/ads_final/` e permitir stream local.
- Prod: enviar ao GCS em um bucket dedicado de entregas (`DELIVERIES_BUCKET`) e servir via Signed URL (v4, GET, expiração curta).

## Decisões de Arquitetura
- Separação de buckets:
  - `ARTIFACTS_BUCKET`: uso interno do ADK (agentes/ferramentas). Não é exposto ao frontend.
  - `DELIVERIES_BUCKET`: entregas finais (JSON). Consumido pelo frontend via Signed URL.
- Convenção de paths no GCS:
  - `deliveries/{user_id}/{session_id}/{timestamp}_{session_id}_{formato}.json`
  - Sidecar: `deliveries/{user_id}/{session_id}/meta.json`

## Backend
- Callback `persist_final_delivery`:
  - Salva localmente em `artifacts/ads_final/`.
  - Se `DELIVERIES_BUCKET` estiver definido: upload para `deliveries/{user_id}/{session_id}/...`.
  - Salva sidecar `meta.json` (local e no GCS) com: `filename`, `formato`, `timestamp`, `size_bytes`, `final_delivery_local_path`, `final_delivery_gcs_uri`, `user_id`, `session_id`.
- Endpoints (router `/delivery`):
  - `GET /delivery/final/meta?user_id=...&session_id=...` → retorna metadados do sidecar.
  - `GET /delivery/final/download?user_id=...&session_id=...` →
    - Prod: `{ signed_url, expires_in }` (v4, GET, 10 min, com `Content-Disposition` e `Content-Type`).
    - Dev: stream do arquivo local (`application/json`).

## Segurança e IAM
- Não tornar o bucket público.
- IAM na Service Account (Cloud Run):
  - `roles/storage.objectAdmin` (ou `objectCreator` + `objectViewer`) no bucket de entregas.
  - `roles/iam.serviceAccountTokenCreator` para gerar Signed URL (ADC, v4).
- APIs: `storage.googleapis.com`, `iamcredentials.googleapis.com`.
- CORS (frontend web): permitir `GET` e expor `Content-Type, Content-Disposition` no bucket de entregas.

## Variáveis de Ambiente
```bash
DELIVERIES_BUCKET=gs://<project>-deliveries
ARTIFACTS_BUCKET=gs://<project>-facilitador-logs-data    # interno ADK
GOOGLE_CLOUD_PROJECT=instagram-ads-472021
GOOGLE_CLOUD_LOCATION=us-central1

# CORS - múltiplas origens separadas por vírgula
ALLOW_ORIGINS=https://<project>-frontend.storage.googleapis.com,https://seudominio.com.br

# Controles de comportamento
ENABLE_AUTO_BUCKET_CREATE=false    # Em produção, sempre false
SIGNED_URL_EXPIRATION_SECONDS=600  # 10 minutos (padrão)
```

## Observações de Produção
- Não criar buckets no startup. Provisione via IaC/CLI.
- `artifact_service_uri` é configurado pelo parâmetro do `get_fast_api_app`; o uso de env var é convenção da aplicação.
- Autenticação/autorização dos endpoints `/delivery/*` será feita em fase posterior; por ora, o desenho já separa dados e viabiliza Signed URLs.

## CORS e Origens (Frontend × Backend × GCS)

### Por que é necessário:
- Navegador aplica Same‑Origin Policy. Seu frontend (ex.: `https://seudominio.com.br`) conversa com:
  - Backend (Cloud Run): `https://instagram-ads-generator-XXXXX.run.app`
  - GCS (Signed URL): `https://storage.googleapis.com/...`
- São origens diferentes. Sem CORS, o navegador bloqueia requisições cross-origin.

### Quando CORS é necessário:

**CORS no Backend (Cloud Run)**: **SEMPRE NECESSÁRIO**
- Todas as chamadas do frontend para a API do backend precisam de CORS configurado

**CORS no Bucket de Deliveries (GCS)**: **CONDICIONAL**
- ❌ **Não precisa** se usar apenas `window.open(signed_url)` para download direto
- ✅ **Precisa** se usar `fetch()` para baixar o JSON como Blob
- ✅ **Precisa** se quiser ler cabeçalhos HTTP (ex.: Content-Disposition para filename)

Backend (Cloud Run) – habilitar CORS para o frontend:
```bash
export SERVICE=instagram-ads-generator
export REGION=us-central1
gcloud run services update "$SERVICE" --region "$REGION" \
  --set-env-vars "ALLOW_ORIGINS=https://seudominio.com.br,https://www.seudominio.com.br"
```

Bucket de Deliveries (GCS) – CORS:
1) Edite `docs/cors_deliveries.json` com seus domínios (apenas se usar fetch/Blob).
2) Aplique ao bucket (apenas se necessário):
```bash
gsutil cors set docs/cors_deliveries.json "$DELIVERIES_BUCKET"
gsutil cors get "$DELIVERIES_BUCKET"
```

## Apêndice – Frontend em GCS (Opção B – MVP)

Objetivo: hospedar o build estático (Vite) diretamente no GCS para acelerar o MVP, mantendo o backend no Cloud Run.

Por que funciona bem no MVP:
- Simples e barato; tudo no GCP.
- Sem necessidade de domínio próprio no início.
- Permite CORS bem definido, desde que use a origem correta do bucket.

### Recomendação de URL do Frontend:

**Opção 1 - Subdomínio (RECOMENDADO)**:
- URL: `https://<PROJECT_ID>-frontend.storage.googleapis.com/app/`
- Origem para CORS: `https://<PROJECT_ID>-frontend.storage.googleapis.com`
- Vantagem: Origem mais específica e segura

**Opção 2 - Path**:
- URL: `https://storage.googleapis.com/<PROJECT_ID>-frontend/app/`
- Origem para CORS: `https://storage.googleapis.com`
- Desvantagem: Origem muito ampla (todos os buckets do GCS)

Passo a passo (frontend):
```bash
# 1) Criar bucket de frontend (público) – apenas para arquivos do site
gcloud storage buckets create gs://instagram-ads-472021-frontend \
  --location=us-central1 \
  --uniform-bucket-level-access

# Tornar o bucket público para leitura (apenas este bucket!)
gsutil iam ch allUsers:objectViewer gs://instagram-ads-472021-frontend

# 2) Configurar como Website (SPA)
# SPA tipicamente usa index.html como fallback; defina main e error para index.html
gsutil web set -m index.html -e index.html gs://instagram-ads-472021-frontend

# 3) Publicar o build do Vite
npm run build
# IMPORTANTE: rsync é destrutivo - remove arquivos no destino que não existem na origem
# O frontend tem base: "/app/" no vite.config.ts, então deve ir para /app no bucket
gsutil -m rsync -r dist gs://instagram-ads-472021-frontend/app

# 4) URL do app (MVP)
echo "https://instagram-ads-472021-frontend.storage.googleapis.com/app/index.html"
```

Backend (Cloud Run) – CORS para a origem do frontend no GCS:
```bash
export SERVICE=instagram-ads-generator
export REGION=us-central1
gcloud run services update "$SERVICE" --region "$REGION" \
  --set-env-vars "ALLOW_ORIGINS=https://instagram-ads-472021-frontend.storage.googleapis.com"
```

Deliveries (GCS) – CORS:
- ❌ Se usar apenas `window.open(signed_url)`: CORS no bucket **não é necessário**
- ✅ Se usar `fetch()` para Blob ou ler cabeçalhos: CORS no bucket **é necessário**
- Quando necessário, aplique com a origem do frontend (veja seção "CORS e Origens")

### CLI – Opção B (copy-paste)
```bash
# 0) Projeto
export PROJECT_ID=instagram-ads-472021
gcloud config set project "$PROJECT_ID"

# 1) Frontend (GCS site estático)
export FE_BUCKET=$PROJECT_ID-frontend
gcloud storage buckets create gs://$FE_BUCKET --location=us-central1 --uniform-bucket-level-access
gsutil iam ch allUsers:objectViewer gs://$FE_BUCKET
gsutil web set -m index.html -e index.html gs://$FE_BUCKET

# Build e publicação (rode no diretório do frontend)
npm run build
# NOTA: rsync remove arquivos no destino que não existem na origem
gsutil -m rsync -r dist gs://$FE_BUCKET/app
echo "Frontend URL:" "https://$FE_BUCKET.storage.googleapis.com/app/index.html"

# 2) Backend (Cloud Run) – CORS para a origem do FE
export SERVICE=instagram-ads-generator
export REGION=us-central1
gcloud run services update "$SERVICE" --region "$REGION" \
  --set-env-vars "ALLOW_ORIGINS=https://$FE_BUCKET.storage.googleapis.com"

# 3) CORS no bucket de deliveries (apenas se usar fetch/Blob no frontend)
export DELIVERIES_BUCKET=gs://$PROJECT_ID-deliveries
# Só execute se o frontend precisar fazer fetch() do JSON (não necessário para window.open)
gsutil cors set docs/cors_deliveries.json "$DELIVERIES_BUCKET"
gsutil cors get "$DELIVERIES_BUCKET"
```


## CLI – Passo a Passo (GCP)

1) Selecionar projeto e habilitar APIs
```bash
export PROJECT_ID=instagram-ads-472021
gcloud config set project "$PROJECT_ID"
gcloud services enable storage.googleapis.com iamcredentials.googleapis.com
```

2) Criar bucket de entregas (região us-central1)
```bash
export DELIVERIES_BUCKET="gs://${PROJECT_ID}-deliveries"
gcloud storage buckets create "$DELIVERIES_BUCKET" \
  --location=us-central1 \
  --uniform-bucket-level-access

gcloud storage buckets describe "$DELIVERIES_BUCKET" \
  --format='value(location,iamConfiguration.uniformBucketLevelAccess.enabled)'
```

3) Conceder IAM para a Service Account do serviço (Cloud Run)
```bash
# Descobrir SA do serviço (ajuste o nome do serviço e região)
export SERVICE=instagram-ads-generator
export REGION=us-central1
export SA_EMAIL=$(gcloud run services describe "$SERVICE" --region "$REGION" \
  --format='value(spec.template.spec.serviceAccountName)')

# Storage (objetos)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

# Assinatura (Signed URL v4 com ADC)
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator"
```

4) Configurar CORS no bucket (se frontend em outro domínio)
```bash
# Edite docs/cors_deliveries.json com o(s) domínio(s) do seu frontend
gsutil cors set docs/cors_deliveries.json "$DELIVERIES_BUCKET"
gsutil cors get "$DELIVERIES_BUCKET"
```

5) Definir variáveis de ambiente no serviço (Cloud Run)
```bash
gcloud run services update "$SERVICE" --region "$REGION" \
  --set-env-vars "DELIVERIES_BUCKET=${DELIVERIES_BUCKET},ARTIFACTS_BUCKET=gs://${PROJECT_ID}-facilitador-logs-data,ENABLE_AUTO_BUCKET_CREATE=false"
```

## Validação Rápida

1) Rodar uma geração normal (frontend ou curl) até o final.

2) Checar metadados e download pelos endpoints:
```bash
# Substitua <USER_ID> e <SESSION_ID>
curl -s "http://localhost:8000/delivery/final/meta?user_id=<USER_ID>&session_id=<SESSION_ID>" | jq .
curl -s "http://localhost:8000/delivery/final/download?user_id=<USER_ID>&session_id=<SESSION_ID>" | jq .
```

- Em produção (com DELIVERIES_BUCKET): o download retorna `{ signed_url, expires_in }` (v4, GET, 10 min).
- Em desenvolvimento (sem DELIVERIES_BUCKET): o endpoint faz stream local do arquivo JSON.
