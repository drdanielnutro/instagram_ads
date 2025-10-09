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

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import google.cloud.storage as storage
from google.api_core import exceptions

from app.config import config
from app.schemas.reference_assets import ReferenceImageMetadata
from app.utils.vision import (
    ReferenceImageAnalysisError,
    ReferenceImageUnsafeError,
    analyze_reference_image,
)


logger = logging.getLogger(__name__)


def create_bucket_if_not_exists(bucket_name: str, project: str, location: str) -> None:
    """Creates a new bucket if it doesn't already exist.

    Args:
        bucket_name: Name of the bucket to create
        project: Google Cloud project ID
        location: Location to create the bucket in (defaults to southamerica-east1)
    """
    storage_client = storage.Client(project=project)

    if bucket_name.startswith("gs://"):
        bucket_name = bucket_name[5:]
    try:
        storage_client.get_bucket(bucket_name)
        logger.info("Bucket %s already exists", bucket_name)
    except exceptions.NotFound:
        bucket = storage_client.create_bucket(
            bucket_name,
            location=location,
            project=project,
        )
        logger.info("Created bucket %s in %s", bucket.name, bucket.location)


def _sanitize_path_component(value: str, fallback: str) -> str:
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch in {"-", "_"})
    return cleaned or fallback


async def upload_reference_image(
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    reference_type: Literal["character", "product"],
    user_id: str | None = None,
    session_id: str | None = None,
    storage_client: storage.Client | None = None,
) -> ReferenceImageMetadata:
    """Upload a reference image to GCS and analyse it with Vision AI."""

    if not file_bytes:
        raise ValueError("file_bytes cannot be empty")

    bucket_name = config.reference_images_bucket or os.getenv("REFERENCE_IMAGES_BUCKET")
    if not bucket_name:
        raise RuntimeError("REFERENCE_IMAGES_BUCKET is not configured")

    client = storage_client or storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
    bucket = client.bucket(bucket_name)

    reference_id = f"ref_{uuid.uuid4().hex}"
    suffix = Path(filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".bin"

    safe_user = _sanitize_path_component((user_id or "anonymous"), "anonymous")
    safe_session = _sanitize_path_component((session_id or "session"), "session")

    blob_path = f"reference-images/{safe_user}/{safe_session}/{reference_type}/{reference_id}{suffix}"
    blob = bucket.blob(blob_path)
    uploaded_at = datetime.now(timezone.utc)

    try:
        await asyncio.to_thread(
            blob.upload_from_string, file_bytes, content_type=content_type
        )
    except exceptions.GoogleAPICallError as exc:
        logger.error("Failed to upload reference image %s: %s", reference_id, exc)
        raise

    gcs_uri = f"gs://{bucket_name}/{blob_path}"
    try:
        signed_url = await asyncio.to_thread(
            blob.generate_signed_url,
            expiration=timedelta(seconds=config.image_signed_url_ttl),
            method="GET",
            version="v4",
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to generate signed URL for %s: %s", gcs_uri, exc)
        await asyncio.to_thread(blob.delete)
        raise

    try:
        metadata = await analyze_reference_image(
            image_bytes=file_bytes,
            reference_type=reference_type,
            reference_id=reference_id,
            gcs_uri=gcs_uri,
            signed_url=signed_url,
            uploaded_at=uploaded_at,
        )
    except ReferenceImageUnsafeError:
        logger.warning("Reference image %s rejected by SafeSearch", reference_id)
        await asyncio.to_thread(blob.delete)
        raise
    except ReferenceImageAnalysisError:
        logger.error("Vision analysis failed for reference image %s", reference_id)
        await asyncio.to_thread(blob.delete)
        raise
    except Exception:  # pragma: no cover - defensive cleanup
        await asyncio.to_thread(blob.delete)
        raise

    logger.info("Reference image %s stored at %s", reference_id, gcs_uri)
    return metadata
