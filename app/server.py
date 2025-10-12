# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
from typing import Any, Literal, Mapping, Optional

# Note: Environment variables are already loaded in app/__init__.py
# This ensures .env is loaded before any imports happen

import google.auth
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile, status
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export

from app.schemas.run_preflight import RunPreflightRequest
from app.plan_models.fixed_plans import get_plan_by_format
from app.format_specifications import get_specs_by_format, get_specs_json_by_format
from app.config import config, CTA_INSTAGRAM_CHOICES, CTA_BY_OBJECTIVE
from app.utils.gcs import upload_reference_image as upload_reference_image_to_gcs
from app.utils.reference_cache import (
    build_reference_summary,
    cache_reference_metadata,
    merge_user_description,
    resolve_reference_metadata,
)
from app.utils.tracing import CloudTraceLoggingSpanExporter
from app.utils.typing import Feedback
from app.utils.vision import (
    ReferenceImageAnalysisError,
    ReferenceImageUnsafeError,
)

try:
    from helpers.user_extract_data import extract_user_input
except Exception:
    # Import opcional para permitir rodar mesmo sem helper durante desenvolvimento
    extract_user_input = None  # type: ignore

_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
py_logger = logging.getLogger("preflight")
logging.basicConfig(level=logging.INFO)

MAX_REFERENCE_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_REFERENCE_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Artifacts bucket configuration (parametrized via env vars)
artifacts_bucket = os.getenv(
    "ARTIFACTS_BUCKET", f"gs://{project_id}-facilitador-logs-data"
)

