# Plano Completo de Implementação - Sistema de Download de JSONs Finais

## 📋 Análise da Situação Atual

### ✅ O que já está funcionando:
1. **Persistência melhorada** (`persist_outputs.py`):
   - Extração de `user_id` com fallback
   - Fix do formato "unknown"
   - Salvamento local + GCS com estrutura `deliveries/{user_id}/{session_id}/`
   - Criação de arquivo meta local e no GCS
   - Uso de `DELIVERIES_BUCKET` (separado do `ARTIFACTS_BUCKET`)

2. **Configuração do servidor** (`server.py`):
   - Auto-criação de bucket desabilitada por padrão (boa prática)
   - Preparado para incluir router de delivery (linha 79-83)

### ❌ O que falta implementar:
1. Endpoints HTTP para download
2. Geração de Signed URLs
3. Configuração de IAM/permissões
4. Variáveis de ambiente para produção
5. Frontend: botão de download

## 🎯 Plano de Implementação Detalhado

### Fase 1: Criar Router de Delivery (Backend)

#### 1.1. Criar arquivo `app/routers/delivery.py`:

```python
# Estrutura completa do router com:
- GET /sessions/{app}/{user}/{session}/final_delivery/meta
  → Retorna metadados do JSON (local_path, gcs_uri, formato, timestamp)

- GET /sessions/{app}/{user}/{session}/final_delivery/download
  → Gera Signed URL (produção) ou stream local (dev)

- GET /sessions/{app}/{user}/{session}/final_delivery/status
  → Verifica se delivery existe (200/404)
```

#### 1.2. Implementar helper para detecção de ambiente:
```python
def get_storage_client():
    """Detecta Cloud Run vs Dev e retorna cliente apropriado"""
    if os.getenv("K_SERVICE"):  # Cloud Run
        return storage.Client()
    # Dev: tentar sa-key.json ou gcloud auth
```

#### 1.3. Implementar cache de metadados:
```python
_DELIVERY_CACHE = {}  # {session_id: metadata}
_DELIVERY_CACHE_MAX = 100  # Limite com eviction FIFO
```

### Fase 2: Configuração de Ambiente

#### 2.1. Criar `.env.example` atualizado:
```bash
# ADK Artifacts (interno - não modificar)
ARTIFACTS_BUCKET=gs://projeto-facilitador-logs-data

# Deliveries (JSONs finais para download)
DELIVERIES_BUCKET=gs://projeto-deliveries-data
DELIVERIES_BUCKET_LOCATION=us-central1

# Controles
ENABLE_AUTO_BUCKET_CREATE=false  # true apenas em dev
ENABLE_SIGNED_URLS=true         # false para usar stream direto
SIGNED_URL_EXPIRATION_MINUTES=10
```

#### 2.2. Atualizar `server.py`:
- Propagar `DELIVERIES_BUCKET` para `os.environ` após leitura
- Garantir que callbacks herdem a variável

### Fase 3: Configuração GCP (Produção)

#### 3.1. Criar bucket de deliveries:
```bash
gcloud storage buckets create gs://projeto-deliveries-data \
  --location=us-central1 \
  --uniform-bucket-level-access
```

#### 3.2. Configurar IAM:
```bash
# Service Account precisa de:
# 1. Acesso ao bucket
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/storage.objectAdmin"

# 2. Permissão para gerar Signed URLs
gcloud iam service-accounts add-iam-policy-binding SA_EMAIL \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/iam.serviceAccountTokenCreator"
```

#### 3.3. Habilitar APIs necessárias:
```bash
gcloud services enable storage.googleapis.com
gcloud services enable iamcredentials.googleapis.com
```

### Fase 4: Frontend - Botão de Download

#### 4.1. Adicionar componente `DownloadButton.tsx`:
```typescript
// Componente que:
- Aparece quando recebe evento "JSON final disponível"
- Chama /final_delivery/status para verificar
- Ao clicar, chama /final_delivery/download
- Se receber signed_url, abre em nova aba
- Trata erros (404, 500, timeout)
```

#### 4.2. Integrar no fluxo existente:
- Detectar evento de conclusão no SSE
- Habilitar botão após validação final

### Fase 5: Testes e Validação

