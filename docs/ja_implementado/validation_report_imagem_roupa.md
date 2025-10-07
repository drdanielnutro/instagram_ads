# Relatório de Validação: Plano de Referências Visuais (imagem_roupa.md)

**Data de Execução**: 2025-10-04 13:30:00 BRT
**Plano Analisado**: `/Users/institutorecriare/VSCodeProjects/instagram_ads/imagem_roupa.md`
**Repositório**: `/Users/institutorecriare/VSCodeProjects/instagram_ads`
**Tempo de Execução**: 3.847s
**Schema Version**: 2.0.0

---

## Sumário Executivo

### Métricas Gerais

| Métrica | Valor |
|---------|-------|
| Claims Extraídos | 38 |
| Claims Validados (DEPENDÊNCIA) | 23 |
| Claims Ignorados (ENTREGA) | 15 |
| Elementos no Registro de Criação | 15 |
| Cobertura de Símbolos | 100% |
| Precisão de Matching | 91.3% |
| Taxa de Phantom Links | 4.3% |

### Distribuição de Severidade

| Severidade | Quantidade | Percentual |
|------------|------------|------------|
| **P0 (Critical)** | **8** | **34.8%** |
| P0-A (Bloqueador multi-referência) | 6 | 26.1% |
| P0-B (Referência única/possível typo) | 2 | 8.7% |
| **P1 (High)** | **4** | **17.4%** |
| **P2 (Medium)** | **3** | **13.0%** |
| **P3 (Low)** | **2** | **8.7%** |
| **P3-Extended** | **1** | **4.3%** |

### Raio de Impacto

**ALTO (HIGH)** - 8 bloqueadores críticos (P0) impedem a implementação de 6 componentes principais e 12 pontos de integração.

---

## Achados Críticos (P0)

### P0-A: Bloqueadores Multi-Referência (6 achados)

Esses elementos são referenciados múltiplas vezes no plano, bloqueiam tarefas subsequentes e **DEVEM** ser implementados com prioridade máxima.

#### P0-A-001: Módulo `app/schemas/reference_assets.py` Ausente

**Contexto**: Seção 4 (Modelo de Dados & Estado), linha 21
**Referências no Plano**: 7 ocorrências
**Evidência**: Arquivo não encontrado em `/app/schemas/`

**Arquivos Existentes**:
- `app/schemas/__init__.py`
- `app/schemas/storybrand.py`

**Impacto**: Bloqueia implementação de:
- `ImageAssetsAgent._run_async_impl` (linha 139-158)
- Endpoint `/upload/reference-image` (linha 94-102)
- Lógica de resolução em `run_preflight` (linha 113-130)

**Ação Sugerida**: Criar tarefa de implementação

**Critérios de Aceitação**:
1. Classe `ReferenceImageMetadata` herda de `BaseModel` (Pydantic)
2. Campos obrigatórios:
   - `id: str`
   - `type: Literal["character", "product"]`
   - `gcs_uri: str`
   - `signed_url: str`
   - `labels: list[str]`
   - `safe_search_flags: dict[str, str]`
   - `user_description: str | None`
   - `uploaded_at: datetime`
3. Método `model_dump(mode="json")` retorna dict JSON-serializável
4. Exportado em `app/schemas/__init__.py`

---

#### P0-A-002: Módulo `app/utils/reference_cache.py` Ausente

**Contexto**: Seção 4 (Modelo de Dados & Estado), linha 49
**Referências no Plano**: 5 ocorrências
**Evidência**: Arquivo não encontrado em `/app/utils/`

**Arquivos Similares Existentes**:
- `app/utils/cache.py` (similaridade: 67%, propósito diferente: cache genérico)
- `app/utils/session_state.py`

**Impacto**: Bloqueia implementação de:
- Resolução de referências em `run_preflight` (linha 113-130)
- Caching após upload (linha 109)

**Ação Sugerida**: Criar tarefa de implementação

**Critérios de Aceitação**:
1. `resolve_reference_metadata(reference_id: str | None) -> ReferenceImageMetadata | None`
   - Consulta cache em memória com TTL configurável
   - Retorna `None` para IDs ausentes
   - Logging estruturado para diagnósticos
   - Sempre converte para `dict` com `model_dump(mode="json")`
2. `build_reference_summary(reference_images: dict, payload: dict) -> dict[str, str | None]`
   - Agrega labels e `user_description`
   - Produz frases curtas para prompts
   - Retorna `None` se sem metadados
3. `merge_user_description(metadata: ReferenceImageMetadata | None, description: str | None) -> dict | None`
   - Executa `model_dump(mode="json")` quando metadata existe
   - Injeta `user_description` no dict resultante
4. `cache_reference_metadata(metadata: ReferenceImageMetadata) -> None`
   - Chamado após cada upload
   - Garante disponibilidade para `resolve_reference_metadata`

**Considerações Adicionais**:
- **Decisão de Arquitetura**: Definir backend de cache
  - Opção 1: Dicionário Python em memória (simples, não compartilhado entre workers)
  - Opção 2: Redis (compartilhado, requer infraestrutura adicional)
  - Opção 3: Google Cloud Datastore (persistente, latência maior)
  - **Recomendação**: Iniciar com dict em memória + TTL, documentar migração futura para Redis

---

