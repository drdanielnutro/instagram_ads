# [DEPRECATED – ver docs/entrega_json_final_producao.md]
# Plano de Entrega e Download do JSON Final (Local + GCS)

## Objetivo

Disponibilizar o JSON final gerado pelo pipeline para download de forma simples e robusta:
- Em desenvolvimento local: salvar sempre um arquivo único por execução em `artifacts/ads_final/` e permitir download direto pelo backend.
- Em produção: fazer upload para o Google Cloud Storage (GCS) e disponibilizar um botão no frontend que baixa via URL assinada (Signed URL) ou, em fallback, por streaming via backend.

Este documento descreve os componentes já existentes, o que falta implementar, como validar e como configurar o GCP para que tudo funcione tanto localmente quanto após o deploy.

## Estado Atual (já implementado)

- Persistência ao final do pipeline:
  - Callback `app/callbacks/persist_outputs.py` (chamado por `final_assembler` via `after_agent_callback`):
    - Salva sempre um arquivo local: `artifacts/ads_final/<timestamp>_<session>_<formato>.json`.
    - Se `ARTIFACTS_BUCKET=gs://...` estiver definido, faz upload adicional para GCS em `ads/final/<mesmo_nome>.json`.
    - Escreve no state da sessão:
      - `final_delivery_local_path`: caminho local do arquivo.
      - `final_delivery_gcs_uri`: `gs://bucket/...` (se upload bem-sucedido).
    - Loga: `Final delivery saved locally: ...` e `Final delivery uploaded to GCS: ...`.

- Observação: o pipeline e os prompts não foram alterados; a adição é não-invasiva e não muda o JSON final.

## O que falta implementar

Para habilitar o botão “Baixar JSON” no frontend e compatibilizar dev/prod:

1) Backend — endpoints de entrega (FastAPI)
- `GET /sessions/{app}/{user}/{session}/final_delivery/meta`
  - Retorna um JSON com metadados de entrega: `final_delivery_local_path`, `final_delivery_gcs_uri`, `formato`, `timestamp` (se disponível) e `size` (opcional).
  - 404 se a sessão não existir ou se a execução ainda não tiver gerado o `final_code_delivery`.

- `GET /sessions/{app}/{user}/{session}/final_delivery/download`
  - Se houver `final_delivery_gcs_uri` no state:
    - Opção A (preferida): gerar uma Signed URL (v4) de curta duração (ex.: 10 minutos) e retornar 302 redirect para ela (ou retornar `{ signed_url: "https://..." }`).
    - Opção B (fallback): fazer download do GCS no backend e streamar (custos de egress/latência sobem; preferir Signed URL).
  - Se não houver GCS e houver `final_delivery_local_path`:
    - Abrir o arquivo local e responder com `Content-Type: application/json` e `Content-Disposition: attachment; filename="..."` (download direto).
  - 404 se nenhum artefato estiver disponível.

2) Frontend — botão “Baixar JSON”
- Exibir quando o pipeline finalizar (depois do evento “✅ PRONTO — JSON final disponível”) ou quando `final_code_delivery` chegar via SSE.
- Chamar `GET /sessions/.../final_delivery/meta` para checar disponibilidade.
- Acionar `GET /sessions/.../final_delivery/download` ao clicar:
  - Se retorno for redirect/Signed URL: abrir em nova janela/aba (ou baixar diretamente).
  - Se retorno for stream: baixar como Blob (respeitando o `filename` do header).
- Tratar erros (ex.: “Ainda processando. Tente novamente.”, “Falha ao baixar. Verifique logs.”).

3) Segurança (produção)
- Não deixar bucket público. Usar Signed URL (tempo curto) ou streamar do backend.
- Proteger os endpoints (opcional nesta fase): IAP/JWT/checar vínculo com `sessionId`/`userId` no state.

## Design dos Endpoints (detalhe)

### 1. `GET /sessions/{app}/{user}/{session}/final_delivery/meta`
- Propósito: permitir ao frontend saber se já existe artefato para download e qual a rota recomendada.
- Resposta (200):
```json
{
  "ok": true,
  "final_delivery_local_path": "artifacts/ads_final/20250914-200512_<SESSION>_Feed.json",
  "final_delivery_gcs_uri": "gs://instagram-ads-472021-facilitador-logs-data/ads/final/20250914-200512_<SESSION>_Feed.json",
  "formato": "Feed",
  "timestamp": "2025-09-14T20:05:12Z",
  "size_bytes": 12345
}
```
- Resposta (404): `{"ok": false, "message": "Final delivery not available yet"}`

### 2. `GET /sessions/{app}/{user}/{session}/final_delivery/download`
- Propósito: fornecer o binário do arquivo (stream) ou um redirect para uma Signed URL do GCS.
- Com GCS (preferido):
  - Gerar Signed URL (v4) com expiração curta (ex.: 600s) para o objeto `gs://.../ads/final/<arquivo>.json`.
  - 302 redirect para a Signed URL (ou responder `{ "signed_url": "..." }`).
- Sem GCS (dev):
  - Stream do arquivo local com cabeçalhos apropriados:
    - `Content-Type: application/json`
    - `Content-Disposition: attachment; filename="<arquivo>.json"`
- Erros esperados: 404 (não disponível), 500 (exceção), 403 (permissão GCS — ver seção IAM).

## GCP — Checklist de Configuração

### 1) Projeto e APIs
- Selecionar projeto e habilitar APIs necessárias:
```bash
gcloud config set project instagram-ads-472021
gcloud services enable storage.googleapis.com aiplatform.googleapis.com logging.googleapis.com iamcredentials.googleapis.com
```

