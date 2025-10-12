from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.agent import ImageAssetsAgent
from app.schemas.reference_assets import ReferenceImageMetadata


@pytest.mark.asyncio
async def test_image_assets_agent_rehydrates_references_and_tracks_emotions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference_payload = {
        "character": {
            "id": "char-11",
            "type": "character",
            "gcs_uri": "gs://bucket/char-11",
            "signed_url": "https://signed/char-11",
            "labels": ["hero", "smile"],
            "safe_search_flags": {"medical": "LIKELY"},
            "user_description": "Cliente animado",
            "uploaded_at": "2025-03-05T12:00:00+00:00",
        },
        "product": {
            "id": "prod-7",
            "type": "product",
            "gcs_uri": "gs://bucket/prod-7",
            "signed_url": "https://signed/prod-7",
            "labels": ["serum"],
            "safe_search_flags": {},
            "user_description": "Sérum revitalizante",
            "uploaded_at": "2025-03-05T12:05:00+00:00",
        },
    }

    variations = [
        {
            "formato": "Reels",
            "visual": {
                "aspect_ratio": "9:16",
                "prompt_estado_atual": "Cena 1 | Emotion: Calm",
                "prompt_estado_intermediario": "Cena 2 | emotion: determined",
                "prompt_estado_aspiracional": "Cena 3 | EMOTION: Joyful",
            },
        }
    ]

    state: dict[str, Any] = {
        "final_code_delivery": json.dumps(variations, ensure_ascii=False),
        "reference_images": reference_payload,
        "reference_image_character_summary": "Cliente animado",
        "reference_image_product_summary": "Sérum revitalizante",
        "reference_image_safe_search_notes": "character: medical=LIKELY",
        "user_id": "user-9",
    }

    async def fake_generate_transformation_images(**kwargs: Any) -> dict[str, Any]:
        assert isinstance(kwargs["reference_character"], ReferenceImageMetadata)
        assert isinstance(kwargs["reference_product"], ReferenceImageMetadata)
        await asyncio.sleep(0)
        return {
            "estado_atual": {"gcs_uri": "gs://generated/one", "signed_url": "https://cdn/one"},
            "estado_intermediario": {
                "gcs_uri": "gs://generated/two",
                "signed_url": "https://cdn/two",
            },
            "estado_aspiracional": {
                "gcs_uri": "gs://generated/three",
                "signed_url": "https://cdn/three",
            },
            "meta": {
                "variation_idx": kwargs["variation_idx"],
                "reference_character_id": "char-11",
                "reference_product_id": "prod-7",
                "reference_character_used": True,
                "reference_product_used": True,
            },
        }

    persist_calls: list[Any] = []
    monkeypatch.setattr("app.agent.generate_transformation_images", fake_generate_transformation_images)
    monkeypatch.setattr("app.agent.persist_final_delivery", lambda ctx: persist_calls.append(ctx))
    monkeypatch.setattr(
        "app.agent.config.enable_deterministic_final_validation",
        True,
        raising=False,
    )

    session = SimpleNamespace(id="sess-22", state=state)
    ctx = SimpleNamespace(session=session)

    agent = ImageAssetsAgent()
    async for _ in agent._run_async_impl(ctx):
        pass

    assert state["character_reference_used"] is True
    assert state["product_reference_used"] is True
    assert state["image_assets_review"]["grade"] == "pass"

    summary = state["image_assets"][0]
    assert summary["character_reference_used"] is True
    assert summary["product_reference_used"] is True
    assert summary["emotions"] == {
        "prompt_estado_atual": "Calm",
        "prompt_estado_intermediario": "determined",
        "prompt_estado_aspiracional": "Joyful",
    }
    assert summary["safe_search_notes"] == "character: medical=LIKELY"

    parsed_delivery = json.loads(state["final_code_delivery"])
    visual = parsed_delivery[0]["visual"]
    assert visual["reference_assets"]["character"]["id"] == "char-11"
    assert visual["reference_assets"]["product"]["labels"] == ["serum"]
    assert visual["image_generation_meta"]["reference_character_used"] is True

    # FIX VALIDATION: Verificar se URLs de imagens foram adicionadas
    assert visual["image_estado_atual_url"] == "https://cdn/one"
    assert visual["image_estado_intermediario_url"] == "https://cdn/two"
    assert visual["image_estado_aspiracional_url"] == "https://cdn/three"
    assert visual["image_estado_atual_gcs"] == "gs://generated/one"
    assert visual["image_estado_intermediario_gcs"] == "gs://generated/two"
    assert visual["image_estado_aspiracional_gcs"] == "gs://generated/three"

    # `persist_final_delivery` is skipped because deterministic validation is enabled.
    assert persist_calls == []