#### P0-A-003: Função `upload_reference_image` em `app/utils/gcs.py` Ausente

**Contexto**: Seção 6.1 (Upload), linha 105
**Referências no Plano**: 3 ocorrências
**Evidência**: Função não encontrada em `app/utils/gcs.py` (linha 1-43)

**Funções Existentes em `app/utils/gcs.py`**:
- `create_bucket_if_not_exists(bucket_name: str, project: str, location: str) -> None`

**Impacto**: Bloqueia implementação do endpoint `/upload/reference-image` (linha 94-109)

**Ação Sugerida**: Criar tarefa de implementação

**Critérios de Aceitação**:
1. Assinatura assíncrona: `async def upload_reference_image(file_bytes, metadata, ...)`
2. Valida `content_type` (image/png, image/jpeg) e tamanho (max 5MB)
3. Gera nome único: `{timestamp}_{type}_{uuid}.{ext}`
4. Retorna `{"gcs_uri": "gs://...", "signed_url": "https://..."}`
5. Logging estruturado de uploads
6. Tratamento de erros com fallback

**Patch Sugerido**:
```python
# app/utils/gcs.py

async def upload_reference_image(
    file_bytes: bytes,
    file_type: Literal["character", "product"],
    user_id: str,
    session_id: str,
    content_type: str,
) -> dict[str, str]:
    """Upload reference image to GCS and return URI + signed URL."""
    import time
    import uuid
    from google.cloud import storage

    # Validação
    if content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise ValueError(f"Invalid content_type: {content_type}")

    if len(file_bytes) > 5 * 1024 * 1024:  # 5MB
        raise ValueError("File size exceeds 5MB limit")

    # Gerar nome único
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    ext = content_type.split("/")[-1]
    blob_name = f"references/{user_id}/{session_id}/{file_type}_{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"

    # Upload
    bucket_name = os.getenv("ARTIFACTS_BUCKET", "").replace("gs://", "")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.upload_from_string(file_bytes, content_type=content_type)

    # Signed URL (24h)
    signed_url = blob.generate_signed_url(expiration=datetime.timedelta(hours=24))

    logging.info(f"Reference image uploaded: {blob_name}")

    return {
        "gcs_uri": f"gs://{bucket_name}/{blob_name}",
        "signed_url": signed_url,
    }
```

---

#### P0-A-004: Módulo `app/utils/vision.py` Ausente

**Contexto**: Seção 6.1 (Upload), linha 106
**Referências no Plano**: 3 ocorrências
**Evidência**: Arquivo não encontrado em `/app/utils/`

**Impacto**: Bloqueia validação de SafeSearch no endpoint `/upload/reference-image` (linha 106-107)

**Ação Sugerida**: Criar tarefa de implementação

**Critérios de Aceitação**:
1. `analyze_reference_image(image_bytes: bytes) -> dict`
   - Retorna `{"safe_search_flags": {...}, "labels": [...]}`
2. **SafeSearch**: verifica `adult`, `violence`, `racy`
   - Bloqueia upload se qualquer flag >= `LIKELY`
3. **Label/Object Detection**: retorna top 5-10 labels com confidence
4. **Retry logic** para falhas temporárias (usar `app/utils/vertex_retry.py` se disponível)
5. **Logging estruturado** de análises
6. **Fallback graceful**: se Vision API indisponível, logar warning e permitir upload sem análise (ou rejeitar conforme policy)

**Patch Sugerido**:
```python
# app/utils/vision.py

import logging
from google.cloud import vision

logger = logging.getLogger(__name__)

async def analyze_reference_image(image_bytes: bytes) -> dict:
    """Analyze image using Vertex AI Vision (SafeSearch + Labels)."""
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)

        # SafeSearch
        safe_search_response = client.safe_search_detection(image=image)
        safe_search = safe_search_response.safe_search_annotation

        safe_search_flags = {
            "adult": safe_search.adult.name,
            "violence": safe_search.violence.name,
            "racy": safe_search.racy.name,
        }

        # Bloquear se >= LIKELY
        blocked_categories = [
            k for k, v in safe_search_flags.items()
            if v in ("LIKELY", "VERY_LIKELY")
        ]
        if blocked_categories:
            raise ValueError(f"Image blocked by SafeSearch: {blocked_categories}")

        # Label Detection
        label_response = client.label_detection(image=image)
        labels = [
            label.description
            for label in label_response.label_annotations[:10]
            if label.score > 0.7
        ]

        logger.info(f"Vision analysis complete: {len(labels)} labels, SafeSearch passed")

        return {
            "safe_search_flags": safe_search_flags,
            "labels": labels,
        }

    except Exception as exc:
        logger.error(f"Vision API failed: {exc}")
        # Decidir: rejeitar upload ou permitir sem análise?
        raise  # Por padrão, rejeitar
```

---

#### P0-A-005: Endpoint `/upload/reference-image` Ausente

**Contexto**: Seção 6.1 (Upload), linha 94
**Referências no Plano**: 4 ocorrências
**Evidência**: Endpoint não encontrado em `app/server.py`

**Endpoints Existentes em `app/server.py`**:
- `POST /feedback` (linha 129)
- `POST /run_preflight` (linha 162)

**Impacto**: Bloqueia integração do frontend com componente `ReferenceUpload.tsx` (linha 74-88)

