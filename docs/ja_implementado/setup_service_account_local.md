# Setup local com service account (`sa-key.json`)

Este guia descreve como configurar o ambiente local para rodar o projeto usando a chave `sa-key.json` da service account `instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com`, garantindo acesso à Vertex AI e aos buckets GCS.

## 0. Pré-requisitos de ferramentas locais
- Sistema com Python 3.10+, Node 18+, `npm`, `uv` e `make`.
- Instalar Google Cloud SDK (necessário para checar/conceder permissões da service account):
  ```bash
  sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates gnupg
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo tee /usr/share/keyrings/cloud.google.gpg >/dev/null
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
  sudo apt-get update && sudo apt-get install -y google-cloud-cli
  ```
- Validar: `gcloud --version`.

## 1. Configurar o gcloud com sua conta
- `gcloud init` (ou `gcloud config set project instagram-ads-472021`).
- `gcloud auth login` para garantir que os comandos CLI executem com sua conta (opcional, mas recomendado).

## 2. Conferir permissões atuais da service account
- Roles no projeto:
  ```bash
  gcloud projects get-iam-policy instagram-ads-472021 \
    --flatten="bindings[].members" \
    --format='table(bindings.role)' \
    --filter="bindings.members:serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com"
  ```
- Roles aplicadas diretamente ao bucket (caso existam):
  ```bash
  gcloud storage buckets get-iam-policy gs://instagram-ads-472021-facilitador-logs-data \
    --project instagram-ads-472021 \
    --flatten="bindings[].members" \
    --format='table(bindings.role)' \
    --filter="bindings.members:serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com"
  ```
  (Repita para o bucket `gs://instagram-ads-472021-deliveries` se necessário.)

## 3. Conceder roles obrigatórias (caso estejam ausentes)
- Vertex AI:
  ```bash
  gcloud projects add-iam-policy-binding instagram-ads-472021 \
    --member="serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
  ```
- Permissões de Storage (escolha escopo de projeto ou bucket):
  - Projeto completo:
    ```bash
    gcloud projects add-iam-policy-binding instagram-ads-472021 \
      --member="serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com" \
      --role="roles/storage.objectCreator"
    gcloud projects add-iam-policy-binding instagram-ads-472021 \
      --member="serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com" \
      --role="roles/storage.legacyBucketReader"
    ```
  - Escopo restrito (exemplo para `facilitador-logs-data`):
    ```bash
    gcloud storage buckets add-iam-policy-binding gs://instagram-ads-472021-facilitador-logs-data \
      --member="serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com" \
      --role="roles/storage.objectCreator"
    gcloud storage buckets add-iam-policy-binding gs://instagram-ads-472021-facilitador-logs-data \
      --member="serviceAccount:instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com" \
      --role="roles/storage.legacyBucketReader"
    ```
    > Ajuste o bucket e repita para o bucket de deliveries, se necessário.

## 4. Configurar a service account localmente
- Garanta que o arquivo `sa-key.json` exista na raiz do projeto (não versionar).
- Em `.env`, mantenha `GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json`.
- Opcional: ativar a service account no CLI para usar os mesmos comandos `gcloud`:
  ```bash
  gcloud auth activate-service-account instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com \
    --key-file=sa-key.json
  gcloud auth application-default set-quota-project instagram-ads-472021
  ```

## 5. Validar permissões da service account
- Vertex AI:
  ```bash
  gcloud ai locations list --project instagram-ads-472021 \
    --impersonate-service-account=instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com
  ```
- Buckets:
  ```bash
  gcloud storage buckets describe gs://instagram-ads-472021-facilitador-logs-data \
    --project instagram-ads-472021 \
    --impersonate-service-account=instagram-ads-sa@instagram-ads-472021.iam.gserviceaccount.com
  ```
  O comando deve retornar metadados sem erros 403/404.

## 6. Rodar o projeto usando a chave
- Instalar dependências (primeira vez): `make install`.
- Subir serviços: `make dev`. O Makefile exporta `GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json` e inicia backend + frontend.
- Verificar logs para garantir ausência de `google.api_core.exceptions.Forbidden` ou 401/403 da Vertex.

## 7. Dicas de operação
- Para confirmar qual credencial está em uso: `echo $GOOGLE_APPLICATION_CREDENTIALS` (deve apontar para `./sa-key.json`).
- Se quiser voltar a usar ADC pessoais, remova `GOOGLE_APPLICATION_CREDENTIALS` do `.env`, rode `gcloud auth application-default login` e `gcloud auth application-default set-quota-project instagram-ads-472021`.
- Mantenha o `sa-key.json` seguro; rotacione a chave se houver suspeita de exposição.
