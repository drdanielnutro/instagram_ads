## Análise de Inconsistências no Código

Identifiquei **várias inconsistências críticas** no código real comparado com a documentação e melhores práticas do Gemini/Nano Banana:

## 🔴 Problemas Críticos

### 1. **Cliente não configurado para Vertex AI**
```python
# ATUAL (incorreto)
_client = genai.Client()

# DEVERIA SER
_client = genai.Client(
    vertexai=True,
    api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
)
```

### 2. **Falta configuração essencial de geração**
```python
# ATUAL - sem configuração
response = await asyncio.to_thread(
    _client.models.generate_content,
    model=_MODEL_NAME,
    contents=contents,  # ❌ Sem config
)

# DEVERIA TER
from google.genai import types

generate_config = types.GenerateContentConfig(
    temperature=0.9,
    top_p=0.95,
    max_output_tokens=32768,
    response_modalities=["TEXT", "IMAGE"],  # CRÍTICO!
    system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTIONS)],
)

response = await asyncio.to_thread(
    _client.models.generate_content,
    model=_MODEL_NAME,
    contents=contents,
    config=generate_config,  # ✅ Com config
)
```

### 3. **Contents mal formatados**
```python
# ATUAL - passando objetos incorretos
image_intermediario = await _call_model([transform_prompt_inter, image_atual])
# image_atual é PIL.Image, não types.Part!

# DEVERIA SER
contents = [
    types.Content(
        role="user",
        parts=[
            types.Part.from_image(image_atual),  # Conversão correta
            types.Part.from_text(text=transform_prompt_inter)
        ]
    )
]
```

### 4. **Ausência de System Instructions**
O código não define instruções de sistema para manter consistência entre as transformações.

## 📝 Código Corrigido

