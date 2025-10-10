from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.utils import vision as vision_module
from app.utils.vision import (
    ReferenceImageAnalysisError,
    ReferenceImageUnsafeError,
    analyze_reference_image,
)


@pytest.fixture(autouse=True)
def _reset_vision_module(monkeypatch: pytest.MonkeyPatch) -> None:
    async def immediate_call(method, *args, **kwargs):  # type: ignore[no-untyped-def]
        return method(*args, **kwargs)

    monkeypatch.setattr(vision_module, "_call_vision", immediate_call)


class _FakeVisionClient:
    def __init__(self, safe_response: Any, label_response: Any) -> None:
        self.safe_response = safe_response
        self.label_response = label_response
        self.safe_calls: list[Any] = []
        self.label_calls: list[Any] = []

    def safe_search_detection(self, *, image: Any) -> Any:
        self.safe_calls.append(image)
        return self.safe_response

    def label_detection(self, *, image: Any) -> Any:
        self.label_calls.append(image)
        return self.label_response


def _configure_fake_vision(
    monkeypatch: pytest.MonkeyPatch,
    *,
    safe_annotation: Any,
    label_annotations: list[Any],
) -> _FakeVisionClient:
    safe_response = SimpleNamespace(safe_search_annotation=safe_annotation)
    label_response = SimpleNamespace(label_annotations=label_annotations)
    client = _FakeVisionClient(safe_response, label_response)

    class _FakeImage:
        def __init__(self, *, content: bytes) -> None:
            self.content = content

    fake_vision = SimpleNamespace(
        ImageAnnotatorClient=lambda: client,
        Image=lambda *, content: _FakeImage(content=content),
        Likelihood=lambda value: SimpleNamespace(name=f"LIKELIHOOD_{value}"),
    )
    monkeypatch.setattr(vision_module, "vision", fake_vision)
    return client


@pytest.mark.asyncio
async def test_analyze_reference_image_returns_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    safe_annotation = SimpleNamespace(
        adult="VERY_UNLIKELY",
        violence="UNLIKELY",
        racy="VERY_UNLIKELY",
        medical="POSSIBLE",
        spoof="VERY_UNLIKELY",
    )
    label_annotations = [
        SimpleNamespace(description="smiling customer"),
        SimpleNamespace(description="clinic lobby"),
        SimpleNamespace(description="ignored"),
    ]
    client = _configure_fake_vision(
        monkeypatch,
        safe_annotation=safe_annotation,
        label_annotations=label_annotations,
    )

    uploaded_at = datetime(2025, 2, 1, 15, tzinfo=timezone.utc)
    metadata = await analyze_reference_image(
        image_bytes=b"image-bytes",
        reference_type="character",
        reference_id="ref-vision",
        gcs_uri="gs://bucket/ref-vision",
        signed_url="https://signed/ref-vision",
        uploaded_at=uploaded_at,
    )

    assert metadata.id == "ref-vision"
    assert metadata.type == "character"
    assert metadata.safe_search_flags["medical"] == "POSSIBLE"
    assert metadata.labels == ["smiling customer", "clinic lobby", "ignored"][:10]
    assert metadata.uploaded_at == uploaded_at
    # Ensure the fake client received the expected Image payload twice.
    assert len(client.safe_calls) == 1
    assert len(client.label_calls) == 1
    assert client.safe_calls[0].content == b"image-bytes"


@pytest.mark.asyncio
async def test_analyze_reference_image_raises_on_blocked_categories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    safe_annotation = SimpleNamespace(
        adult="LIKELY",
        violence="VERY_UNLIKELY",
        racy="UNLIKELY",
        medical="POSSIBLE",
        spoof="UNLIKELY",
    )
    _configure_fake_vision(monkeypatch, safe_annotation=safe_annotation, label_annotations=[])

    with pytest.raises(ReferenceImageUnsafeError) as excinfo:
        await analyze_reference_image(
            image_bytes=b"image-bytes",
            reference_type="product",
            reference_id="blocked",
            gcs_uri="gs://bucket/blocked",
            signed_url="https://signed/blocked",
        )

    assert "adult" in str(excinfo.value)


@pytest.mark.asyncio
async def test_analyze_reference_image_requires_bytes() -> None:
    with pytest.raises(ReferenceImageAnalysisError):
        await analyze_reference_image(
            image_bytes=b"",
            reference_type="character",
            reference_id="empty",
            gcs_uri="gs://bucket/empty",
            signed_url="https://signed/empty",
        )
