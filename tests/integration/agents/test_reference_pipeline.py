"""Integration tests for the reference image pipeline within ImageAssetsAgent."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.agent import ImageAssetsAgent
from app.schemas.reference_assets import ReferenceImageMetadata


@pytest.mark.asyncio
async def test_agent_consumes_preflight_reference_state(reference_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, metadata = reference_client

    upload_response = client.post(
        "/upload/reference-image",
        files={"file": ("ref.png", b"img", "image/png")},
        data={"type": "character"},
    )
    assert upload_response.status_code == 200

    preflight_response = client.post(
        "/run_preflight",
        json={
            "text": "Criar anúncios",
            "reference_images": {
                "character": {"id": metadata.id, "user_description": "Cliente sorridente"}
            },
        },
    )
    assert preflight_response.status_code == 200
    initial_state = preflight_response.json()["initial_state"]

    variations = [
        {
            "formato": "Reels",
            "visual": {
                "prompt_estado_atual": "Emotion: Calm | Stage 1",
                "prompt_estado_intermediario": "Emotion: Hopeful | Stage 2",
                "prompt_estado_aspiracional": "Emotion: Triumphant | Stage 3",
                "aspect_ratio": "4:5",
            },
        }
    ]

    state: dict[str, Any] = {
        **initial_state,
        "final_code_delivery": json.dumps(variations),
        "user_id": "user-77",
    }

    async def fake_generate(**kwargs: Any) -> dict[str, Any]:
        reference_character: ReferenceImageMetadata | None = kwargs.get("reference_character")
        assert reference_character is not None
        assert reference_character.id == metadata.id
        assert kwargs["metadata"]["character_summary"] == initial_state["reference_image_character_summary"]
        await asyncio.sleep(0)
        return {
            "estado_atual": {"gcs_uri": "gs://generated/one", "signed_url": ""},
            "estado_intermediario": {"gcs_uri": "gs://generated/two", "signed_url": ""},
            "estado_aspiracional": {"gcs_uri": "gs://generated/three", "signed_url": ""},
            "meta": {
                "variation_idx": kwargs["variation_idx"],
                "reference_character_id": reference_character.id,
                "reference_character_used": True,
                "reference_product_used": False,
            },
        }

    monkeypatch.setattr("app.agent.generate_transformation_images", fake_generate)
    monkeypatch.setattr("app.agent.persist_final_delivery", lambda ctx: None)

    ctx = SimpleNamespace(session=SimpleNamespace(id="sess-int", state=state))
    agent = ImageAssetsAgent()
    async for _ in agent._run_async_impl(ctx):
        pass

    review = state["image_assets_review"]
    assert review["grade"] == "pass"
    summary = state["image_assets"][0]
    assert summary["character_reference_used"] is True
    assert summary["product_reference_used"] is False
    assert "medical=LIKELY" in (summary.get("safe_search_notes") or "")
    visual_state = json.loads(state["final_code_delivery"])[0]["visual"]
    assert visual_state["reference_assets"]["character"]["user_description"] == "Cliente sorridente"
    assert visual_state["image_generation_meta"]["reference_character_used"] is True
