"""Unit tests for generate_transformation_images tool."""

from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module
from types import SimpleNamespace
from typing import Any

import pytest

from app.config import config
from app.schemas.reference_assets import ReferenceImageMetadata

gti = import_module("app.tools.generate_transformation_images")

class _FakeReferenceImage:
    def __init__(self, name: str) -> None:
        self.name = name

    def convert(self, mode: str) -> "_FakeReferenceImage":
        return self

    def save(self, buffer, format: str = "PNG") -> None:  # noqa: D401 - required by PIL contract
        buffer.write(b"image")


class _FakeGeneratedImage:
    def __init__(self, stage: int) -> None:
        self.stage = stage

    def convert(self, mode: str) -> "_FakeGeneratedImage":
        return self

    def save(self, buffer, format: str = "PNG") -> None:
        buffer.write(f"stage-{self.stage}".encode("utf-8"))


@pytest.fixture()
def reference_character() -> ReferenceImageMetadata:
    return ReferenceImageMetadata(
        id="char-1",
        type="character",
        gcs_uri="gs://bucket/char-1",
        signed_url="https://signed/char-1",
        labels=["hero", "confident"],
        safe_search_flags={"adult": "VERY_UNLIKELY"},
        user_description="Heroína confiante",
        uploaded_at=datetime(2025, 1, 5, 12, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def reference_product() -> ReferenceImageMetadata:
    return ReferenceImageMetadata(
        id="prod-9",
        type="product",
        gcs_uri="gs://bucket/prod-9",
        signed_url="https://signed/prod-9",
        labels=["shoes", "leather", "red"],
        safe_search_flags={"violence": "VERY_UNLIKELY"},
        user_description="Tênis vermelho premium",
        uploaded_at=datetime(2025, 1, 6, 18, 30, tzinfo=timezone.utc),
    )


@pytest.fixture()
def metadata_payload() -> dict[str, Any]:
    return {
        "user_id": "user-1",
        "session_id": "sess-2",
        "character_summary": "Heroína confiante",
        "product_summary": "Tênis vermelho premium",
    }


@pytest.mark.asyncio
async def test_generate_transformation_images_with_references(
    monkeypatch: pytest.MonkeyPatch,
    reference_character: ReferenceImageMetadata,
    reference_product: ReferenceImageMetadata,
    metadata_payload: dict[str, Any],
) -> None:
    prompts: list[dict[str, Any]] = []

    async def fake_call_model(inputs: list[Any]) -> _FakeGeneratedImage:
        prompt_text = next((item for item in inputs if isinstance(item, str)), "")
        image_names = [getattr(item, "name", getattr(item, "stage", None)) for item in inputs if not isinstance(item, str)]
        prompts.append({"prompt": prompt_text, "inputs": image_names})
        return _FakeGeneratedImage(len(prompts))

    async def fake_upload_image(*, stage_label: str, **_: Any) -> SimpleNamespace:
        return SimpleNamespace(
            gcs_uri=f"gs://generated/{stage_label}",
            signed_url=f"https://cdn/{stage_label}",
        )

    def fake_load_reference_image(metadata: ReferenceImageMetadata) -> _FakeReferenceImage:
        return _FakeReferenceImage(metadata.id)

    monkeypatch.setattr(
        gti,
        "_call_model",
        lambda inputs: fake_call_model(list(inputs)),
    )
    monkeypatch.setattr(
        gti,
        "_upload_image",
        lambda image, **kwargs: fake_upload_image(**kwargs),
    )
    monkeypatch.setattr(
        gti,
        "_load_reference_image",
        fake_load_reference_image,
    )
    monkeypatch.setattr(config, "image_current_prompt_template", "C:{prompt_atual} [{character_summary}] {character_labels}")
    monkeypatch.setattr(config, "image_intermediate_prompt_template", "I:{prompt_intermediario}")
    monkeypatch.setattr(config, "image_aspirational_prompt_template_with_product", "A:{prompt_aspiracional}:{product_summary}:{product_labels}")

    result = await gti.generate_transformation_images(
        prompt_atual="Emotion: Joyful | Stage one",
        prompt_intermediario="Stage two",
        prompt_aspiracional="Stage three",
        variation_idx=0,
        metadata=metadata_payload,
        reference_character=reference_character,
        reference_product=reference_product,
    )

    assert len(prompts) == 3
    assert prompts[0]["prompt"] == "C:Emotion: Joyful | Stage one [Heroína confiante] hero, confident"
    assert prompts[1]["prompt"] == "I:Stage two"
    assert prompts[2]["prompt"] == "A:Stage three:Tênis vermelho premium:shoes, leather, red"
    assert result["estado_atual"]["gcs_uri"].endswith("estado_atual")
    assert result["estado_aspiracional"]["signed_url"].endswith("estado_aspiracional")
    meta = result["meta"]
    assert meta["reference_character_id"] == "char-1"
    assert meta["reference_product_id"] == "prod-9"
    assert meta["reference_character_used"] is True
    assert meta["reference_product_used"] is True


@pytest.mark.asyncio
async def test_generate_transformation_images_product_only(monkeypatch: pytest.MonkeyPatch, reference_product: ReferenceImageMetadata) -> None:
    prompts: list[str] = []

    async def fake_call_model(inputs: list[Any]) -> _FakeGeneratedImage:
        prompt_text = next((item for item in inputs if isinstance(item, str)), "")
        prompts.append(prompt_text)
        return _FakeGeneratedImage(len(prompts))

    async def fake_upload_image(*, stage_label: str, **_: Any) -> SimpleNamespace:
        return SimpleNamespace(gcs_uri=f"gs://generated/{stage_label}", signed_url="")

    def fake_load_reference_image(_: ReferenceImageMetadata) -> _FakeReferenceImage:
        return _FakeReferenceImage("product")

    monkeypatch.setattr(
        gti,
        "_call_model",
        lambda inputs: fake_call_model(list(inputs)),
    )
    monkeypatch.setattr(
        gti,
        "_upload_image",
        lambda image, **kwargs: fake_upload_image(**kwargs),
    )
    monkeypatch.setattr(
        gti,
        "_load_reference_image",
        fake_load_reference_image,
    )

    result = await gti.generate_transformation_images(
        prompt_atual="Stage one",
        prompt_intermediario="Stage two",
        prompt_aspiracional="Stage three",
        variation_idx=1,
        metadata={"user_id": "user", "session_id": "session", "product_summary": None},
        reference_character=None,
        reference_product=reference_product,
    )

    assert prompts[0].startswith("Stage one Highlight the approved product reference")
    assert "integrate" in prompts[2].lower()
    meta = result["meta"]
    assert meta.get("reference_character_used", False) is False
    assert meta["reference_product_used"] is True


@pytest.mark.asyncio
async def test_generate_transformation_images_records_load_errors(
    monkeypatch: pytest.MonkeyPatch,
    reference_character: ReferenceImageMetadata,
) -> None:
    async def fake_call_model(inputs: list[Any]) -> _FakeGeneratedImage:
        return _FakeGeneratedImage(len(inputs))

    async def fake_upload_image(*, stage_label: str, **_: Any) -> SimpleNamespace:
        return SimpleNamespace(gcs_uri=f"gs://generated/{stage_label}", signed_url="")

    def failing_load(_: ReferenceImageMetadata) -> None:
        raise RuntimeError("download failed")

    monkeypatch.setattr(
        gti,
        "_call_model",
        lambda inputs: fake_call_model(list(inputs)),
    )
    monkeypatch.setattr(
        gti,
        "_upload_image",
        lambda image, **kwargs: fake_upload_image(**kwargs),
    )
    monkeypatch.setattr(gti, "_load_reference_image", failing_load)

    result = await gti.generate_transformation_images(
        prompt_atual="Stage one",
        prompt_intermediario="Stage two",
        prompt_aspiracional="Stage three",
        variation_idx=2,
        metadata={"user_id": "user", "session_id": "session"},
        reference_character=reference_character,
        reference_product=None,
    )

    meta = result["meta"]
    assert meta["reference_character_id"] == "char-1"
    assert meta["reference_character_used"] is False
    assert "download failed" in meta["reference_character_error"]
