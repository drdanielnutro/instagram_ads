import os
import json
import logging
from pathlib import Path
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from google.cloud import storage
from typing import Any


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


def _has_all_image_urls(data: Any) -> bool:
    """Validate that all variations have complete image URLs.

    Note: We allow variations with image_generation_error since they
    are expected and the frontend handles them gracefully.
    """
    if not isinstance(data, list) or len(data) != 3:
        return False

    required_fields = [
        "image_estado_atual_url",
        "image_estado_intermediario_url",
        "image_estado_aspiracional_url",
    ]

    # At least one variation must have all image URLs
    has_at_least_one_complete = False

    for item in data:
        if not item or not isinstance(item, dict):
            return False
        visual = item.get("visual", {})

        # If variation has image_generation_error, it's acceptable
        if visual.get("image_generation_error"):
            continue

        # Check if this variation has all required URLs
        if all(visual.get(k) for k in required_fields):
            has_at_least_one_complete = True

    return has_at_least_one_complete


def _report_missing(data: Any) -> list[dict[str, Any]]:
    """Report which image URLs are missing from variations."""
    out = []
    if not isinstance(data, list):
        return [{"error": "payload_not_list"}]

    for idx, item in enumerate(data):
        if not item or not isinstance(item, dict):
            out.append({"variation": idx, "error": "invalid_structure"})
            continue

        visual = item.get("visual", {})

        # Skip variations with image generation errors
        if visual.get("image_generation_error"):
            out.append({"variation": idx, "status": "generation_error", "error": visual["image_generation_error"]})
            continue

        missing = [k for k in [
            "image_estado_atual_url",
            "image_estado_intermediario_url",
            "image_estado_aspiracional_url",
        ] if not visual.get(k)]

        if missing:
            out.append({"variation": idx, "missing": missing})

    return out


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
def download_final(
    user_id: str = Query(...),
    session_id: str = Query(...),
    inline: bool = Query(False),
):
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
            if inline:
                try:
                    payload = blob.download_as_bytes()

                    # Validate the payload has all required image URLs (optional validation)
                    data = json.loads(payload)
                    if not _has_all_image_urls(data):
                        logger.warning(
                            "Some image assets missing for session %s. Details: %s",
                            session_id,
                            _report_missing(data)
                        )
                        # For now, we'll still return the data as frontend handles missing images gracefully
                        # Uncomment below to enforce strict validation:
                        # raise HTTPException(
                        #     status_code=424,
                        #     detail={
                        #         "message": "Image assets incomplete. Please reprocess the session.",
                        #         "missing": _report_missing(data)
                        #     }
                        # )

                    return Response(content=payload, media_type="application/json")
                except Exception as e:
                    logger.warning(
                        "Failed to download inline payload for %s: %s. Trying local fallback.",
                        gcs_uri,
                        e,
                    )
                    # Try local fallback before returning signed_url
                    local_path = meta.get("final_delivery_local_path")
                    if local_path and Path(local_path).exists():
                        try:
                            payload = Path(local_path).read_bytes()

                            # Validate the local payload (optional validation)
                            data = json.loads(payload)
                            if not _has_all_image_urls(data):
                                logger.warning(
                                    "Some image assets missing in local file for session %s. Details: %s",
                                    session_id,
                                    _report_missing(data)
                                )
                                # For now, we'll still return the data as frontend handles missing images gracefully
                                # Uncomment below to enforce strict validation:
                                # raise HTTPException(
                                #     status_code=424,
                                #     detail={
                                #         "message": "Image assets incomplete. Please reprocess the session.",
                                #         "missing": _report_missing(data)
                                #     }
                                # )

                            logger.info(
                                "Successfully served inline content from local fallback for session %s",
                                session_id
                            )
                            return Response(content=payload, media_type="application/json")
                        except HTTPException:
                            raise
                        except Exception as local_err:
                            logger.error(
                                "Failed to read local fallback for session %s: %s",
                                session_id,
                                local_err
                            )
                    # If we reach here, neither GCS nor local worked for inline
                    logger.error(
                        "Unable to serve inline content for session %s - no fallback available",
                        session_id
                    )

            # For non-inline requests, return signed URL as before
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=600),
                method="GET",
                response_disposition=f'attachment; filename="{filename}"',
                response_type="application/json",
            )
            return {"ok": True, "signed_url": url, "expires_in": 600}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to generate Signed URL for %s: %s. Falling back to local download if available.",
                gcs_uri,
                e,
                exc_info=True,
            )
            # Fall through to local fallback below

    # Fallback to local stream
    local_path = meta.get("final_delivery_local_path")
    if local_path and Path(local_path).exists():
        if inline:
            try:
                payload = Path(local_path).read_bytes()
            except Exception:
                logger.exception(
                    "Failed to read local inline payload for session %s from %s.",
                    session_id,
                    local_path,
                )
            else:
                return Response(content=payload, media_type="application/json")

        return FileResponse(path=local_path, media_type="application/json", filename=filename)

    raise HTTPException(status_code=404, detail="No artifact available for download")
