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


def _safe_user_id(callback_context: Any) -> str:
    """Best-effort extraction of user_id from callback context.

    Falls back to `state.get('user_id')` and finally 'anonymous'.
    """
    try:
        sess = getattr(callback_context, "_invocation_context", None)
        if sess and getattr(sess, "session", None):
            s = sess.session
            uid = getattr(s, "user_id", None)
            if uid:
                return uid
    except Exception:
        pass
    try:
        st = getattr(callback_context, "state", {}) or {}
        uid = st.get("user_id")
        if uid:
            return str(uid)
    except Exception:
        pass
    return "anonymous"


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
        if (fmt in ("", "unknown")) and isinstance(data_obj, list) and data_obj:
            try:
                fmt = data_obj[0].get("formato", fmt) or fmt
            except Exception:
                pass

        session_id = _safe_session_id(callback_context)
        user_id = _safe_user_id(callback_context)
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
    except Exception as e:
        logger.error("persist_final_delivery error: %s", e)
