# Guia de Configuração — Vertex AI (Local) e Preparação para Deploy

Este guia documenta, de forma operacional, tudo que falta para rodar o projeto localmente usando SEMPRE o backend Vertex AI (sem deploy) e o que preparar para um futuro deploy. Também aponta ajustes opcionais no código/projeto quando necessário.

Status atual (conforme seu log):
- Projeto ativo no gcloud: `instagram-ads-472021`.
- Quota Project do ADC alinhado: `gcloud auth application-default set-quota-project instagram-ads-472021` concluído.
- Google Cloud CLI atualizado para v538.x.

Importante: Já foi criado o arquivo `app/.env` com as variáveis para modo Vertex:
- `GOOGLE_GENAI_USE_VERTEXAI=True`
- `GOOGLE_CLOUD_PROJECT=instagram-ads-472021`
- `GOOGLE_CLOUD_LOCATION=us-central1`
- `ALLOW_ORIGINS=*`

---

## 1) Passos no Terminal (obrigatórios)

Execute na raiz do repositório ou em qualquer terminal autenticado no GCP.

1. Selecionar projeto e habilitar APIs necessárias
   - `gcloud config set project instagram-ads-472021`
   - `gcloud services enable aiplatform.googleapis.com storage.googleapis.com logging.googleapis.com`

2. Autenticação (ADC) — se ainda não fez login nesta sessão
   - `gcloud auth login`
   - `gcloud auth application-default login`
   - (Você já fez) `gcloud auth application-default set-quota-project instagram-ads-472021`
   - Validar token: `gcloud auth application-default print-access-token`

3. Criar o bucket de artifacts/logs na região us-central1 (recomendado)
   - Nome esperado pelo servidor: `gs://instagram-ads-472021-facilitador-logs-data`
   - Criação (apenas uma vez):
     - `gcloud storage buckets create gs://instagram-ads-472021-facilitador-logs-data --project=instagram-ads-472021 --location=us-central1 --uniform-bucket-level-access`
   - Verificar região do bucket:
     - `gcloud storage buckets describe gs://instagram-ads-472021-facilitador-logs-data --format='value(location)'`

4. Preparar ambiente local e subir o app (Vertex local)
   - Instalar dependências: `make install`
   - Recomendado (usa nosso FastAPI com bucket e tracing):
     - Backend: `make local-backend`
     - Frontend (em outro terminal): `npm --prefix frontend run dev`
   - Alternativa (“stack” via ADK CLI): `make dev`
     - Observação: este caminho usa o `adk api_server` padrão; para garantir uso do bucket GCS, prefira `make local-backend`.

5. Acesso e smoke test
   - Backend (UI do ADK ativada): `http://localhost:8000`
   - Frontend (se iniciado): `http://localhost:5173`
   - Teste uma geração com payload contendo: `landing_page_url`, `objetivo_final`, `perfil_cliente`, `formato_anuncio`. A saída deve trazer exatamente 3 variações.

Notas:
- Não defina `GOOGLE_API_KEY` no shell quando usar Vertex (não é utilizada neste modo).
- Se aparecer `PERMISSION_DENIED`/`UNAUTHENTICATED`, reexecute `gcloud auth application-default login` e confira o projeto ativo.
- Se surgir `model not found`/404, confirme `GOOGLE_CLOUD_LOCATION=us-central1` e que os modelos estão habilitados nessa região (passo 2 da próxima seção).

---

## 2) Passos no Console do Google Cloud (obrigatórios)

1. Ativar billing (conta de faturamento vinculada ao projeto `instagram-ads-472021`).

2. Habilitar modelos Gemini 2.5 na região selecionada
   - Console → Vertex AI → Generative AI Studio → “Get started”
   - Habilite os modelos Gemini 2.5 em `us-central1`.

3. Verificar Cloud Storage
   - Console → Cloud Storage → Buckets → confirme a existência do bucket `instagram-ads-472021-facilitador-logs-data` com localização `us-central1`.
   - Caso não exista, crie pelo Console na mesma região (`us-central1`) ou use o comando da seção 1.3.