### 2) Bucket GCS (artefatos)
- Criar bucket (se não existir), na região `us-central1`:
```bash
gcloud storage buckets create gs://instagram-ads-472021-facilitador-logs-data \
  --location=us-central1 --uniform-bucket-level-access
```
- Verificar configuração do bucket:
```bash
gcloud storage buckets describe gs://instagram-ads-472021-facilitador-logs-data \
  --format='value(location,iamConfiguration.uniformBucketLevelAccess.enabled)'
```
- Listar objetos (verificar uploads de teste):
```bash
gcloud storage ls gs://instagram-ads-472021-facilitador-logs-data/ads/final/
```

### 3) Service Account e permissões
- Descobrir a Service Account do serviço (ex.: Cloud Run):
```bash
gcloud run services describe instagram-ads-generator --region us-central1 \
  --format='value(spec.template.spec.serviceAccountName)'
```
- Conceder acesso ao Storage (upload + leitura):
```bash
gcloud projects add-iam-policy-binding instagram-ads-472021 \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectAdmin"
```
- (Para assinar URLs sem chave privada local) Permitir que a própria SA assine com IAM Credentials:
```bash
gcloud iam service-accounts add-iam-policy-binding SERVICE_ACCOUNT_EMAIL \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/iam.serviceAccountTokenCreator"
```
> Observação: a lib `google-cloud-storage` consegue gerar Signed URLs usando o serviço `iamcredentials.googleapis.com`. O papel `roles/iam.serviceAccountTokenCreator` permite o `signBlob` via IAM no contexto da própria SA.

### 4) Variáveis de ambiente (backend)
- Local (dev):
```bash
export GOOGLE_GENAI_USE_VERTEXAI=True
export GOOGLE_CLOUD_PROJECT=instagram-ads-472021
export GOOGLE_CLOUD_LOCATION=us-central1
# Opcional: ativar upload para GCS em dev
export ARTIFACTS_BUCKET=gs://instagram-ads-472021-facilitador-logs-data
```
- Produção (Cloud Run): definir as mesmas env vars no serviço (Console ou CLI `gcloud run deploy ... --set-env-vars ...`).

### 5) Testes manuais (CLI)
- Baixar do GCS manualmente (verificação rápida):
```bash
gcloud storage cp gs://instagram-ads-472021-facilitador-logs-data/ads/final/<arquivo>.json .
```
- Ver links assinados (se optar por gerar via CLI para teste):
  - Recomenda-se gerar via código; pela CLI, preferir acessar via permissões diretas ou temporariamente tornar um objeto público (não recomendado para produção).

## Fluxo E2E (dev e prod)

1) Usuário envia prompt → `/run_preflight` → 200 com `initial_state` (ou 422 com erros)
2) Frontend cria sessão com `initial_state` e dispara `/run_sse`
3) Pipeline executa:
   - Análise da landing (StoryBrand)
   - 8 tarefas do plano fixo (STRATEGY → … → ASSEMBLY)
   - `final_assembler` escreve `final_code_delivery` no state e dispara o callback que salva local e (se possível) no GCS
4) Ao final: `final_validator=pass` e logs indicam locais de salvamento
5) Frontend chama `/sessions/.../final_delivery/meta` → mostra botão “Baixar JSON”
6) Clique do usuário → `/sessions/.../final_delivery/download`
   - Dev: stream local → download do arquivo
   - Prod: Signed URL (redirect) → download direto do GCS

## Aceites (critério de sucesso)

- Dev:
  - JSON sempre salvo em `artifacts/ads_final/…json` (nome único por execução).
  - `GET .../meta` retorna `final_delivery_local_path` e `ok: true`.
  - `GET .../download` retorna o arquivo (`Content-Disposition: attachment; filename=...`).

- Prod (GCS configurado):
  - `final_delivery_gcs_uri` presente no state e log “uploaded to GCS”.
  - `GET .../download` faz redirect para Signed URL (tempo de expiração curto) ou retorna `{ signed_url: "..." }`.
  - Download funciona sem expor bucket público.

## Pontos de Atenção e Alternativas

- Signed URL:
  - Preferível para produção. Requer `iamcredentials.googleapis.com` habilitado e permissões adequadas à SA (token creator) se não houver chave privada local.
  - Alternativa simplificada: stream via backend (menos seguro/eficiente para grandes volumes; use como fallback).

- Permissões IAM:
  - Upload: `roles/storage.objectAdmin` (ou combinação de `objectCreator` + `objectViewer`).
  - Leitura por Signed URL: não requer conceder `objectViewer` ao usuário final.

- Segurança dos endpoints:
  - Nesta fase, sem controle de acesso; em produção, proteger via IAP/JWT e checagens de sessão.

- Nomes de arquivo:
  - Incluem `timestamp`, `sessionId` e `formato` para garantir unicidade e rastreabilidade.

## Análise de Inconsistências (revisão)

- Persistência atual: já salva local e em GCS opcionalmente; escreve caminhos no state — consistente com o fluxo.
- Frontend: precisa apenas consultar `meta` e chamar `download` — não há dependência forte de mudanças no pipeline.
- IAM e APIs: detalhadas com comandos `gcloud`; sem isso, Signed URL pode falhar (403). Alternativa de stream cobre o gap em dev e durante ajustes.
- Backward compatibility: sem GCS, tudo funciona em dev; com GCS, preferir Signed URL.
- Observabilidade: logs já indicam onde foi salvo; endpoints `meta`/`download` podem logar as chamadas e respostas.

Conclusão: plano consistente e incremental; não quebra a geração (3 variações), garante download em dev e provê caminho seguro para produção via Signed URL.