#### 5.1. Testes locais:
```bash
# 1. Executar pipeline completo
make dev

# 2. Verificar salvamento local
ls artifacts/ads_final/
ls artifacts/ads_final/meta/

# 3. Testar endpoints
curl http://localhost:8000/sessions/app/user1/SESSION_ID/final_delivery/meta
curl http://localhost:8000/sessions/app/user1/SESSION_ID/final_delivery/download
```

#### 5.2. Testes em staging:
- Deploy em Cloud Run de staging
- Verificar Signed URLs funcionando
- Testar download pelo frontend

### Fase 6: Documentação

#### 6.1. Atualizar README.md:
- Adicionar seção "Download de JSONs Finais"
- Documentar endpoints disponíveis
- Incluir exemplos de uso

#### 6.2. Criar `docs/download_architecture.md`:
- Diagrama do fluxo completo
- Decisões de design (bucket separado, signed URLs)
- Troubleshooting comum

## 📊 Ordem de Execução

1. **Primeiro**: Router de delivery (`delivery.py`)
2. **Segundo**: Configuração de ambiente (`.env.example`)
3. **Terceiro**: Setup GCP (buckets, IAM)
4. **Quarto**: Testes locais
5. **Quinto**: Frontend (se tempo permitir)
6. **Último**: Documentação

## ⚠️ Pontos Críticos de Atenção

1. **Segurança**:
   - Validar session_id para prevenir path traversal
   - Signed URLs com expiração curta (10 min)
   - Não expor listagem global de deliveries

2. **Performance**:
   - Cache de metadados em memória
   - Eviction FIFO para prevenir memory leak
   - Não carregar JSON completo para gerar URL

3. **Robustez**:
   - Fallback de Signed URL para stream local
   - Detecção automática de ambiente
   - Logs detalhados para debugging

4. **Compatibilidade**:
   - Manter `ARTIFACTS_BUCKET` para ADK
   - Usar `DELIVERIES_BUCKET` separado
   - Não quebrar código existente

## 🎯 Resultado Esperado

Ao final, o sistema terá:
- ✅ JSONs salvos em bucket dedicado de deliveries
- ✅ Endpoints REST para meta/download
- ✅ Signed URLs em produção, stream em dev
- ✅ Cache eficiente de metadados
- ✅ Frontend com botão de download (opcional)
- ✅ Documentação completa
- ✅ Testes validados local e staging

## 📝 Código de Exemplo - Router Completo