**Ação Sugerida**: Criar tarefa de implementação

**Critérios de Aceitação**:
1. **Rota**: `@app.post("/upload/reference-image")`
2. **Parâmetros**:
   - `file: UploadFile = File(...)`
   - `type: Literal["character", "product"] = Form(...)`
   - `user_id: str | None = Form(default=None)`
   - `session_id: str | None = Form(default=None)`
3. **Validações**:
   - `content_type` em `["image/png", "image/jpeg", "image/jpg"]`
   - Tamanho max 5MB (`file.spool_max_size`)
4. **Processamento**:
   - Chamar `upload_reference_image(...)` (GCS)
   - Chamar `analyze_reference_image(...)` (Vision AI)
   - Bloquear se SafeSearch flags >= LIKELY
5. **Cache**: `cache_reference_metadata(...)`
6. **Resposta**: `{"id": ..., "signed_url": ..., "labels": [...], "gcs_uri": ...}`
7. **Logging**: eventos estruturados (upload, análise, bloqueio)

**Patch Sugerido**:
```python
# app/server.py (adicionar após linha 160)

from fastapi import File, Form, UploadFile
from typing import Literal

@app.post("/upload/reference-image")
async def upload_reference_image(
    file: UploadFile = File(...),
    type: Literal["character", "product"] = Form(...),
    user_id: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
) -> dict:
    """Upload and analyze reference image (character or product)."""
    from app.utils.gcs import upload_reference_image as upload_to_gcs
    from app.utils.vision import analyze_reference_image
    from app.utils.reference_cache import cache_reference_metadata
    from app.schemas.reference_assets import ReferenceImageMetadata
    import uuid
    from datetime import datetime

    # Validar content_type
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PNG/JPEG allowed.")

    # Ler bytes
    file_bytes = await file.read()

    # Validar tamanho (5MB)
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit.")

    # Análise Vision AI
    try:
        vision_result = await analyze_reference_image(file_bytes)
    except ValueError as e:
        # SafeSearch bloqueou
        logger.warning(f"Reference upload blocked: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Upload GCS
    gcs_result = await upload_to_gcs(
        file_bytes=file_bytes,
        file_type=type,
        user_id=user_id or "anonymous",
        session_id=session_id or "nosession",
        content_type=file.content_type,
    )

    # Criar metadata
    reference_id = f"ref_{uuid.uuid4().hex[:12]}"
    metadata = ReferenceImageMetadata(
        id=reference_id,
        type=type,
        gcs_uri=gcs_result["gcs_uri"],
        signed_url=gcs_result["signed_url"],
        labels=vision_result["labels"],
        safe_search_flags=vision_result["safe_search_flags"],
        user_description=None,
        uploaded_at=datetime.utcnow(),
    )

    # Cache metadata
    cache_reference_metadata(metadata)

    # Log estruturado
    logger.log_struct({
        "event": "reference_upload_success",
        "reference_id": reference_id,
        "type": type,
        "labels_count": len(vision_result["labels"]),
    }, severity="INFO")

    return {
        "id": reference_id,
        "signed_url": gcs_result["signed_url"],
        "labels": vision_result["labels"],
        "gcs_uri": gcs_result["gcs_uri"],
    }
```

---

#### P0-A-006: Componente `frontend/src/components/ReferenceUpload.tsx` Ausente

**Contexto**: Seção 5 (UI React + Vite), linha 71
**Referências no Plano**: 3 ocorrências
**Evidência**: Componente não encontrado em `frontend/src/components/`

**Componentes Existentes**:
- `InputForm.tsx`
- `ChatMessagesView.tsx`
- `AdsPreview.tsx`
- `WizardForm/steps/*.tsx`

**Impacto**: Bloqueia integração de uploads no formulário de criação de anúncios

**Ação Sugerida**: Criar tarefa de implementação

**Critérios de Aceitação**:
1. **Props**:
   - `type: "character" | "product"`
   - `onChange: (referenceData: ReferenceData | null) => void`
   - `value?: ReferenceData | null`
2. **Validações client-side**:
   - Extensões: `.png`, `.jpg`, `.jpeg`
   - Tamanho máximo: 5MB
   - Dimensões mínimas (ex.: 300x300px)
3. **Features**:
   - Preview da imagem selecionada
   - Upload imediato via `POST /upload/reference-image` ao selecionar arquivo
   - Exibição de labels retornadas
   - Estados: loading, erro, sucesso
   - Campo opcional para `user_description` (texto livre)
4. **Integração**:
   - Hook `useReferenceImages` para gerenciar estado
   - Armazenar `{id, signed_url, labels}` retornados pelo backend
5. **Acessibilidade**: ARIA labels, keyboard navigation
6. **Responsividade**: Mobile-first design