# Production note: avoid creating buckets at startup.
# If you really need auto-create in dev, set ENABLE_AUTO_BUCKET_CREATE=true
if os.getenv("ENABLE_AUTO_BUCKET_CREATE", "false").lower() == "true":
    from app.utils.gcs import create_bucket_if_not_exists
    bucket_location = os.getenv(
        "ARTIFACTS_BUCKET_LOCATION",
        os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    try:
        create_bucket_if_not_exists(
            bucket_name=artifacts_bucket, project=project_id, location=bucket_location
        )
    except Exception as e:
        logging.getLogger(__name__).warning(
            "Auto bucket creation failed or is not permitted: %s", e
        )

provider = TracerProvider()
processor = export.BatchSpanProcessor(CloudTraceLoggingSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In-memory session configuration - no persistent storage
session_service_uri = None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifacts_bucket,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
)
app.title = "facilitador"
app.description = "API for interacting with the Agent facilitador"

# Include custom delivery router (final JSON download)
try:
    from app.routers.delivery import router as delivery_router
    app.include_router(delivery_router)
except Exception as e:  # pragma: no cover
    logging.getLogger(__name__).warning("Delivery router not loaded: %s", e)


@app.on_event("startup")
async def log_feature_flags():
    """Log feature flags on startup for visibility and debugging."""
    from app.config import config

    print("=" * 80)
    print("🚀 SERVER STARTUP COMPLETE - KEY FEATURE FLAGS:")
    print("=" * 80)
    print(f"  enable_storybrand_fallback: {config.enable_storybrand_fallback}")
    print(f"  enable_new_input_fields: {config.enable_new_input_fields}")
    print(f"  storybrand_gate_debug: {config.storybrand_gate_debug}")
    print(f"  enable_image_generation: {config.enable_image_generation}")
    print("=" * 80)

    py_logger.info(
        "Feature flags loaded on startup",
        extra={
            "enable_storybrand_fallback": config.enable_storybrand_fallback,
            "enable_new_input_fields": config.enable_new_input_fields,
            "storybrand_gate_debug": config.storybrand_gate_debug,
            "enable_image_generation": config.enable_image_generation,
            "preflight_shadow_mode": config.preflight_shadow_mode,
            "vertex_concurrency_limit": os.getenv("VERTEX_CONCURRENCY_LIMIT"),
            "storybrand_soft_char_limit": os.getenv("STORYBRAND_SOFT_CHAR_LIMIT"),
            "storybrand_hard_char_limit": os.getenv("STORYBRAND_HARD_CHAR_LIMIT"),
        }
    )


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized in {"true", "1", "yes", "sim", "on"}:
            return True
        if normalized in {"false", "0", "no", "nao", "não", "off"}:
            return False
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


@app.post("/upload/reference-image")
async def upload_reference_image_endpoint(
    file: UploadFile = File(...),
    type: Literal["character", "product"] = Form(...),
    user_id: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
) -> dict[str, Any]:
    """Upload a reference image, analyse it and cache its metadata."""

    if not config.enable_reference_images:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reference image uploads are disabled.",
        )

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_REFERENCE_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Use PNG, JPEG or WebP images.",
        )

    file_bytes = await file.read()
    await file.close()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > MAX_REFERENCE_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Reference image must be 5MB or smaller.",
        )

    try:
        logger.log_struct(
            {
                "event": "reference_image_upload_start",
                "filename": file.filename,
                "content_type": content_type,
                "reference_type": type,
                "size_bytes": len(file_bytes),
                "user_id": user_id,
                "session_id": session_id,
            },
            severity="INFO",
        )
    except Exception:
        pass

    try:
        metadata = await upload_reference_image_to_gcs(
            file_bytes=file_bytes,
            filename=file.filename or "reference-image",
            content_type=content_type,
            reference_type=type,
            user_id=user_id,
            session_id=session_id,
        )
    except ReferenceImageUnsafeError as exc:
        try:
            logger.log_struct(
                {
                    "event": "reference_image_upload_rejected",
                    "reason": "safe_search_blocked",
                    "reference_type": type,
                    "user_id": user_id,
                    "session_id": session_id,
                },
                severity="WARNING",
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ReferenceImageAnalysisError as exc:
        try:
            logger.log_struct(
                {
                    "event": "reference_image_upload_failed",
                    "reason": "vision_analysis_error",
                    "reference_type": type,
                    "user_id": user_id,
                    "session_id": session_id,
                },
                severity="ERROR",
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Vision analysis failed for the uploaded image.",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        try:
            logger.log_struct(
                {
                    "event": "reference_image_upload_failed",
                    "reason": "unexpected_error",
                    "reference_type": type,
                    "user_id": user_id,
                    "session_id": session_id,
                },
                severity="ERROR",
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process reference image.",
        ) from exc

    cache_reference_metadata(metadata)

    try:
        logger.log_struct(
            {
                "event": "reference_image_upload_success",
                "reference_id": metadata.id,
                "reference_type": metadata.type,
                "labels_count": len(metadata.labels),
                "user_id": user_id,
                "session_id": session_id,
            },
            severity="INFO",
        )
    except Exception:
        pass

    return {
        "id": metadata.id,
        "signed_url": metadata.signed_url,
        "labels": metadata.labels,
    }


@app.post("/run_preflight")
def run_preflight(request: RunPreflightRequest = Body(...)) -> dict:
    """Preflight: valida/normaliza entrada do usuário e retorna estado inicial.

    Aceita:
      - { "text": "..." }
      - payload do /run com newMessage.parts[0].text
    Retorna 422 com campos faltantes/invalidos, ou 200 com initial_state pronto
    para criar a sessão ADK e executar o pipeline em modo plano fixo.

    Quando `ENABLE_REFERENCE_IMAGES` estiver desativada, quaisquer referências
    enviadas serão ignoradas e o comportamento permanecerá compatível com a
    versão anterior do endpoint.
    """
    if extract_user_input is None:
        raise HTTPException(status_code=500, detail="Preflight helper not available.")

    text = request.resolve_text()
    if not text:
        raise HTTPException(status_code=400, detail="Payload must include 'text' or newMessage.parts[0].text")

    raw_payload = request.raw_payload()
    reference_images_payload = request.reference_images_payload()
    reference_images_provided = any(
        bool((reference_images_payload.get(key) or {}).get("id"))
        for key in ("character", "product")
    )

    # Log início do preflight
    try:
        logger.log_struct({
            "event": "preflight_start",
            "text_len": len(text or ""),
            "reference_images_provided": reference_images_provided,
            "reference_images_feature_enabled": config.enable_reference_images,
        }, severity="INFO")
    except Exception:
        pass
    # Mirror to console
    try:
        py_logger.info(
            "[preflight] start text_len=%s reference_images=%s",
            len(text or ""),
            reference_images_provided,
        )
    except Exception:
        pass

    result = extract_user_input(text)
    try:
        logger.log_struct({
            "event": "preflight_result",
            "success": result.get("success"),
            "errors_count": len(result.get("errors", [])),
        }, severity="INFO")
    except Exception:
        pass
    try:
        py_logger.info(
            "[preflight] result success=%s errors_count=%s",
            result.get("success"),
            len(result.get("errors", [])),
        )
    except Exception:
        pass

    if not result.get("success"):
        try:
            logger.log_struct({
                "event": "preflight_blocked",
                "reason": "validation_failed",
                "errors": result.get("errors", []),
            }, severity="WARNING")
        except Exception:
            pass
        try:
            py_logger.warning(
                "[preflight] blocked errors=%s",
                result.get("errors", []),
            )
        except Exception:
            pass
        raise HTTPException(status_code=422, detail={
            "message": "Campos mínimos ausentes/invalidos.",
            "errors": result.get("errors", []),
            "partial": result.get("data", {}),
        })

    data = result["data"]
    norm = result["normalized"]

    formato = norm.get("formato_anuncio_norm") or data.get("formato_anuncio")
    try:
        plan = get_plan_by_format(formato)
        specs = get_specs_by_format(formato)
        specs_json = get_specs_json_by_format(formato)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=422, detail=str(e))

    # Log plano selecionado
    try:
        logger.log_struct({
            "event": "preflight_plan_selected",
            "formato": formato,
            "feature_name": plan.get("feature_name"),
            "tasks_count": len(plan.get("implementation_tasks", [])),
        }, severity="INFO")
    except Exception:
        pass
    try:
        py_logger.info(
            "[preflight] plan_selected formato=%s tasks_count=%s",
            formato,
            len(plan.get("implementation_tasks", [])),
        )
    except Exception:
        pass

    enable_new_input_fields = config.enable_new_input_fields
    preflight_shadow_mode = config.preflight_shadow_mode
    enable_storybrand_fallback = getattr(config, "enable_storybrand_fallback", False)

    nome_empresa = (data.get("nome_empresa") or "").strip()
    descricao_empresa = (data.get("o_que_a_empresa_faz") or "").strip()
    sexo_alvo_norm = (norm.get("sexo_cliente_alvo_norm") or "").strip()
    sexo_alvo_effective = sexo_alvo_norm or "neutro"

    if preflight_shadow_mode:
        try:
            logger.log_struct(
                {
                    "event": "preflight_new_fields_shadow",
                    "enabled": enable_new_input_fields,
                    "nome_empresa_present": bool(nome_empresa),
                    "o_que_faz_present": bool(descricao_empresa),
                    "sexo_alvo": sexo_alvo_norm or "",
                },
                severity="INFO",
            )
        except Exception:
            pass
        try:
            py_logger.info(
                "[preflight] shadow_new_fields nome_empresa?=%s o_que?=%s sexo=%s",
                bool(nome_empresa),
                bool(descricao_empresa),
                sexo_alvo_norm or "",
            )
        except Exception:
            pass

    if enable_new_input_fields:
        try:
            logger.log_struct(
                {
                    "event": "preflight_new_fields",
                    "nome_empresa_provided": bool(nome_empresa),
                    "o_que_faz_provided": bool(descricao_empresa),
                    "sexo_alvo": sexo_alvo_effective,
                    "defaults_used": {
                        "nome_empresa": not nome_empresa,
                        "o_que_faz": not descricao_empresa,
                        "sexo_alvo": sexo_alvo_effective == "neutro",
                    },
                },
                severity="INFO",
            )
        except Exception:
            pass
        try:
            py_logger.info(
                "[preflight] new_fields nome_empresa?=%s o_que?=%s sexo=%s",
                bool(nome_empresa),
                bool(descricao_empresa),
                sexo_alvo_effective,
            )
        except Exception:
            pass

    # Montar estado inicial para a sessão ADK
    initial_state = {
        "landing_page_url": data.get("landing_page_url"),
        "objetivo_final": (norm.get("objetivo_final_norm") or data.get("objetivo_final")),
        "perfil_cliente": data.get("perfil_cliente"),
        "formato_anuncio": formato,
        "foco": data.get("foco") or "",
        # Plano fixo e specs por formato
        "implementation_plan": plan,
        "format_specs": specs,
        "format_specs_json": specs_json,
        # Sinalizador para pular o planner (será usado em fase 2)
        "planning_mode": "fixed",
    }

    force_flag_payload = _coerce_bool(request.force_storybrand_fallback)

    force_flag_data = data.get("force_storybrand_fallback") if isinstance(data, dict) else None
    if not isinstance(force_flag_data, bool):
        force_flag_data = False

    force_storybrand_fallback = force_flag_data
    if force_flag_payload is not None:
        force_storybrand_fallback = force_flag_payload

    if force_storybrand_fallback:
        if not enable_new_input_fields:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "force_storybrand_fallback exige ENABLE_NEW_INPUT_FIELDS ativo.",
                    "action": "Ative ENABLE_NEW_INPUT_FIELDS e VITE_ENABLE_NEW_FIELDS antes de forçar o fallback.",
                },
            )
        if not enable_storybrand_fallback:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Fallback StoryBrand está desativado na configuração atual.",
                    "action": "Defina ENABLE_STORYBRAND_FALLBACK=true para permitir o acionamento manual.",
                },
            )

    if enable_new_input_fields:
        initial_state.update(
            {
                "nome_empresa": nome_empresa or "Empresa",
                "o_que_a_empresa_faz": descricao_empresa or "",
                "sexo_cliente_alvo": sexo_alvo_effective,
            }
        )

        initial_state["force_storybrand_fallback"] = bool(force_storybrand_fallback)

    initial_state.update(
        {
            "reference_image_character_summary": None,
            "reference_image_product_summary": None,
            "reference_image_safe_search_notes": None,
            "reference_image_character_gcs_uri": "",
            "reference_image_character_labels": "",
            "reference_image_character_user_description": "",
            "reference_image_product_gcs_uri": "",
            "reference_image_product_labels": "",
            "reference_image_product_user_description": "",
        }
    )

    if config.enable_reference_images:
        character_payload = reference_images_payload.get("character") or {}
        product_payload = reference_images_payload.get("product") or {}

        character_metadata = resolve_reference_metadata(character_payload.get("id"))
        product_metadata = resolve_reference_metadata(product_payload.get("id"))

        reference_images_state = {
            "character": merge_user_description(
                character_metadata, character_payload.get("user_description")
            ),
            "product": merge_user_description(
                product_metadata, product_payload.get("user_description")
            ),
        }

        initial_state["reference_images"] = reference_images_state

        summary = build_reference_summary(reference_images_state, raw_payload)
        initial_state["reference_image_summary"] = summary
        initial_state["reference_image_character_summary"] = summary.get("character")
        initial_state["reference_image_product_summary"] = summary.get("product")
        initial_state["reference_image_safe_search_notes"] = summary.get(
            "safe_search_notes"
        )

        character_state = reference_images_state.get("character") or {}
        product_state = reference_images_state.get("product") or {}

        def _format_reference_value(
            data: Mapping[str, Any] | None, key: str
        ) -> str:
            if not data:
                return ""
            value = data.get(key)
            if value in (None, ""):
                return ""
            if isinstance(value, list):
                return ", ".join(str(item) for item in value)
            return str(value)

        initial_state["reference_image_character_gcs_uri"] = (
            character_state.get("gcs_uri") or ""
        )
        initial_state["reference_image_character_labels"] = _format_reference_value(
            character_state, "labels"
        )
        initial_state[
            "reference_image_character_user_description"
        ] = _format_reference_value(character_state, "user_description")
        initial_state["reference_image_product_gcs_uri"] = (
            product_state.get("gcs_uri") or ""
        )
        initial_state["reference_image_product_labels"] = _format_reference_value(
            product_state, "labels"
        )
        initial_state["reference_image_product_user_description"] = (
            _format_reference_value(product_state, "user_description")
        )

        try:
            logger.log_struct(
                {
                    "event": "preflight_reference_images_resolved",
                    "character_id": character_payload.get("id"),
                    "product_id": product_payload.get("id"),
                    "character_found": character_metadata is not None,
                    "product_found": product_metadata is not None,
                    "summary_character": summary.get("character"),
                    "summary_product": summary.get("product"),
                    "safe_search_notes": summary.get("safe_search_notes"),
                },
                severity="INFO",
            )
        except Exception:
            pass
    elif reference_images_provided:
        try:
            logger.log_struct(
                {
                    "event": "preflight_reference_images_ignored",
                    "reason": "feature_flag_disabled",
                },
                severity="INFO",
            )
        except Exception:
            pass

    # P1: Enriquecer estado inicial com CTAs e recomendações
    initial_state["cta_instagram_choices"] = list(CTA_INSTAGRAM_CHOICES)
    initial_state["cta_by_objective"] = CTA_BY_OBJECTIVE

    objetivo = initial_state.get("objetivo_final", "")
    recommended_cta = CTA_BY_OBJECTIVE.get(objetivo, ("Saiba mais",))[0]
    initial_state["recommended_cta"] = recommended_cta

    try:
        py_logger.debug(
            f"Estado inicial enriquecido: objetivo={objetivo}, recommended_cta={recommended_cta}"
        )
    except Exception:
        pass

    response = {
        "success": True,
        "normalized": norm,
        "initial_state": initial_state,
        "plan_summary": {
            "feature_name": plan["feature_name"],
            "tasks": [t["category"] for t in plan.get("implementation_tasks", [])],
        },
    }
    try:
        logger.log_struct({
            "event": "preflight_return",
            "status": "ok",
        }, severity="INFO")
    except Exception:
        pass
    try:
        py_logger.info("[preflight] return status=ok")
    except Exception:
        pass
    return response


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