```python
# app/routers/delivery.py
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from datetime import timedelta
from typing import Optional, Dict, Any
import json
import logging
import os
from google.cloud import storage
from google.api_core import exceptions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/delivery/final", tags=["delivery"])

# Cache simples para metadados
_DELIVERY_CACHE: Dict[str, Dict[str, Any]] = {}
_DELIVERY_CACHE_MAX = 100

def get_storage_client():
    """Cria cliente GCS apropriado para o ambiente."""
    if os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"):
        # Cloud Run - usar ADC
        return storage.Client()

    # Dev - tentar sa-key.json
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./sa-key.json")
    if Path(creds_path).exists():
        return storage.Client.from_service_account_json(creds_path)

    # Fallback para gcloud auth
    return storage.Client()

def _get_meta_from_cache_or_file(session_id: str) -> Optional[Dict[str, Any]]:
    """Busca metadados do cache ou arquivo local."""
    # Tentar cache primeiro
    if session_id in _DELIVERY_CACHE:
        return _DELIVERY_CACHE[session_id]

    # Tentar arquivo local
    meta_file = Path(f"artifacts/ads_final/meta/{session_id}.json")
    if meta_file.exists():
        try:
            with open(meta_file) as f:
                meta = json.load(f)
                # Adicionar ao cache
                if len(_DELIVERY_CACHE) >= _DELIVERY_CACHE_MAX:
                    # Eviction FIFO
                    oldest = next(iter(_DELIVERY_CACHE))
                    del _DELIVERY_CACHE[oldest]
                _DELIVERY_CACHE[session_id] = meta
                return meta
        except Exception as e:
            logger.error(f"Erro ao ler meta file: {e}")

    return None

@router.get("/meta")
async def get_delivery_meta(
    user_id: str = Query(..., description="ID do usuário"),
    session_id: str = Query(..., description="ID da sessão")
):
    """Retorna metadados do JSON final."""

    meta = _get_meta_from_cache_or_file(session_id)

    if not meta:
        raise HTTPException(404, detail="Delivery não encontrada")

    # Validar user_id
    if meta.get("user_id") != user_id:
        logger.warning(f"User ID mismatch: esperado={meta.get('user_id')}, recebido={user_id}")
        raise HTTPException(403, detail="Acesso negado")

    return {
        "ok": True,
        **meta
    }

@router.get("/download")
async def download_delivery(
    user_id: str = Query(..., description="ID do usuário"),
    session_id: str = Query(..., description="ID da sessão")
):
    """Gera URL para download do JSON final."""

    meta = _get_meta_from_cache_or_file(session_id)

    if not meta:
        raise HTTPException(404, detail="Delivery não encontrada")

    # Validar user_id
    if meta.get("user_id") != user_id:
        raise HTTPException(403, detail="Acesso negado")

    # Se tem GCS e Signed URLs habilitado
    if meta.get("final_delivery_gcs_uri") and os.getenv("ENABLE_SIGNED_URLS", "true").lower() == "true":
        try:
            # Extrair bucket e path
            gcs_uri = meta["final_delivery_gcs_uri"]
            # gs://bucket/path/to/file.json
            parts = gcs_uri.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1]

            storage_client = get_storage_client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            if not blob.exists():
                logger.error(f"Blob não existe no GCS: {gcs_uri}")
                # Fallback para arquivo local
                if meta.get("final_delivery_local_path"):
                    from fastapi.responses import FileResponse
                    return FileResponse(
                        meta["final_delivery_local_path"],
                        media_type="application/json",
                        filename=f"ads_{session_id}.json"
                    )
                raise HTTPException(404, detail="Arquivo não encontrado")

            # Gerar Signed URL v4
            expiration_minutes = int(os.getenv("SIGNED_URL_EXPIRATION_MINUTES", "10"))
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET",
                response_disposition=f'attachment; filename="ads_{session_id}.json"',
                response_type="application/json"
            )

            return {
                "signed_url": url,
                "expires_in": expiration_minutes * 60,
                "filename": meta.get("filename", f"ads_{session_id}.json")
            }

        except exceptions.NotFound:
            logger.error(f"Bucket ou blob não encontrado: {meta.get('final_delivery_gcs_uri')}")
        except Exception as e:
            logger.error(f"Erro ao gerar signed URL: {e}")
            # Continuar para fallback

    # Fallback: arquivo local
    if meta.get("final_delivery_local_path"):
        local_path = Path(meta["final_delivery_local_path"])
        if local_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(
                str(local_path),
                media_type="application/json",
                filename=f"ads_{session_id}.json"
            )

    raise HTTPException(404, detail="Arquivo não disponível para download")

@router.get("/status")
async def check_delivery_status(
    user_id: str = Query(..., description="ID do usuário"),
    session_id: str = Query(..., description="ID da sessão")
):
    """Verifica se delivery existe (200) ou não (404)."""

    meta = _get_meta_from_cache_or_file(session_id)

    if not meta:
        raise HTTPException(404, detail="Delivery não encontrada")

    if meta.get("user_id") != user_id:
        raise HTTPException(403, detail="Acesso negado")

    return {
        "status": "ready",
        "session_id": session_id,
        "formato": meta.get("formato"),
        "timestamp": meta.get("timestamp")
    }
```

## 🚀 Comandos GCP para Setup Completo

```bash
# 1. Configurar projeto
export PROJECT_ID=instagram-ads-472021
gcloud config set project $PROJECT_ID

# 2. Criar bucket de deliveries
gcloud storage buckets create gs://${PROJECT_ID}-deliveries \
  --location=us-central1 \
  --uniform-bucket-level-access

# 3. Obter Service Account do Cloud Run (se já deployado)
SA_EMAIL=$(gcloud run services describe instagram-ads-generator \
  --region=us-central1 \
  --format='value(spec.template.spec.serviceAccountName)')

# Ou usar Service Account padrão do projeto
SA_EMAIL=${PROJECT_ID}@appspot.gserviceaccount.com

# 4. Conceder permissões
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator"

# 5. Habilitar APIs
gcloud services enable storage.googleapis.com
gcloud services enable iamcredentials.googleapis.com

# 6. Verificar configuração
gcloud storage buckets describe gs://${PROJECT_ID}-deliveries
gcloud iam service-accounts get-iam-policy $SA_EMAIL
```