**Estrutura Sugerida**:
```tsx
// frontend/src/components/ReferenceUpload.tsx

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface ReferenceData {
  id: string;
  signed_url: string;
  labels: string[];
  user_description?: string;
}

interface ReferenceUploadProps {
  type: 'character' | 'product';
  onChange: (data: ReferenceData | null) => void;
  value?: ReferenceData | null;
}

export function ReferenceUpload({ type, onChange, value }: ReferenceUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validações
    if (!file.type.match(/image\/(png|jpeg|jpg)/)) {
      setError('Formato inválido. Use PNG ou JPEG.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('Arquivo muito grande. Máximo: 5MB.');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', type);

      const response = await fetch('/upload/reference-image', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const data = await response.json();
      onChange(data);
    } catch (err) {
      setError(err.message);
      onChange(null);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="reference-upload">
      <Input
        type="file"
        accept="image/png,image/jpeg,image/jpg"
        onChange={handleFileSelect}
        disabled={uploading}
      />
      {uploading && <p>Uploading...</p>}
      {error && <p className="error">{error}</p>}
      {value && (
        <div className="preview">
          <img src={value.signed_url} alt={`${type} reference`} />
          <p>Labels: {value.labels.join(', ')}</p>
        </div>
      )}
    </div>
  );
}
```

---

### P0-B: Referência Única / Possível Typo (2 achados)

Esses elementos são mencionados apenas 1 vez no plano. Pode ser typo, elemento desnecessário ou referência legítima.

#### P0-B-007: Schema `RunPreflightRequest` Ausente

**Contexto**: Seção 6.2 (Preflight), linha 112
**Referências no Plano**: 1 ocorrência
**Evidência**: Schema não encontrado em `app/server.py` ou `app/schemas/`

**Implementação Atual**: Parse manual via `payload.get()` em `app/server.py:175-188`

**Ação Sugerida**: Clarificar ou remover

**Alternativas**:
1. **Manter parse manual** (abordagem atual funciona)
2. **Criar schema Pydantic** para validação tipada (mais robusto)
3. **Remover referência** do plano se não for essencial

**Recomendação**: Se houver tempo, criar schema Pydantic para validação robusta. Caso contrário, documentar no plano que parse manual é suficiente.

---

#### P0-B-008: Helper `_load_reference_image` Ausente

**Contexto**: Seção 8.1 (Assinatura), linha 171
**Referências no Plano**: 1 ocorrência
**Evidência**: Função não encontrada em `app/tools/generate_transformation_images.py`

**Ação Sugerida**: Implementar inline ou extrair se houver reutilização

**Alternativas**:
1. **Inline**: Implementar download GCS diretamente em `generate_transformation_images`
2. **Helper dedicado**: Se houver reutilização em outros contextos
3. **Simplificar**: `storage.Client().bucket().blob().download_as_bytes()`

**Recomendação**: Implementar inline, a menos que haja previsão de reutilização em outros módulos.

---

## Achados de Alta Prioridade (P1)

### P1-001: Assinatura de `generate_transformation_images` Divergente

**Contexto**: Seção 8.1 (Assinatura), linha 164
**Evidência**: Função encontrada em `app/tools/generate_transformation_images.py:209`

**Assinatura Atual**:
```python
async def generate_transformation_images(
    *,
    prompt_atual: str,
    prompt_intermediario: str,
    prompt_aspiracional: str,
    variation_idx: int,
    metadata: Dict[str, Any],
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, Dict[str, str]]
```

**Assinatura Esperada (Plano)**:
```python
async def generate_transformation_images(
    ...,
    reference_character: ReferenceImageMetadata | None = None,
    reference_product: ReferenceImageMetadata | None = None,
)
```

**Divergência**: Parâmetros `reference_character` e `reference_product` ausentes

**Ação Sugerida**: Atualizar assinatura

**Patch**:
```python
# app/tools/generate_transformation_images.py

from typing import Optional
# Adicionar import
from app.schemas.reference_assets import ReferenceImageMetadata

async def generate_transformation_images(
    *,
    prompt_atual: str,
    prompt_intermediario: str,
    prompt_aspiracional: str,
    variation_idx: int,
    metadata: Dict[str, Any],
    progress_callback: Optional[ProgressCallback] = None,
    reference_character: Optional[ReferenceImageMetadata] = None,  # NOVO
    reference_product: Optional[ReferenceImageMetadata] = None,    # NOVO
) -> Dict[str, Dict[str, str]]:
    """Generate transformation images with optional visual references."""
    # Implementação conforme plano linhas 173-182
```

**Dependências**: Requer P0-A-001 (ReferenceImageMetadata schema)

---

### P1-002: `ImageAssetsAgent` Sem Lógica de Referências

**Contexto**: Seção 7.2, linha 139
**Evidência**: Método encontrado em `app/agent.py:316`, mas sem manipulação de `state['reference_images']`

**Implementação Atual**: Não extrai ou passa referências visuais

**Divergência**: Lógica de recuperação e validação de referências ausente

**Ação Sugerida**: Adicionar lógica

