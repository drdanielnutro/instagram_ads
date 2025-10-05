from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from google.cloud import storage

from app.utils.delivery_status import clear_failure_meta
from app.utils.json_tools import try_parse_json_string
from app.utils.session_state import resolve_state, safe_session_id, safe_user_id


logger = logging.getLogger(__name__)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _upload_to_gcs(bucket_uri: str, dest_path: str, data: bytes) -> str:
    if not bucket_uri.startswith("gs://"):
        raise ValueError("ARTIFACTS_BUCKET must start with gs://")
    bucket_name = bucket_uri[len("gs://") :].rstrip("/")
    client = storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_path)
    blob.upload_from_string(data, content_type="application/json")
    return f"gs://{bucket_name}/{dest_path}"


def persist_final_delivery(callback_context: Any) -> None:
    """After-agent callback to persist the final JSON delivery locally and optionally to GCS.

    - Saves a unique file under artifacts/ads_final/
    - If ARTIFACTS_BUCKET (gs://...) is set, also uploads to GCS at ads/final/<filename>
    - Writes local and GCS paths back into state
    """

    try:
        state = resolve_state(callback_context)
        payload = state.get("final_code_delivery")
        deterministic_result = state.get("deterministic_final_validation")
        normalized_payload: dict[str, Any] | None = None
        if isinstance(deterministic_result, dict):
            candidate = deterministic_result.get("normalized_payload")
            if isinstance(candidate, dict):
                normalized_payload = candidate

        normalized_variations: list[Any] | None = None
        if normalized_payload:
            variations = normalized_payload.get("variations")
            if isinstance(variations, list):
                normalized_variations = variations

        if normalized_variations is None:
            parsed_variations = state.get("final_code_delivery_parsed")
            if isinstance(parsed_variations, list):
                normalized_variations = parsed_variations

        data_obj: Any
        if normalized_variations is not None:
            data_obj = normalized_variations
        else:
            if not payload:
                logger.warning("persist_final_delivery: no final_code_delivery in state; skipping")
                return

            # Parse/validate JSON (string or list)
            if isinstance(payload, str):
                parsed, data_obj = try_parse_json_string(payload)
                if not parsed:
                    try:
                        data_obj = json.loads(payload)
                    except json.JSONDecodeError:
                        # Not valid JSON -> wrap as string content
                        data_obj = payload
            else:
                data_obj = payload

        # Determine format for naming (best effort)
        fmt = state.get("formato_anuncio") or "unknown"
        if (fmt in ("", "unknown")) and isinstance(data_obj, list) and data_obj:
            try:
                fmt = data_obj[0].get("formato", fmt) or fmt
            except Exception:
                pass

        session_id = safe_session_id(callback_context)
        user_id = safe_user_id(callback_context)
        ts = time.strftime("%Y%m%d-%H%M%S")
        fname = f"{ts}_{session_id}_{fmt}.json"

        # Local save
        base_dir = Path("artifacts/ads_final")
        _ensure_dir(base_dir)
        local_path = base_dir / fname
        with local_path.open("w", encoding="utf-8") as f:
            json.dump(data_obj, f, ensure_ascii=False, indent=2)
        logger.info("Final delivery saved locally: %s", str(local_path))

        # Try GCS upload if configured
        gcs_uri = ""
        deliveries_bucket_uri = os.getenv("DELIVERIES_BUCKET", "").strip()
        if deliveries_bucket_uri.startswith("gs://"):
            try:
                prefix = f"deliveries/{user_id}/{session_id}"
                gcs_dest = f"{prefix}/{fname}"
                payload_bytes = json.dumps(data_obj, ensure_ascii=False).encode("utf-8")
                gcs_uri = _upload_to_gcs(deliveries_bucket_uri, gcs_dest, payload_bytes)
                logger.info("Final delivery uploaded to GCS: %s", gcs_uri)
            except Exception as e:
                logger.error("Failed to upload final delivery to GCS: %s", e)
        else:
            if os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"):
                logger.warning(
                    "DELIVERIES_BUCKET is not configured; skipping GCS upload in production environment.")

        # Persist paths into state for easy retrieval
        state["final_delivery_local_path"] = str(local_path)
        if gcs_uri:
            state["final_delivery_gcs_uri"] = gcs_uri

        # Atualiza representação normalizada no estado (garante consistência pós-validador)
        if normalized_variations is not None:
            state["final_code_delivery_parsed"] = normalized_variations
            state["final_code_delivery"] = json.dumps(normalized_variations, ensure_ascii=False)

        stage_name = "legacy_final_validation"
        grade = "pass"
        if isinstance(deterministic_result, dict):
            stage_name = "deterministic_final_validation"
            grade = deterministic_result.get("grade") or grade

        storybrand_audit = state.get("storybrand_audit_trail")
        if not isinstance(storybrand_audit, list):
            storybrand_audit = [] if storybrand_audit is None else [storybrand_audit]
        storybrand_metrics = state.get("storybrand_gate_metrics")
        if not isinstance(storybrand_metrics, dict):
            storybrand_metrics = {}
        storybrand_fallback = state.get("storybrand_fallback_meta")
        if not isinstance(storybrand_fallback, dict):
            storybrand_fallback = {}
        delivery_audit = state.get("delivery_audit_trail")
        if not isinstance(delivery_audit, list):
            delivery_audit = [] if delivery_audit is None else [delivery_audit]

        state["final_delivery_status"] = {
            "status": "completed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_id": session_id,
            "user_id": user_id,
            "stage": stage_name,
            "grade": grade,
            "storybrand_audit_trail": storybrand_audit,
            "storybrand_gate_metrics": storybrand_metrics,
            "storybrand_fallback_meta": storybrand_fallback,
            "delivery_audit_trail": delivery_audit,
        }

        if stage_name == "deterministic_final_validation":
            # Evita sinalizadores legados quando a validação determinística foi concluída.
            state.pop("final_validation_result_failed", None)
            state.pop("final_validation_result_failure_reason", None)

        # Write sidecar meta locally and to GCS for fast lookup by endpoints
        try:
            meta = {
                "filename": fname,
                "formato": fmt,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "size_bytes": local_path.stat().st_size if local_path.exists() else None,
                "final_delivery_local_path": str(local_path),
                "final_delivery_gcs_uri": gcs_uri,
                "user_id": user_id,
                "session_id": session_id,
                "stage": stage_name,
                "grade": grade,
                "deterministic_final_validation": state.get("deterministic_final_validation"),
                "semantic_visual_review": state.get("semantic_visual_review"),
                "image_assets_review": state.get("image_assets_review"),
                "storybrand_audit_trail": storybrand_audit,
                "storybrand_gate_metrics": storybrand_metrics,
                "storybrand_fallback_meta": storybrand_fallback,
                "delivery_audit_trail": delivery_audit,
            }
            meta_dir = base_dir / "meta"
            _ensure_dir(meta_dir)
            meta_local = meta_dir / f"{session_id}.json"
            with meta_local.open("w", encoding="utf-8") as mf:
                json.dump(meta, mf, ensure_ascii=False, indent=2)
            logger.info("Final delivery meta saved locally: %s", str(meta_local))

            if deliveries_bucket_uri.startswith("gs://"):
                try:
                    meta_dest = f"deliveries/{user_id}/{session_id}/meta.json"
                    _upload_to_gcs(deliveries_bucket_uri, meta_dest, json.dumps(meta, ensure_ascii=False).encode("utf-8"))
                    state["final_delivery_meta_gcs_uri"] = f"{deliveries_bucket_uri.rstrip('/')}/{meta_dest}"
                    logger.info("Final delivery meta uploaded to GCS: %s", state["final_delivery_meta_gcs_uri"])
                except Exception as me:
                    logger.error("Failed to upload final delivery meta to GCS: %s", me)
        except Exception as e:
            logger.error("Failed to persist final delivery meta: %s", e)

        clear_failure_meta(session_id, state=state)
    except Exception as e:
        logger.error("persist_final_delivery error: %s", e)