```python
"""Utilities for generating sequential transformation images via Gemini Image Preview."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import time
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from typing import Any, Awaitable, Callable, Dict, Optional

from google import genai
from google.genai import types  # ✅ Adicionar import
from google.cloud import storage
from PIL import Image

from app.config import config

logger = logging.getLogger(__name__)

_MODEL_NAME = "gemini-2.5-flash-image-preview"

# ✅ Cliente configurado corretamente
_client = genai.Client(
    vertexai=True,
    api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
)

_storage_client = storage.Client()

# ✅ System Instructions para consistência
SYSTEM_INSTRUCTIONS = """## PAPEL
Você é um especialista em transformações visuais progressivas para campanhas motivacionais.

## REGRAS DE TRANSFORMAÇÃO

### Consistência Obrigatória:
- MANTER identidade da pessoa (rosto, etnia, gênero, idade)
- MANTER ambiente/cenário base (exceto se explicitamente alterado)
- MANTER estilo visual e iluminação

### Progressão Visual:
- Estado Atual: Representação realista da situação presente
- Estado Intermediário: Evolução visível mas parcial (30-50% da transformação)
- Estado Aspiracional: Transformação completa e inspiradora

### Diretrizes Técnicas:
- Fotorrealismo de alta qualidade
- Composição consistente entre frames
- Iluminação e cores coerentes
- Foco em mudanças comportamentais/emocionais visíveis"""

# ✅ Configuração de geração
def _get_generation_config() -> types.GenerateContentConfig:
    """Retorna configuração otimizada para geração de imagens."""
    return types.GenerateContentConfig(
        temperature=0.9,  # Balanceado para consistência
        top_p=0.95,
        max_output_tokens=32768,
        response_modalities=["TEXT", "IMAGE"],  # CRÍTICO para gerar imagens
        system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTIONS)],
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="OFF"
            )
        ],
    )

ProgressCallback = Callable[[int, str], Awaitable[None] | None]

@dataclass
class _UploadResult:
    gcs_uri: str
    signed_url: str

# [Funções auxiliares mantidas como estão]
def _sanitize_segment(value: str, fallback: str) -> str:
    # ... código existente ...
    
def _resolve_bucket() -> tuple[str, str]:
    # ... código existente ...

def _extract_image(response: Any) -> Image.Image:
    """Extrai imagem da resposta do modelo."""
    candidates = getattr(response, "candidates", []) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data and getattr(inline_data, "data", None):
                with BytesIO(inline_data.data) as handle:
                    image = Image.open(handle)
                    return image.convert("RGB")
    raise RuntimeError("Resposta do modelo não contém dados de imagem.")

# ✅ Função _call_model corrigida
async def _call_model(contents: list[Any], base_image: Optional[Image.Image] = None) -> Image.Image:
    """
    Chama o modelo com configuração correta.
    
    Args:
        contents: Prompt(s) de texto
        base_image: Imagem base opcional para transformação
    """
    # Formatar contents corretamente
    if base_image:
        # Para transformação com imagem base
        if isinstance(contents[0], str):
            formatted_contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_image(base_image),
                        types.Part.from_text(text=contents[0])
                    ]
                )
            ]
        else:
            formatted_contents = contents
    else:
        # Para geração inicial (só texto)
        if isinstance(contents[0], str):
            formatted_contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=contents[0])]
                )
            ]
        else:
            formatted_contents = contents
    
    config = _get_generation_config()
    
    delay_seconds = 1.5
    last_exc: Optional[Exception] = None
    
    for attempt in range(1, config.image_generation_max_retries + 1):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    _client.models.generate_content,
                    model=_MODEL_NAME,
                    contents=formatted_contents,
                    config=config,  # ✅ Passar config
                ),
                timeout=config.image_generation_timeout,
            )
            return _extract_image(response)
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Falha ao gerar imagem (tentativa %s/%s): %s",
                attempt,
                config.image_generation_max_retries,
                exc,
            )
            if attempt < config.image_generation_max_retries:
                await asyncio.sleep(min(delay_seconds, 10))
                delay_seconds *= 1.5
    
    raise RuntimeError(
        f"Falha na geração de imagem após {config.image_generation_max_retries} tentativas: {last_exc}"
    )

# [Outras funções mantidas]
async def _notify(callback: Optional[ProgressCallback], stage_idx: int, stage_label: str) -> None:
    # ... código existente ...

async def _upload_image(...) -> _UploadResult:
    # ... código existente ...

# ✅ Função principal atualizada
async def generate_transformation_images(
    *,
    prompt_atual: str,
    prompt_intermediario: str,
    prompt_aspiracional: str,
    variation_idx: int,
    metadata: Dict[str, Any],
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, Dict[str, str]]:
    """Generate and upload the three transformation images for a single variation."""

    if not prompt_atual:
        raise ValueError("prompt_atual não pode ser vazio.")
    if not prompt_intermediario:
        raise ValueError("prompt_intermediario não pode ser vazio.")
    if not prompt_aspiracional:
        raise ValueError("prompt_aspiracional não pode ser vazio.")

    user_id = str(metadata.get("user_id") or "anonymous")
    session_id = str(metadata.get("session_id") or "nosession")
    prefix = metadata.get("gcs_prefix")

    started_at = time.perf_counter()

    # Etapa 1 – estado atual (sem imagem base)
    image_atual = await _call_model([prompt_atual])
    upload_atual = await _upload_image(
        image_atual,
        user_id=user_id,
        session_id=session_id,
        variation_idx=variation_idx,
        stage_label="estado_atual",
        prefix_override=prefix,
    )
    await _notify(progress_callback, 1, "estado_atual")

    # Etapa 2 – intermediário (COM imagem base)
    transform_prompt_inter = config.image_intermediate_prompt_template.format(
        prompt_intermediario=prompt_intermediario
    )
    # ✅ Passar imagem base corretamente
    image_intermediario = await _call_model(
        [transform_prompt_inter], 
        base_image=image_atual
    )
    upload_intermediario = await _upload_image(
        image_intermediario,
        user_id=user_id,
        session_id=session_id,
        variation_idx=variation_idx,
        stage_label="estado_intermediario",
        prefix_override=prefix,
    )
    await _notify(progress_callback, 2, "estado_intermediario")

    # Etapa 3 – aspiracional (COM imagem intermediária)
    transform_prompt_asp = config.image_aspirational_prompt_template.format(
        prompt_aspiracional=prompt_aspiracional
    )
    # ✅ Passar imagem base corretamente
    image_aspiracional = await _call_model(
        [transform_prompt_asp], 
        base_image=image_intermediario
    )
    upload_aspiracional = await _upload_image(
        image_aspiracional,
        user_id=user_id,
        session_id=session_id,
        variation_idx=variation_idx,
        stage_label="estado_aspiracional",
        prefix_override=prefix,
    )
    await _notify(progress_callback, 3, "estado_aspiracional")

    elapsed = time.perf_counter() - started_at
    logger.info(
        "Geração de imagens concluída para variação %s em %.2fs",
        variation_idx,
        elapsed,
    )

    return {
        "estado_atual": upload_atual.__dict__,
        "estado_intermediario": upload_intermediario.__dict__,
        "estado_aspiracional": upload_aspiracional.__dict__,
        "meta": {
            "variation_idx": variation_idx,
            "duration_seconds": elapsed,
        },
    }

__all__ = ["generate_transformation_images"]
```

## 📊 Resumo das Correções

| Problema                  | Impacto                        | Correção                                |
| ------------------------- | ------------------------------ | --------------------------------------- |
| Cliente sem Vertex AI     | Não usa infraestrutura correta | Adicionar `vertexai=True`               |
| Sem `response_modalities` | **NÃO GERA IMAGENS**           | Adicionar config completa               |
| Contents mal formatados   | Erro de execução               | Usar `types.Content` e `types.Part`     |
| Sem system instructions   | Inconsistência visual          | Adicionar instruções de consistência    |
| PIL.Image passado direto  | Tipo incorreto                 | Converter com `types.Part.from_image()` |

## ⚠️ Ação Necessária

**O código atual provavelmente não está gerando imagens** devido à falta de `response_modalities=["TEXT", "IMAGE"]`. Esta é a configuração mais crítica!