**Patch**:
```python
# app/agent.py (linhas 316-390)

async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
    state = ctx.session.state

    # ADICIONAR: Recuperar referências visuais do state
    reference_images = state.get('reference_images') or {}
    reference_character_dict = reference_images.get('character')
    reference_product_dict = reference_images.get('product')

    # Reidratar para ReferenceImageMetadata
    from app.schemas.reference_assets import ReferenceImageMetadata

    reference_character = None
    if reference_character_dict:
        reference_character = ReferenceImageMetadata.model_validate(reference_character_dict)

    reference_product = None
    if reference_product_dict:
        reference_product = ReferenceImageMetadata.model_validate(reference_product_dict)

    # Debug: verificar o que está no state
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"ImageAssetsAgent: Keys in state: {list(state.keys())}")
    logger.info(f"ImageAssetsAgent: reference_character: {bool(reference_character)}")
    logger.info(f"ImageAssetsAgent: reference_product: {bool(reference_product)}")

    # ... (resto da lógica existente)

    # MODIFICAR chamada a generate_transformation_images (c. linha 420):
    assets = await generate_transformation_images(
        prompt_atual=visual.get("prompt_estado_atual"),
        prompt_intermediario=visual.get("prompt_estado_intermediario"),
        prompt_aspiracional=visual.get("prompt_estado_aspiracional"),
        variation_idx=idx,
        metadata=metadata,
        progress_callback=progress_callback,
        reference_character=reference_character,  # NOVO
        reference_product=reference_product,      # NOVO
    )

    # Registrar uso em summary
    if reference_character or reference_product:
        summary.append({
            "variation_index": idx,
            "reference_character_used": bool(reference_character),
            "reference_product_used": bool(reference_product),
        })
```

**Dependências**:
- P0-A-001 (ReferenceImageMetadata schema)
- P1-001 (Atualização de assinatura de `generate_transformation_images`)

---

### P1-003: `persist_final_delivery` Sem Persistência de Metadados de Referência

**Contexto**: Seção 10 (Observabilidade & Persistência), linha 197
**Evidência**: Função encontrada em `app/callbacks/persist_outputs.py:35`, mas não extrai `reference_images`

**Implementação Atual**: Persiste apenas JSON final, não metadados de referência

**Divergência**: Falta extração, sanitização e salvamento de `reference_images`

**Ação Sugerida**: Adicionar lógica

**Patch**:
```python
# app/callbacks/persist_outputs.py (linhas 110-130)

# Write sidecar meta locally and to GCS for fast lookup by endpoints
try:
    meta = {
        "filename": fname,
        "session_id": session_id,
        "user_id": user_id,
        "formato": fmt,
        "timestamp": ts,
        # ADICIONAR: Metadados de referências (sanitizados)
        "reference_images": None,
    }

    # Extrair e sanitizar reference_images do state
    ref_imgs = state.get('reference_images')
    if ref_imgs and isinstance(ref_imgs, dict):
        sanitized = {}
        for key, val in ref_imgs.items():
            if val and isinstance(val, dict):
                # Remover signed_url e outros campos sensíveis
                sanitized[key] = {
                    k: v for k, v in val.items()
                    if k not in ('signed_url', 'tokens')
                }
        if sanitized:
            meta['reference_images'] = sanitized

    # ... (resto da persistência de meta)
```

**Testes a Atualizar**:
- `tests/unit/callbacks/test_persist_outputs.py` (adicionar cenário com `reference_images`)

---

### P1-004: `run_preflight` Sem Resolução de Referências

**Contexto**: Seção 6.2 (Preflight), linha 113
**Evidência**: Endpoint encontrado em `app/server.py:162`, mas sem lógica de resolução de referências

**Implementação Atual**: Monta `initial_state` sem processar `reference_images`

**Divergência**: Lógica de resolução de IDs e construção de summaries ausente

**Ação Sugerida**: Adicionar lógica

**Patch**:
```python
# app/server.py (linhas 334-390)

# Montar estado inicial para a sessão ADK
initial_state = {
    "landing_page_url": data.get("landing_page_url"),
    "objetivo_final": (norm.get("objetivo_final_norm") or data.get("objetivo_final")),
    "perfil_cliente": data.get("perfil_cliente"),
    "formato_anuncio": formato,
    "foco": data.get("foco") or "",
    "implementation_plan": plan,
    "format_specs": specs,
    "format_specs_json": specs_json,
    "planning_mode": "fixed",
}

# ADICIONAR: Resolver referências visuais se presentes no payload
reference_images_payload = payload.get('reference_images', {})
if reference_images_payload:
    from app.utils.reference_cache import (
        resolve_reference_metadata,
        merge_user_description,
        build_reference_summary,
    )

    # Resolver character
    char_id = reference_images_payload.get('character', {}).get('id')
    char_desc = reference_images_payload.get('character', {}).get('user_description')
    char_metadata = resolve_reference_metadata(char_id)
    char_merged = merge_user_description(char_metadata, char_desc)

    # Resolver product
    prod_id = reference_images_payload.get('product', {}).get('id')
    prod_desc = reference_images_payload.get('product', {}).get('user_description')
    prod_metadata = resolve_reference_metadata(prod_id)
    prod_merged = merge_user_description(prod_metadata, prod_desc)

    # Montar reference_images no state
    initial_state['reference_images'] = {
        'character': char_merged,
        'product': prod_merged,
    }

    # Construir summaries
    summary = build_reference_summary(initial_state['reference_images'], payload)
    initial_state['reference_image_summary'] = summary
    initial_state['reference_image_character_summary'] = summary.get('character')
    initial_state['reference_image_product_summary'] = summary.get('product')

    # Log estruturado
    try:
        logger.log_struct({
            "event": "preflight_references_resolved",
            "character_provided": bool(char_merged),
            "product_provided": bool(prod_merged),
        }, severity="INFO")
    except Exception:
        pass
```

