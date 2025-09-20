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
from google.genai import types
from google.cloud import storage
from PIL import Image

from app.config import config

logger = logging.getLogger(__name__)

_MODEL_NAME = "gemini-2.5-flash-image-preview"
_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
_client = genai.Client(
    vertexai=True,
    project=_PROJECT_ID,
    location=_LOCATION,
)
_storage_client = storage.Client()

SYSTEM_INSTRUCTIONS = (
    "Você gera imagens que contam uma transformação em três etapas.\n"
    "Regras principais:\n"
    "- Sempre mantenha a mesma pessoa (rosto, idade, gênero, etnia).\n"
    "- Preserve o ambiente, a iluminação e as roupas, a menos que o prompt peça o contrário.\n"
    "- Ajuste apenas expressões, postura e energia conforme o estágio descrito.\n"
    "- Estágio atual: represente o problema ou dor.\n"
    "- Estágio intermediário: mostre a ação de mudança acontecendo, ~40% de progresso.\n"
    "- Estágio aspiracional: mostre o resultado desejado com naturalidade e credibilidade.\n"
    "Mantenha estilo fotorrealista e consistência visual entre as imagens."
)


def _get_generation_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        temperature=0.9,
        top_p=0.95,
        max_output_tokens=32768,
        system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTIONS)],
    )

ProgressCallback = Callable[[int, str], Awaitable[None] | None]


@dataclass
class _UploadResult:
    gcs_uri: str
    signed_url: str


def _sanitize_segment(value: str, fallback: str) -> str:
    value = (value or fallback or "").strip()
    if not value:
        return fallback
    return value.replace(" ", "-").replace("..", "_")


def _resolve_bucket() -> tuple[str, str]:
    bucket_uri = os.getenv("DELIVERIES_BUCKET", "").strip()
    if not bucket_uri:
        raise RuntimeError("DELIVERIES_BUCKET não configurado para upload das imagens.")
    if bucket_uri.startswith("gs://"):
        bucket_name = bucket_uri[5:].split("/", 1)[0]
    else:
        bucket_name = bucket_uri
        bucket_uri = f"gs://{bucket_name}"
    if not bucket_name:
        raise RuntimeError("DELIVERIES_BUCKET inválido; informe um bucket GCS.")
    return bucket_name, bucket_uri


def _extract_image(response: Any) -> Image.Image:
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


async def _call_model(contents: list[Any]) -> Image.Image:
    parts: list[types.Part] = []
    for item in contents:
        if isinstance(item, str):
            parts.append(types.Part.from_text(text=item))
        elif isinstance(item, Image.Image):
            buffer = BytesIO()
            item.save(buffer, format="PNG")
            parts.append(
                types.Part.from_bytes(
                    data=buffer.getvalue(),
                    mime_type="image/png",
                )
            )
            buffer.close()
        else:
            parts.append(item)

    formatted_contents = [
        types.Content(
            role="user",
            parts=parts,
        )
    ]

    generation_config = _get_generation_config()

    delay_seconds = 1.5
    last_exc: Optional[Exception] = None
    for attempt in range(1, config.image_generation_max_retries + 1):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    _client.models.generate_content,
                    model=_MODEL_NAME,
                    contents=formatted_contents,
                    config=generation_config,
                ),
                timeout=config.image_generation_timeout,
            )
            return _extract_image(response)
        except Exception as exc:  # pragma: no cover - network.errors
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


async def _notify(callback: Optional[ProgressCallback], stage_idx: int, stage_label: str) -> None:
    if not callback:
        return
    result = callback(stage_idx, stage_label)
    if inspect.isawaitable(result):
        await result


async def _upload_image(
    image: Image.Image,
    *,
    user_id: str,
    session_id: str,
    variation_idx: int,
    stage_label: str,
    prefix_override: Optional[str] = None,
) -> _UploadResult:
    bucket_name, bucket_uri = _resolve_bucket()
    bucket = _storage_client.bucket(bucket_name)

    safe_user = _sanitize_segment(user_id, "anonymous")
    safe_session = _sanitize_segment(session_id, "nosession")
    base_prefix = prefix_override or f"deliveries/{safe_user}/{safe_session}/images"
    filename = f"{stage_label}_{variation_idx}.png"
    blob_path = f"{base_prefix}/{filename}"

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    data = buffer.getvalue()
    buffer.close()

    blob = bucket.blob(blob_path)
    await asyncio.to_thread(blob.upload_from_string, data, content_type="image/png")

    signed_url = ""
    try:
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=config.image_signed_url_ttl),
            method="GET",
            response_type="image/png",
        )
    except Exception as exc:  # pragma: no cover - depends on GCP setup
        logger.warning("Falha ao gerar Signed URL para %s: %s", blob_path, exc, exc_info=True)

    return _UploadResult(
        gcs_uri=f"gs://{bucket_name}/{blob_path}",
        signed_url=signed_url,
    )


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

    # Etapa 1 – estado atual
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

    # Etapa 2 – intermediário (usa imagem base)
    transform_prompt_inter = config.image_intermediate_prompt_template.format(
        prompt_intermediario=prompt_intermediario
    )
    image_intermediario = await _call_model([image_atual, transform_prompt_inter])
    upload_intermediario = await _upload_image(
        image_intermediario,
        user_id=user_id,
        session_id=session_id,
        variation_idx=variation_idx,
        stage_label="estado_intermediario",
        prefix_override=prefix,
    )
    await _notify(progress_callback, 2, "estado_intermediario")

    # Etapa 3 – aspiracional (usa imagem intermediária)
    transform_prompt_asp = config.image_aspirational_prompt_template.format(
        prompt_aspiracional=prompt_aspiracional
    )
    image_aspiracional = await _call_model([image_intermediario, transform_prompt_asp])
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
