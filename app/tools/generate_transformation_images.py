"""Utilities for generating sequential transformation images via Gemini Image Preview."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from typing import Any, Awaitable, Callable, Dict, Optional

import requests

from google import genai
from google.genai import types
from google.cloud import storage
from PIL import Image

from app.config import config
from app.schemas.reference_assets import ReferenceImageMetadata

logger = logging.getLogger(__name__)

_MODEL_NAME = "gemini-2.5-flash-image"
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
        response_modalities=["IMAGE"],  # somete imagem, evita respostas em texto
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


def _load_reference_image(metadata: ReferenceImageMetadata) -> Image.Image:
    """Load a reference image either from a signed URL or directly from GCS."""

    if not metadata.gcs_uri:
        raise ValueError("Reference metadata must include a GCS URI")

    # Prefer signed URL when available to avoid requiring elevated permissions.
    if metadata.signed_url:
        try:
            response = requests.get(metadata.signed_url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - depends on network
            raise RuntimeError(
                f"Failed to download reference image {metadata.id} via signed URL"
            ) from exc
        with BytesIO(response.content) as buffer:
            image = Image.open(buffer)
            return image.convert("RGB")

    # Fallback to direct GCS access.
    if not metadata.gcs_uri.startswith("gs://"):
        raise RuntimeError(
            f"Unsupported GCS URI for reference image {metadata.id}: {metadata.gcs_uri}"
        )

    bucket_path = metadata.gcs_uri[5:]
    bucket_name, _, blob_name = bucket_path.partition("/")
    if not bucket_name or not blob_name:
        raise RuntimeError(
            f"Invalid GCS URI for reference image {metadata.id}: {metadata.gcs_uri}"
        )

    blob = _storage_client.bucket(bucket_name).blob(blob_name)
    data = blob.download_as_bytes()  # pragma: no cover - depends on GCS
    with BytesIO(data) as buffer:
        image = Image.open(buffer)
        return image.convert("RGB")


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


def _summarize_stage_inputs(parts: list[Any]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for item in parts:
        if isinstance(item, str):
            preview = item if len(item) <= 120 else f"{item[:117]}..."
            summary.append(
                {
                    "type": "text",
                    "length": len(item),
                    "preview": preview,
                }
            )
            continue
        if isinstance(item, Image.Image):
            summary.append(
                {
                    "type": "image",
                    "mode": getattr(item, "mode", "unknown"),
                    "size": getattr(item, "size", None),
                }
            )
            continue
        summary.append({"type": type(item).__name__})
    return summary


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
    reference_character: Optional[ReferenceImageMetadata] = None,
    reference_product: Optional[ReferenceImageMetadata] = None,
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

    character_image: Image.Image | None = None
    product_image: Image.Image | None = None
    character_load_error: str | None = None
    product_load_error: str | None = None

    if reference_character is not None:
        try:
            character_image = await asyncio.to_thread(
                _load_reference_image, reference_character
            )
        except Exception as exc:  # pragma: no cover - network/GCS failures
            character_load_error = str(exc)
            logger.warning(
                "Failed to load character reference %s: %s",
                reference_character.id,
                exc,
                exc_info=True,
            )

    if reference_product is not None:
        try:
            product_image = await asyncio.to_thread(
                _load_reference_image, reference_product
            )
        except Exception as exc:  # pragma: no cover - network/GCS failures
            product_load_error = str(exc)
            logger.warning(
                "Failed to load product reference %s: %s",
                reference_product.id,
                exc,
                exc_info=True,
            )

    character_labels = ""
    character_summary = metadata.get("character_summary") if metadata else None
    if reference_character is not None:
        character_labels = ", ".join(reference_character.labels) or (
            reference_character.user_description or reference_character.id
        )
        if not character_summary:
            character_summary = reference_character.user_description or character_labels

    product_labels = ""
    product_summary = metadata.get("product_summary") if metadata else None
    if reference_product is not None:
        product_labels = ", ".join(reference_product.labels) or (
            reference_product.user_description or reference_product.id
        )
        if not product_summary:
            product_summary = reference_product.user_description or product_labels

    # Etapa 1 – estado atual
    prompt_estado_atual_parts: list[str] = [
        "Gerar a IMAGEM DO ESTADO ATUAL do personagem. Não altere rosto, traços, proporções corporais, tom de pele ou cabelo."
    ]
    if character_image is not None:
        prompt_estado_atual_parts.append(
            "Use a imagem compartilhada do personagem como referência principal e mantenha integralmente as características físicas."
        )
    if product_image is not None:
        extra_product_context = product_summary or product_labels
        product_instruction = "Use a imagem compartilhada do produto/serviço como referência visual na cena."
        if extra_product_context:
            product_instruction = (
                f"Use a imagem compartilhada do produto/serviço como referência visual e destaque {extra_product_context}."
            )
        prompt_estado_atual_parts.append(product_instruction)
    prompt_estado_atual_parts.append(prompt_atual)
    prompt_estado_atual = " ".join(prompt_estado_atual_parts)

    stage_one_inputs: list[Any] = []
    if character_image is not None:
        stage_one_inputs.append(character_image)
    if product_image is not None:
        stage_one_inputs.append(product_image)
    stage_one_inputs.append(prompt_estado_atual)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "generate_content inputs for variation %s - estado_atual: %s",
            variation_idx,
            json.dumps(_summarize_stage_inputs(stage_one_inputs)),
        )

    image_atual = await _call_model(stage_one_inputs)
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
    transform_prompt_inter_parts: list[str] = [
        "Gerar a IMAGEM DO ESTADO INTERMEDIÁRIO: o personagem está buscando soluções na internet sobre o produto/serviço do anunciante.",
        "Enquadramento over-the-shoulder (por trás e levemente de lado), câmera atrás e lateral do personagem.",
        "A TELA do dispositivo deve estar de frente para a câmera e ser o foco principal, mostrando Instagram, site ou resultados de busca do anunciante.",
        "Iluminação realista, foco na tela e sem reflexos que impeçam a leitura."
    ]
    if image_atual is not None:
        transform_prompt_inter_parts.append(
            "Use como referência a IMAGEM COMPARTILHADA do estado atual para manter o mesmo personagem, características físicas e expressões."
        )
    if character_image is not None:
        transform_prompt_inter_parts.append(
            "Considere também a imagem compartilhada do personagem para reforçar consistência de rosto e proporções."
        )
    if product_image is not None:
        transform_prompt_inter_parts.append(
            "Utilize a imagem compartilhada do produto/serviço apenas se for exibida no contexto da pesquisa."
        )
    transform_prompt_inter_parts.append(
        "Mantenha o cenário da imagem anterior quando fizer sentido; caso contrário, ajuste para um ambiente plausível de pesquisa online (quarto, sala ou escritório)."
    )
    transform_prompt_inter_parts.append(prompt_intermediario)
    transform_prompt_inter = " ".join(transform_prompt_inter_parts)
    stage_two_inputs: list[Any] = [image_atual]
    if character_image is not None:
        stage_two_inputs.append(character_image)
    if product_image is not None:
        stage_two_inputs.append(product_image)
    stage_two_inputs.append(transform_prompt_inter)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "generate_content inputs for variation %s - estado_intermediario: %s",
            variation_idx,
            json.dumps(_summarize_stage_inputs(stage_two_inputs)),
        )

    image_intermediario = await _call_model(stage_two_inputs)
    upload_intermediario = await _upload_image(
        image_intermediario,
        user_id=user_id,
        session_id=session_id,
        variation_idx=variation_idx,
        stage_label="estado_intermediario",
        prefix_override=prefix,
    )
    await _notify(progress_callback, 2, "estado_intermediario")

    # Etapa 3 – aspiracional (usa apenas uploads aprovados)
    transform_prompt_asp_parts: list[str] = [
        "Gerar a IMAGEM DO ESTADO ASPIRACIONAL (futuro desejado/sucesso), conforme o prompt aspiracional fornecido.",
        "Não altere o rosto, traços, proporções corporais, tom de pele ou cabelo do personagem."
    ]
    if character_image is not None:
        transform_prompt_asp_parts.append(
            "Use SOMENTE a IMAGEM ORIGINAL DO PERSONAGEM (upload inicial) como referência de pessoa, mantendo integralmente as características físicas."
        )
    if product_image is not None:
        transform_prompt_asp_parts.append(
            "Incorpore visualmente a IMAGEM DO PRODUTO/SERVIÇO compartilhada na cena aspiracional."
        )
    transform_prompt_asp_parts.append(
        "Não utilize imagens geradas anteriormente como referência principal nesta etapa."
    )
    transform_prompt_asp_parts.append(prompt_aspiracional)
    transform_prompt_asp = " ".join(transform_prompt_asp_parts)

    stage_three_inputs: list[Any] = []
    if product_image is not None:
        stage_three_inputs.append(product_image)
    if character_image is not None:
        stage_three_inputs.append(character_image)
    stage_three_inputs.append(transform_prompt_asp)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "generate_content inputs for variation %s - estado_aspiracional: %s",
            variation_idx,
            json.dumps(_summarize_stage_inputs(stage_three_inputs)),
        )

    image_aspiracional = await _call_model(stage_three_inputs)
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

    meta: Dict[str, Any] = {
        "variation_idx": variation_idx,
        "duration_seconds": elapsed,
    }

    if reference_character is not None:
        meta.update(
            {
                "reference_character_id": reference_character.id,
                "reference_character_used": character_image is not None,
            }
        )
        if character_load_error:
            meta["reference_character_error"] = character_load_error

    if reference_product is not None:
        meta.update(
            {
                "reference_product_id": reference_product.id,
                "reference_product_used": product_image is not None,
            }
        )
        if product_load_error:
            meta["reference_product_error"] = product_load_error

    return {
        "estado_atual": upload_atual.__dict__,
        "estado_intermediario": upload_intermediario.__dict__,
        "estado_aspiracional": upload_aspiracional.__dict__,
        "meta": meta,
    }


__all__ = ["generate_transformation_images", "_load_reference_image"]