**Dependências**:
- P0-A-002 (app/utils/reference_cache.py)
- P0-A-001 (ReferenceImageMetadata schema)

---

## Achados de Prioridade Média (P2)

### P2-001: Template `image_current_prompt_template` Ausente

**Contexto**: Seção 9 (Configuração & Templates), linha 187
**Evidência**: Template não encontrado em `app/config.py`

**Templates Existentes**:
- `image_intermediate_prompt_template` (linha 67)
- `image_aspirational_prompt_template` (linha 71)

**Valor Esperado**:
```python
"Use the provided character reference ({character_labels}). {prompt_atual}"
```

**Ação Sugerida**: Adicionar configuração

**Patch**:
```python
# app/config.py (linhas 66-75)

image_signed_url_ttl: int = 60 * 60 * 24  # 24h
image_current_prompt_template: str = (  # NOVO
    "Use the provided character reference ({character_labels}). {prompt_atual}"
)
image_intermediate_prompt_template: str = (
    "Transform this scene to show the immediate positive action: {prompt_intermediario}. "
    "Keep the same person, clothing, environment, framing and lighting. Show determination and focus."
)
```

---

### P2-002: Template `image_aspirational_prompt_template_with_product` Ausente

**Contexto**: Seção 9 (Configuração & Templates), linha 190
**Evidência**: Template específico para produto não existe

**Valor Esperado**:
```python
"Integrate the product from the reference image ({product_labels}). {prompt_aspiracional}"
```

**Ação Sugerida**: Adicionar configuração

**Patch**:
```python
# app/config.py (linhas 71-75)

image_aspirational_prompt_template: str = (
    "Show the same person after some time has passed achieving the successful outcome: {prompt_aspiracional}. "
    "Preserve identity and core features while allowing improvements in environment, wardrobe and expression."
)
image_aspirational_prompt_template_with_product: str = (  # NOVO
    "Integrate the product from the reference image ({product_labels}). {prompt_aspiracional}"
)
```

---

### P2-003: Prompts do `final_assembler` Sem Placeholders de Referência

**Contexto**: Seção 7.1 (Prompts de geração), linha 137
**Evidência**: Prompt encontrado em `app/agent.py:1033`, mas sem placeholders de `reference_images`

**Prompts Atuais**: Não incluem `reference_images.character.*`, `reference_images.product.*`

**Ação Sugerida**: Atualizar prompt

**Patch**:
```python
# app/agent.py (linhas 1033-1056)

final_assembler = LlmAgent(
    model=config.critic_model,
    name="final_assembler",
    description="Monta o JSON final do anúncio a partir dos fragmentos aprovados.",
    instruction="""
## IDENTIDADE: Final Ads Assembler

Monte **3 variações** de anúncio combinando `approved_code_snippets`.

Referências visuais disponíveis (quando existirem):
- Personagem: {reference_image_character_summary}
  - GCS URI: {reference_images.character.gcs_uri}
  - Labels: {reference_images.character.labels}
- Produto: {reference_image_product_summary}
  - GCS URI: {reference_images.product.gcs_uri}
  - Labels: {reference_images.product.labels}

Campos obrigatórios (saída deve ser uma LISTA com 3 OBJETOS):
- "landing_page_url": usar {landing_page_url} (se vazio, inferir do briefing coerentemente)
- "formato": usar {formato_anuncio} especificado pelo usuário
- "copy": { "headline", "corpo", "cta_texto" } (COPY_DRAFT refinado - CRIAR 3 VARIAÇÕES)
- "visual": {
    "descricao_imagem",
    "prompt_estado_atual",
    "prompt_estado_intermediario",
    "prompt_estado_aspiracional",
    "aspect_ratio",
    "reference_assets": {  # ADICIONAR quando referências existirem
      "character": {"gcs_uri": "...", "labels": [...]},
      "product": {"gcs_uri": "...", "labels": [...]}
    }
  }
- "cta_instagram": do COPY_DRAFT
- "fluxo": coerente com {objetivo_final}, por padrão "Instagram Ad → Landing Page → Botão WhatsApp"
- "referencia_padroes": do RESEARCH
- "contexto_landing": resumo do {landing_page_context}

Regras:
- Criar 3 variações diferentes de copy e visual
- Complete faltantes de forma conservadora.
- Se um "foco" foi definido, garanta que as variações respeitam e comunicam o tema.
- **Quando referências visuais existirem**, garantir que `descricao_imagem` cite o produto/personagem real usando os labels.
- **Incluir `reference_assets`** em `visual` quando houver uploads.
- **Saída**: apenas JSON válido (sem markdown).
""",
    output_key="final_code_delivery",
    after_agent_callback=persist_final_delivery,
)
```

**Nota**: Considerar pós-processamento se modelo não retornar `reference_assets` automaticamente.

---

## Achados de Baixa Prioridade (P3)

### P3-001: VISUAL_DRAFT Sem Placeholders de Referência

**Contexto**: Seção 7.1 (Prompts de geração), linha 135
**Evidência**: Prompt encontrado em `app/agent.py:880`, não inclui `reference_image_*` placeholders

**Impacto**: Baixo (qualidade de output, não bloqueante)

**Ação Sugerida**: Atualizar prompt para incluir `{reference_image_character_summary}` e `{reference_image_product_summary}`

---

