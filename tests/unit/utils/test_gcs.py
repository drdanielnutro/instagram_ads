from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, Literal, cast

import pytest

from app.schemas.reference_assets import ReferenceImageMetadata
from app.utils import gcs


@pytest.mark.asyncio
@pytest.mark.parametrize("bucket_value", ["test-bucket", "gs://test-bucket"])
async def test_upload_reference_image_accepts_bucket_formats(
    monkeypatch: pytest.MonkeyPatch, bucket_value: str
) -> None:
    called: dict[str, Any] = {}

    class FakeBlob:
        def __init__(self, bucket_name: str, blob_path: str) -> None:
            called["blob_path"] = blob_path
            called["blob_bucket_name"] = bucket_name

        def upload_from_string(self, data: bytes, content_type: str) -> None:
            called["upload_payload"] = data
            called["upload_content_type"] = content_type

        def generate_signed_url(self, *, expiration, method, version) -> str:
            called["signed_url_kwargs"] = {
                "expiration": expiration,
                "method": method,
                "version": version,
            }
            return "https://signed.url"

        def delete(self) -> None:  # pragma: no cover - defensive
            called["deleted"] = True

    class FakeBucket:
        def __init__(self, name: str) -> None:
            self.name = name

        def blob(self, blob_path: str) -> FakeBlob:
            return FakeBlob(self.name, blob_path)

    class FakeClient:
        def __init__(self, project: str | None = None) -> None:
            called["project"] = project

        def bucket(self, name: str) -> FakeBucket:
            called["bucket_name"] = name
            return FakeBucket(name)

    async def fake_analyze_reference_image(
        *,
        image_bytes: bytes,
        reference_type: str,
        reference_id: str,
        gcs_uri: str,
        signed_url: str,
        uploaded_at: datetime,
    ) -> ReferenceImageMetadata:
        called["analyze_reference_image_args"] = {
            "image_bytes": image_bytes,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "gcs_uri": gcs_uri,
            "signed_url": signed_url,
            "uploaded_at": uploaded_at,
        }
        return ReferenceImageMetadata(
            id=reference_id,
            type=cast(Literal["character", "product"], reference_type),
            gcs_uri=gcs_uri,
            signed_url=signed_url,
            labels=["ok"],
            safe_search_flags={},
            uploaded_at=uploaded_at,
        )

    monkeypatch.setattr(gcs, "storage", SimpleNamespace(Client=FakeClient), raising=False)
    monkeypatch.setattr(gcs, "analyze_reference_image", fake_analyze_reference_image)
    monkeypatch.setattr(gcs.config, "reference_images_bucket", None, raising=False)
    monkeypatch.setattr(gcs.uuid, "uuid4", lambda: SimpleNamespace(hex="deadbeef"))
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("REFERENCE_IMAGES_BUCKET", bucket_value)

    metadata = await gcs.upload_reference_image(
        file_bytes=b"binary-data",
        filename="image.png",
        content_type="image/png",
        reference_type="character",
        user_id="User",
        session_id="Session",
    )

    assert called["bucket_name"] == "test-bucket"
    assert called["blob_bucket_name"] == "test-bucket"
    assert metadata.gcs_uri.startswith("gs://test-bucket/reference-images/")
    assert metadata.id == "ref_deadbeef"
    assert called["analyze_reference_image_args"]["gcs_uri"] == metadata.gcs_uri
