"""Integration tests for reference image upload and preflight flow."""

from __future__ import annotations

import io
from typing import Any

import pytest

from app.utils import reference_cache
def test_upload_and_preflight_roundtrip(reference_client) -> None:
    client, metadata = reference_client

    response = client.post(
        "/upload/reference-image",
        files={"file": ("ref.png", io.BytesIO(b"image"), "image/png")},
        data={"type": "character", "user_id": "user", "session_id": "sess"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == metadata.id
    assert payload["labels"] == metadata.labels

    cached = reference_cache.resolve_reference_metadata(metadata.id)
    assert cached is not None
    assert cached.id == metadata.id

    preflight = client.post(
        "/run_preflight",
        json={
            "text": "Criar anúncios",
            "reference_images": {
                "character": {
                    "id": metadata.id,
                    "user_description": "Cliente sorridente",
                }
            },
        },
    )
    assert preflight.status_code == 200
    initial_state = preflight.json()["initial_state"]
    character_state = initial_state["reference_images"]["character"]
    assert character_state["id"] == metadata.id
    assert character_state["user_description"] == "Cliente sorridente"
    assert initial_state["reference_image_character_labels"] == ", ".join(metadata.labels)
    assert "medical=LIKELY" in initial_state["reference_image_safe_search_notes"]


def test_upload_rejected_by_safe_search(reference_client, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.server as server
    from app.utils.vision import ReferenceImageUnsafeError

    async def rejecting_upload(**_: Any):
        raise ReferenceImageUnsafeError("blocked")

    monkeypatch.setattr(server, "upload_reference_image_to_gcs", rejecting_upload)
    client, _ = reference_client
    response = client.post(
        "/upload/reference-image",
        files={"file": ("ref.png", io.BytesIO(b"image"), "image/png")},
        data={"type": "product"},
    )
    assert response.status_code == 400
    assert "blocked" in response.json()["detail"]