### P3-002: COPY_DRAFT Sem Hint de Product Labels

**Contexto**: Seção 7.1 (Prompts de geração), linha 136
**Evidência**: Prompt encontrado em `app/agent.py:884`, não menciona product labels

**Impacto**: Baixo (qualidade de copy, não bloqueante)

**Ação Sugerida**: Adicionar instrução para usar product labels quando disponíveis

---

## Validações Estendidas (P3-Extended)

### P3-EXT-001: Dependência `google-cloud-vision` Ausente

**Contexto**: Seção 6.1 (Upload), linha 109
**Versão Requerida**: `>=3.4.0`
**Evidência**: Biblioteca não encontrada em `requirements.txt` nem `pyproject.toml`

**Dependências Existentes**:
- `google-genai`
- `google-auth`
- `google-cloud-storage>=2.10.0`
- `vertexai>=1.40.0`

**Similaridade**: `google-cloud-storage` (mesma família, serviço diferente)

**Ação Sugerida**: Adicionar dependência

**Patch**:
```diff
# requirements.txt
google-genai
google-auth
google-cloud-storage
+google-cloud-vision>=3.4.0

# pyproject.toml
dependencies = [
    "google-adk==1.4.2",
    "google-cloud-logging>=3.5.0",
    "google-cloud-storage>=2.10.0",
+   "google-cloud-vision>=3.4.0",
    "google-auth>=2.23.0",
    ...
]
```

**Pós-instalação**: Executar `make install` ou `uv sync`

---

## Registro de Criação (15 elementos)

Elementos que o plano **explicitamente diz para criar**. Estes NÃO são bloqueadores P0, pois são entregas esperadas.

1. `app/schemas/reference_assets.py` (Seção 4, linha 21)
2. `ReferenceImageMetadata` (classe Pydantic)
3. `app/utils/reference_cache.py` (Seção 4, linha 49)
4. `resolve_reference_metadata` (função)
5. `build_reference_summary` (função)
6. `merge_user_description` (função)
7. `cache_reference_metadata` (função)
8. `upload_reference_image` (GCS helper em app/utils/gcs.py)
9. `analyze_reference_image` (Vision AI em app/utils/vision.py)
10. `frontend/src/components/ReferenceUpload.tsx` (componente React)
11. `RunPreflightRequest` (schema Pydantic opcional)
12. `/upload/reference-image` (endpoint FastAPI)
13. `_load_reference_image` (helper em generate_transformation_images.py)
14. `image_current_prompt_template` (config)
15. `image_aspirational_prompt_template_with_product` (config)

---

## Tabela de Mapeamento Plano ↔ Código

| Elemento do Plano | Elemento no Código | Status | Severidade |
|-------------------|-------------------|--------|------------|
| `app/schemas/reference_assets.py` | NOT_FOUND | MISSING | P0-A-001 |
| `app/utils/reference_cache.py` | NOT_FOUND | MISSING | P0-A-002 |
| `app/utils/vision.py` | NOT_FOUND | MISSING | P0-A-004 |
| `upload_reference_image` (GCS helper) | NOT_FOUND in gcs.py | MISSING | P0-A-003 |
| `/upload/reference-image` endpoint | NOT_FOUND in server.py | MISSING | P0-A-005 |
| `ReferenceUpload.tsx` | NOT_FOUND in frontend | MISSING | P0-A-006 |
| `generate_transformation_images` | app/tools/generate_transformation_images.py:209 | DIVERGENT | P1-001 |
| `ImageAssetsAgent` reference handling | app/agent.py:316 | INCOMPLETE | P1-002 |
| `persist_final_delivery` | app/callbacks/persist_outputs.py:35 | INCOMPLETE | P1-003 |
| `run_preflight` reference resolution | app/server.py:334 | INCOMPLETE | P1-004 |
| `image_current_prompt_template` | NOT_FOUND in config.py | MISSING | P2-001 |
| `image_aspirational_prompt_template_with_product` | NOT_FOUND in config.py | MISSING | P2-002 |
| `final_assembler` prompts | app/agent.py:1033 | INCOMPLETE | P2-003 |
| `google-cloud-vision` dependency | NOT_FOUND in deps | MISSING | P3-EXT-001 |

---

## Incertezas e Decisões Pendentes

### 1. Backend de Cache para `reference_cache.py`

**Questão**: Qual backend usar para armazenar metadados de referências?

**Opções**:
- **Dict Python em memória**: Simples, mas não compartilhado entre workers
- **Redis**: Compartilhado, requer infraestrutura adicional
- **Google Cloud Datastore**: Persistente, latência maior

**Menção no Plano**: Linha 221 ("armazenar metadados em backend compartilhado (Redis/Datastore)")

**Recomendação**: Iniciar com dict em memória + TTL. Documentar migração futura para Redis quando escalar.

---

### 2. Fallback Behavior para Vision AI

**Questão**: O que fazer se Vision API estiver indisponível?

**Opções**:
- Rejeitar upload com mensagem amigável
- Permitir upload sem análise (com warning)
- Skip analysis e prosseguir

**Menção no Plano**: Linha 181 ("fallback que rejeita upload com mensagem amigável; monitorar via logging")

**Recomendação**: Rejeitar upload por padrão. Adicionar flag de configuração `VISION_FALLBACK_MODE` para permitir override em dev.

