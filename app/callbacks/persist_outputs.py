import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from google.cloud import storage


logger = logging.getLogger(__name__)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_session_id(callback_context: Any) -> str:
    try:
        sess = getattr(callback_context, "_invocation_context", None)
        if sess and getattr(sess, "session", None):
            s = sess.session
            return getattr(s, "id", None) or getattr(s, "session_id", None) or "nosession"
    except Exception:
        pass
    return "nosession"


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
        state = getattr(callback_context, "state", {}) or {}
        payload = state.get("final_code_delivery")
        if not payload:
            logger.warning("persist_final_delivery: no final_code_delivery in state; skipping")
            return

        # Parse/validate JSON (string or list)
        if isinstance(payload, str):
            try:
                data_obj = json.loads(payload)
            except json.JSONDecodeError:
                # Not valid JSON -> wrap as string content
                data_obj = payload
        else:
            data_obj = payload

        # Determine format for naming (best effort)
        fmt = state.get("formato_anuncio") or "unknown"
        if fmt == "" and isinstance(data_obj, list) and data_obj:
            fmt = data_obj[0].get("formato", "unknown")

        session_id = _safe_session_id(callback_context)
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
        bucket_uri = os.getenv("ARTIFACTS_BUCKET", "").strip()
        if bucket_uri.startswith("gs://"):
            try:
                gcs_dest = f"ads/final/{fname}"
                gcs_uri = _upload_to_gcs(bucket_uri, gcs_dest, json.dumps(data_obj, ensure_ascii=False).encode("utf-8"))
                logger.info("Final delivery uploaded to GCS: %s", gcs_uri)
            except Exception as e:
                logger.error("Failed to upload final delivery to GCS: %s", e)

        # Persist paths into state for easy retrieval
        state["final_delivery_local_path"] = str(local_path)
        if gcs_uri:
            state["final_delivery_gcs_uri"] = gcs_uri
    except Exception as e:
        logger.error("persist_final_delivery error: %s", e)

