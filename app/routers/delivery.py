import os
import json
import logging
from pathlib import Path
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from google.cloud import storage


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/delivery", tags=["delivery"])


def _load_local_meta(session_id: str) -> Optional[dict]:
    meta_path = Path("artifacts/ads_final/meta") / f"{session_id}.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to read local meta for session %s: %s", session_id, e)
    return None


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError("GCS URI must start with gs://")
    path = uri[5:]
    bucket, _, blob = path.partition("/")
    if not bucket or not blob:
        raise ValueError("Invalid GCS URI")
    return bucket, blob


@router.get("/final/meta")
def get_final_meta(user_id: str = Query(...), session_id: str = Query(...)):
    """Return final delivery metadata for a given user/session.

    Relies on the sidecar meta saved by the persistence callback.
    """
    meta = _load_local_meta(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Final delivery not available yet")

    # Optional sanity check: if user_id mismatches, still return 404
    if str(meta.get("user_id", "")) != str(user_id):
        raise HTTPException(status_code=404, detail="Final delivery not found for this user/session")

    return {"ok": True, **meta}


@router.get("/final/download")
def download_final(user_id: str = Query(...), session_id: str = Query(...)):
    """Provide access to the final delivery via Signed URL (GCS) or local stream.

    - If meta includes a GCS URI, generate a short-lived v4 Signed URL and return it.
    - Otherwise, stream the local file (dev fallback).
    """
    meta = _load_local_meta(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Final delivery not available yet")

    if str(meta.get("user_id", "")) != str(user_id):
        raise HTTPException(status_code=404, detail="Final delivery not found for this user/session")

    gcs_uri = (meta.get("final_delivery_gcs_uri") or "").strip()
    filename = meta.get("filename") or f"{session_id}.json"

    if gcs_uri.startswith("gs://"):
        # Generate Signed URL
        try:
            bucket_name, blob_name = _parse_gcs_uri(gcs_uri)
            client = storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=600),
                method="GET",
                response_disposition=f'attachment; filename="{filename}"',
                response_type="application/json",
            )
            return {"ok": True, "signed_url": url, "expires_in": 600}
        except Exception as e:
            logger.error("Failed to generate Signed URL for %s: %s", gcs_uri, e)
            raise HTTPException(status_code=500, detail="Failed to generate Signed URL")

    # Fallback to local stream
    local_path = meta.get("final_delivery_local_path")
    if local_path and Path(local_path).exists():
        return FileResponse(path=local_path, media_type="application/json", filename=filename)

    raise HTTPException(status_code=404, detail="No artifact available for download")