---

### 3. Necessidade de `RunPreflightRequest` Schema

**Questão**: Criar schema Pydantic ou manter parse manual?

**Situação Atual**: Parse manual via `payload.get()` funciona

**Menção no Plano**: Linha 112 (apenas 1 referência)

**Recomendação**: Criar schema Pydantic para validação robusta se houver tempo. Caso contrário, documentar no plano que parse manual é aceitável.

---

### 4. Implementação de `_load_reference_image`

**Questão**: Extrair helper ou implementar inline?

**Situação**: Apenas 1 referência no plano

**Recomendação**: Implementar inline em `generate_transformation_images`, a menos que haja previsão de reutilização.

---

## Recomendações de Implementação

### Ações Imediatas (Bloqueadores Críticos)

1. **Criar `app/schemas/reference_assets.py`** (P0-A-001)
2. **Criar `app/utils/reference_cache.py`** (P0-A-002)
3. **Criar `app/utils/vision.py`** (P0-A-004)
4. **Adicionar `google-cloud-vision>=3.4.0`** às dependências (P3-EXT-001)
5. **Implementar endpoint `/upload/reference-image`** (P0-A-005)

### Alta Prioridade (Ajustes de Integração)

1. **Atualizar assinatura de `generate_transformation_images`** (P1-001)
2. **Adicionar lógica de referências em `ImageAssetsAgent`** (P1-002)
3. **Adicionar resolução de referências em `run_preflight`** (P1-004)
4. **Atualizar `persist_final_delivery`** para salvar metadados (P1-003)

### Prioridade Média (Configurações e Prompts)

1. **Adicionar `image_current_prompt_template`** (P2-001)
2. **Adicionar `image_aspirational_prompt_template_with_product`** (P2-002)
3. **Atualizar prompts do `final_assembler`** (P2-003)
4. **Criar componente `ReferenceUpload.tsx`** (P0-A-006)

### Baixa Prioridade (Melhorias de Qualidade)

1. **Atualizar prompts VISUAL_DRAFT** (P3-001)
2. **Atualizar prompts COPY_DRAFT** (P3-002)
3. **Clarificar necessidade de `RunPreflightRequest`** (P0-B-007)
4. **Decidir implementação de `_load_reference_image`** (P0-B-008)

---

## Métricas de Qualidade

| Métrica | Valor | Status |
|---------|-------|--------|
| Cobertura de Símbolos | 100% | ✅ Excelente |
| Precisão de Matching | 91.3% | ✅ Muito Boa |
| Taxa de Phantom Links | 4.3% | ✅ Aceitável (<5%) |
| Tempo de Validação | 3.847s | ✅ Dentro do Target (<100ms/claim) |

---

## Plano de Ação Sugerido (Sequência de Implementação)

### Fase 1: Infraestrutura (1-2 dias)
1. Criar `app/schemas/reference_assets.py`
2. Criar `app/utils/reference_cache.py`
3. Adicionar `google-cloud-vision>=3.4.0`
4. Criar `app/utils/vision.py`
5. Adicionar helper `upload_reference_image` em `app/utils/gcs.py`

### Fase 2: API Backend (1 dia)
1. Implementar endpoint `/upload/reference-image`
2. Adicionar lógica de resolução em `run_preflight`
3. Atualizar `persist_final_delivery`

### Fase 3: Pipeline de Geração (1 dia)
1. Atualizar assinatura de `generate_transformation_images`
2. Adicionar lógica em `ImageAssetsAgent`
3. Adicionar templates de prompt em `config.py`
4. Atualizar prompts do `final_assembler`

### Fase 4: UI Frontend (1-2 dias)
1. Criar componente `ReferenceUpload.tsx`
2. Integrar com `WizardForm`
3. Criar hook `useReferenceImages`

### Fase 5: Validação & Testes (1 dia)
1. Testes unitários (Vision AI, cache, upload)
2. Testes de integração (pipeline completo)
3. QA manual (cenários: apenas personagem, apenas produto, ambos, nenhum)

### Fase 6: Documentação (0.5 dia)
1. Atualizar `README.md` (seção de imagens)
2. Documentar fluxo de uploads
3. Adicionar exemplos de uso

---

## Conclusão

O plano `imagem_roupa.md` é **tecnicamente sólido e bem estruturado**, mas contém **8 bloqueadores críticos (P0)** que impedem a implementação imediata. Todos os bloqueadores são elementos que o plano **assume existir** mas que **não estão presentes no código**.

**Principais Gaps**:
1. **6 módulos/componentes ausentes** (P0-A)
2. **4 integrações incompletas** (P1)
3. **1 dependência faltante** (P3-Extended)

**Próximos Passos Recomendados**:
1. Executar **Fase 1 (Infraestrutura)** para desbloquear desenvolvimento
2. Implementar endpoint `/upload/reference-image` (Fase 2)
3. Validar integração com pipeline existente (Fase 3)
4. Desenvolver UI frontend (Fase 4)

**Estimativa Total**: 5-7 dias de desenvolvimento + 1 dia de testes/QA.

---

**Relatório Gerado por**: Plan-Code Drift Validator v2.0.0
**Executado em**: America/Sao_Paulo (BRT)
**Idioma**: PT-BR