@pytest.mark.asyncio
async def test_image_assets_agent_updates_normalized_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that ImageAssetsAgent updates deterministic_final_validation.normalized_payload with image URLs."""

    variations = [
        {
            "formato": "Feed",
            "visual": {
                "aspect_ratio": "4:5",
                "prompt_estado_atual": "Test | Emotion: sad",
                "prompt_estado_intermediario": "Test | Emotion: hopeful",
                "prompt_estado_aspiracional": "Test | Emotion: happy",
            },
        }
    ]

    # Simula que o validador determinístico já rodou e criou normalized_payload
    normalized_payload = {
        "variations": [
            {
                "formato": "Feed",
                "visual": {
                    "aspect_ratio": "4:5",
                    "prompt_estado_atual": "Test | Emotion: sad",
                    "prompt_estado_intermediario": "Test | Emotion: hopeful",
                    "prompt_estado_aspiracional": "Test | Emotion: happy",
                },
            }
        ]
    }

    state: dict[str, Any] = {
        "final_code_delivery": json.dumps(variations, ensure_ascii=False),
        "deterministic_final_validation": {
            "grade": "pass",
            "normalized_payload": normalized_payload,
        },
        "user_id": "test-user",
    }

    async def fake_generate(**kwargs: Any) -> dict[str, Any]:
        await asyncio.sleep(0)
        return {
            "estado_atual": {"gcs_uri": "gs://test/1", "signed_url": "https://test/1"},
            "estado_intermediario": {"gcs_uri": "gs://test/2", "signed_url": "https://test/2"},
            "estado_aspiracional": {"gcs_uri": "gs://test/3", "signed_url": "https://test/3"},
            "meta": {"variation_idx": kwargs["variation_idx"]},
        }

    monkeypatch.setattr("app.agent.generate_transformation_images", fake_generate)
    monkeypatch.setattr("app.agent.persist_final_delivery", lambda ctx: None)
    monkeypatch.setattr("app.agent.config.enable_deterministic_final_validation", True, raising=False)

    session = SimpleNamespace(id="test-session", state=state)
    ctx = SimpleNamespace(session=session)

    agent = ImageAssetsAgent()
    async for _ in agent._run_async_impl(ctx):
        pass

    # CRITICAL: Verifica que normalized_payload foi atualizado com URLs
    updated_normalized = state["deterministic_final_validation"]["normalized_payload"]
    assert isinstance(updated_normalized, dict)
    assert isinstance(updated_normalized["variations"], list)

    updated_visual = updated_normalized["variations"][0]["visual"]
    assert updated_visual["image_estado_atual_url"] == "https://test/1"
    assert updated_visual["image_estado_intermediario_url"] == "https://test/2"
    assert updated_visual["image_estado_aspiracional_url"] == "https://test/3"
    assert updated_visual["image_estado_atual_gcs"] == "gs://test/1"
    assert updated_visual["image_estado_intermediario_gcs"] == "gs://test/2"
    assert updated_visual["image_estado_aspiracional_gcs"] == "gs://test/3"

    # Verifica que final_code_delivery_parsed também foi atualizado
    assert state["final_code_delivery_parsed"] == updated_normalized["variations"]
