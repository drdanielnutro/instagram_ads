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

import os
import logging

import google.auth
from fastapi import FastAPI, HTTPException
from fastapi import Body
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export

from app.utils.gcs import create_bucket_if_not_exists
from app.utils.tracing import CloudTraceLoggingSpanExporter
from app.utils.typing import Feedback
from app.plan_models.fixed_plans import get_plan_by_format
from app.format_specifications import get_specs_by_format, get_specs_json_by_format

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
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Artifacts bucket configuration (parametrized via env vars)
artifacts_bucket = os.getenv(
    "ARTIFACTS_BUCKET", f"gs://{project_id}-facilitador-logs-data"
)
bucket_location = os.getenv(
    "ARTIFACTS_BUCKET_LOCATION",
    os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
)
create_bucket_if_not_exists(
    bucket_name=artifacts_bucket, project=project_id, location=bucket_location
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


@app.post("/run_preflight")
def run_preflight(payload: dict = Body(...)) -> dict:
    """Preflight: valida/normaliza entrada do usuário e retorna estado inicial.

    Aceita:
      - { "text": "..." }
      - payload do /run com newMessage.parts[0].text
    Retorna 422 com campos faltantes/invalidos, ou 200 com initial_state pronto
    para criar a sessão ADK e executar o pipeline em modo plano fixo.
    """
    if extract_user_input is None:
        raise HTTPException(status_code=500, detail="Preflight helper not available.")

    # Extrair texto do payload (compatível com /run e modo simples)
    text = None
    if isinstance(payload, dict):
        text = payload.get("text")
        if not text:
            try:
                parts = payload.get("newMessage", {}).get("parts", [])
                if parts and isinstance(parts, list):
                    text = parts[0].get("text")
            except Exception:
                text = None
    if not text:
        raise HTTPException(status_code=400, detail="Payload must include 'text' or newMessage.parts[0].text")

    # Log início do preflight
    try:
        logger.log_struct({
            "event": "preflight_start",
            "text_len": len(text or ""),
        }, severity="INFO")
    except Exception:
        pass
    # Mirror to console
    try:
        py_logger.info("[preflight] start text_len=%s", len(text or ""))
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