4. IAM (se necessário)
   - Sua conta de usuário, como proprietária do projeto, já deve ter permissões. Em cenários de CI/Service Account, garanta as funções: `Vertex AI User`, `Storage Admin`, `Logs Writer` para a SA utilizada.

---

## 3) Ajustes nos Arquivos do Projeto (implementados)

Foi implementada a parametrização do bucket de artifacts/logs por variáveis de ambiente:

- `app/server.py`
  - Agora lê `ARTIFACTS_BUCKET` e `ARTIFACTS_BUCKET_LOCATION` do ambiente.
  - Fallbacks: se não definir, usa `gs://{PROJECT_ID}-facilitador-logs-data` e a região de `GOOGLE_CLOUD_LOCATION` (ou `us-central1`).
  - Ao iniciar, verifica se o bucket existe e cria caso necessário na região configurada.

- Arquivos de configuração adicionados/atualizados
  - `app/.env` já contém:
    - `GOOGLE_GENAI_USE_VERTEXAI=True`
    - `GOOGLE_CLOUD_PROJECT=instagram-ads-472021`
    - `GOOGLE_CLOUD_LOCATION=us-central1`
    - `ALLOW_ORIGINS=*`
    - `ARTIFACTS_BUCKET=gs://instagram-ads-472021-facilitador-logs-data`
    - `ARTIFACTS_BUCKET_LOCATION=us-central1`
  - `app/.env.example` incluído como referência.

---

## 4) Rotina de Execução (resumo)

Em toda nova sessão de terminal:
1. `gcloud config set project instagram-ads-472021`
2. `set -a; source app/.env; set +a` (opcional, o ADK costuma ler `.env` automaticamente; usar este comando garante as variáveis no shell)
3. Backend: `make local-backend`
4. Frontend: `npm --prefix frontend run dev`

URLs:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

---

## 5) Preparação para Deploy (quando chegar a hora)

Opção A — Cloud Run (container serverless):
- Pré-requisitos: Dockerfile pronto (já existe no repo), ADC configurada, projeto/região.
- Comando base:
  - `gcloud run deploy instagram-ads-generator --source . --region us-central1 --project instagram-ads-472021`
- Observações: definir variáveis de ambiente de produção (se usarmos `ARTIFACTS_BUCKET`, etc.), configurar autenticação (IAP/JWT) conforme necessidade.

Opção B — Vertex AI Agent Engine (gerenciado para ADK):
- Empacote seu `root_agent` como `AdkApp` e crie um Engine:
  - Python (resumo):
    ```python
    from vertexai import agent_engines
    from vertexai.preview import reasoning_engines

    app_for_engine = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)
    remote_app = agent_engines.create(
        agent_engine=app_for_engine,
        requirements=["google-cloud-aiplatform[adk,agent_engines]"],
        display_name="Instagram Ads Generator"
    )
    print(remote_app.resource_name)
    ```
- O frontend do repo já suporta conectar por “Remote Agent Engine ID”.

---

## 6) Troubleshooting Rápido

- 401/403 (auth): `gcloud auth application-default login`; confira projeto/região; verifique permissões “Vertex AI User”.
- 404/model: confirme modelos habilitados em `us-central1` no Console; confira `GOOGLE_CLOUD_LOCATION=us-central1` no `.env`.
- Bucket/região: se criou o bucket com outro nome/região, apague e recrie com o nome esperado em `us-central1`, ou ajuste o código para ler `ARTIFACTS_BUCKET` e `ARTIFACTS_BUCKET_LOCATION`.
- Tempo de resposta: rede local/proxy; tente novamente; confira quotas no Console.

---

Qualquer ponto acima posso automatizar (ex.: parametrização do bucket no código, `.env.example`, script make para habilitar APIs). Diga se aprova as mudanças opcionais e eu aplico.
