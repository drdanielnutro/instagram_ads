from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.callbacks.persist_outputs import persist_final_delivery


@pytest.mark.usefixtures("tmp_path")
def test_persist_final_delivery_normalizes_and_updates_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DELIVERIES_BUCKET", "")

    normalized_payload = {
        "variations": [
            {
                "landing_page_url": "https://example.com",
                "formato": "Feed",
                "cta_instagram": "Saiba mais",
                "fluxo": "Instagram → Landing Page",
                "referencia_padroes": "StoryBrand",
                "contexto_landing": {"hero": "Consultas"},
                "copy": {
                    "headline": "Agende sua consulta",
                    "corpo": "Use nosso app para reservar em minutos.",
                    "cta_texto": "Saiba mais",
                },
                "visual": {
                    "descricao_imagem": "Pessoa usando smartphone",
                    "prompt_estado_atual": "cliente procurando opções",
                    "prompt_estado_intermediario": "cliente comparando planos",
                    "prompt_estado_aspiracional": "cliente satisfeito",
                    "aspect_ratio": "4:5",
                },
            }
        ]
    }

    state = {
        "final_code_delivery": json.dumps(normalized_payload["variations"], ensure_ascii=False),
        "deterministic_final_validation": {
            "grade": "pass",
            "normalized_payload": normalized_payload,
        },
        "semantic_visual_review": {"grade": "pass"},
        "image_assets_review": {"grade": "skipped"},
        "delivery_audit_trail": [
            {"stage": "final_assembly_normalizer", "status": "pending"},
            {"stage": "final_delivery_validator", "status": "pass"},
        ],
        "storybrand_audit_trail": [
            {"stage": "storybrand_analysis", "status": "done"}
        ],
        "storybrand_gate_metrics": {"decision_path": "happy_path"},
        "storybrand_fallback_meta": {},
        "reference_images": {
            "character": {
                "id": "ref-123",
                "type": "character",
                "gcs_uri": "gs://bucket/reference-images/ref-123",
                "signed_url": "https://signed.example/ref-123",
                "labels": ["model", "fashion"],
                "safe_search_flags": {"adult": "VERY_UNLIKELY"},
                "user_description": "Modelo com jaqueta vermelha",
                "uploaded_at": "2025-03-01T12:00:00+00:00",
                "raw_annotations": {"safe_search": {"adult": "VERY_UNLIKELY"}},
                "access_token": "secret-token",
            }
        },
    }

    session = SimpleNamespace(id="sess-1", user_id="user-9", state=state)
    callback_context = SimpleNamespace(session=session, state=state)

    persist_final_delivery(callback_context)

    local_path = Path(state["final_delivery_local_path"])
    assert local_path.exists()
    assert local_path.parent.parent.name == "artifacts"

    parsed = state["final_code_delivery_parsed"]
    assert isinstance(parsed, list) and parsed
    assert parsed[0]["contexto_landing"] == {"hero": "Consultas"}

    reserialized = json.loads(state["final_code_delivery"])
    assert isinstance(reserialized, list)

    status = state["final_delivery_status"]
    assert status["stage"] == "deterministic_final_validation"
    assert status["grade"] == "pass"
    assert status["storybrand_audit_trail"]
    assert state["image_assets_review"]["grade"] == "skipped"

    meta_path = Path("artifacts/ads_final/meta/sess-1.json")
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["image_assets_review"]["grade"] == "skipped"
    assert meta["reference_images_present"] is True
    reference_meta = meta["reference_images"]["character"]
    assert reference_meta["id"] == "ref-123"
    assert "signed_url" not in reference_meta
    assert "raw_annotations" not in reference_meta
    assert "access_token" not in reference_meta
    assert reference_meta["signed_url_ttl_seconds"] == 60 * 60 * 24
    assert reference_meta["signed_url_expires_at"] == "2025-03-02T12:00:00+00:00"

    status_reference = state["final_delivery_status"]["reference_images"]["character"]
    assert status_reference == reference_meta

