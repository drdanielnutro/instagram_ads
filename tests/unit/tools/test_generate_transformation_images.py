"""Unit tests for generate_transformation_images tool."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from importlib import import_module
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

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
    first_prompt = prompts[0]["prompt"]
    assert "Gerar a IMAGEM DO ESTADO ATUAL" in first_prompt
    assert "Use a imagem compartilhada do personagem" in first_prompt
    assert "destaque Tênis vermelho premium" in first_prompt
    assert prompts[0]["inputs"] == ["char-1", "prod-9"]

    second_prompt = prompts[1]["prompt"]
    assert "IMAGEM DO ESTADO INTERMEDIÁRIO" in second_prompt
    assert "over-the-shoulder" in second_prompt
    assert "Use como referência a IMAGEM COMPARTILHADA do estado atual" in second_prompt
    assert "Considere também a imagem compartilhada do personagem" in second_prompt
    assert "Utilize a imagem compartilhada do produto/serviço" in second_prompt
    assert prompts[1]["inputs"] == [1, "char-1", "prod-9"]

    third_prompt = prompts[2]["prompt"]
    assert "IMAGEM DO ESTADO ASPIRACIONAL" in third_prompt
    assert "Use SOMENTE a IMAGEM ORIGINAL DO PERSONAGEM" in third_prompt
    assert "Incorpore visualmente a IMAGEM DO PRODUTO/SERVIÇO" in third_prompt
    assert "Não utilize imagens geradas anteriormente" in third_prompt
    assert prompts[2]["inputs"] == ["prod-9", "char-1"]
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

    assert "Gerar a IMAGEM DO ESTADO ATUAL" in prompts[0]
    assert "destaque Tênis vermelho premium" in prompts[0]
    assert "IMAGEM DO ESTADO ASPIRACIONAL" in prompts[2]
    assert "Incorpore visualmente a IMAGEM DO PRODUTO/SERVIÇO" in prompts[2]
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


@pytest.mark.asyncio
async def test_generate_transformation_images_debug_logs(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="app.tools.generate_transformation_images")

    async def fake_call_model(inputs: list[Any]) -> Image.Image:
        # Always return a fresh image so subsequent stages receive a PIL.Image object
        return Image.new("RGB", (12, 18), color=(128, 64, 32))

    async def fake_upload_image(*, stage_label: str, **_: Any) -> SimpleNamespace:
        return SimpleNamespace(gcs_uri=f"gs://generated/{stage_label}", signed_url="")

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

    prompt_estado_atual = (
        "The same persona from the approved references stands beside a lake under overcast skies, "
        "wearing worn fishing gear and holding a damaged life vest with visible tears. Emotion: despair."
    )
    prompt_estado_intermediario = (
        "The same persona now checks an online store on a tablet showing a highlighted new life vest. "
        "Lighting becomes brighter to suggest hope. Emotion: determined."
    )
    prompt_estado_aspiracional = (
        "The same persona fishes from a boat wearing the new MG Pesca life vest, smiling while the sun shines "
        "over calm waters. Emotion: joyful."
    )

    await gti.generate_transformation_images(
        prompt_atual=prompt_estado_atual,
        prompt_intermediario=prompt_estado_intermediario,
        prompt_aspiracional=prompt_estado_aspiracional,
        variation_idx=7,
        metadata={"user_id": "u-test", "session_id": "sess-test"},
        reference_character=None,
        reference_product=None,
    )

    debug_messages = [
        message for message in caplog.messages if "generate_content inputs" in message
    ]
    assert len(debug_messages) == 3
    assert "estado_atual" in debug_messages[0]
    assert "estado_intermediario" in debug_messages[1]
    assert "estado_aspiracional" in debug_messages[2]

    def parse_payload(message: str) -> list[dict[str, Any]]:
        _, payload = message.split(": ", 1)
        return json.loads(payload)

    first_payload = parse_payload(debug_messages[0])
    assert len(first_payload) == 1
    assert first_payload[0]["type"] == "text"
    assert first_payload[0]["length"] == len(prompt_estado_atual)
    assert first_payload[0]["preview"].startswith("The same persona from the approved references")

    second_payload = parse_payload(debug_messages[1])
    assert len(second_payload) == 2
    assert second_payload[0]["type"] == "image"
    assert second_payload[1]["type"] == "text"
    assert "The same persona now checks an online store" in second_payload[1]["preview"]

    third_payload = parse_payload(debug_messages[2])
    assert len(third_payload) == 2
    assert third_payload[0]["type"] == "image"
    assert third_payload[1]["type"] == "text"
    assert "The same persona fishes from a boat" in third_payload[1]["preview"]
