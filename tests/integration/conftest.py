"""Shared fixtures for integration tests."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient

from app.schemas.reference_assets import ReferenceImageMetadata
from app.utils import reference_cache


@pytest.fixture()
def reference_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, ReferenceImageMetadata]]:
    import google.auth

    def _fake_default(**kwargs: Any) -> tuple[SimpleNamespace, str]:
        return SimpleNamespace(), "test-project"

    monkeypatch.setattr(google.auth, "default", _fake_default)

    import app.server as server

    monkeypatch.setattr(server.config, "enable_reference_images", True)
    monkeypatch.setattr(server.config, "enable_new_input_fields", True)
    monkeypatch.setattr(server.config, "enable_storybrand_fallback", True)

    backend = reference_cache.InMemoryReferenceMetadataCache(ttl_seconds=3600)
    original_backend = reference_cache._backend
    reference_cache.configure_reference_cache(backend)

    metadata = ReferenceImageMetadata(
        id="ref-123",
        type="character",
        gcs_uri="gs://bucket/ref-123",
        signed_url="https://signed/ref-123",
        labels=["person", "portrait", "smile"],
        safe_search_flags={"adult": "VERY_UNLIKELY", "medical": "LIKELY"},
        user_description=None,
        uploaded_at=datetime(2025, 1, 10, 15, 0, tzinfo=timezone.utc),
    )

    async def fake_upload_reference_image_to_gcs(**_: Any) -> ReferenceImageMetadata:
        return metadata

    def fake_extract_user_input(_: str) -> dict[str, Any]:
        return {
            "success": True,
            "data": {
                "landing_page_url": "https://example.com",
                "objetivo_final": "agendamentos",
                "perfil_cliente": "profissionais",
                "formato_anuncio": "Reels",
                "nome_empresa": "Clinica",
                "o_que_a_empresa_faz": "Consultas",
                "sexo_cliente_alvo": "feminino",
            },
            "normalized": {
                "formato_anuncio_norm": "Reels",
                "objetivo_final_norm": "agendamentos",
                "sexo_cliente_alvo_norm": "feminino",
            },
            "errors": [],
        }

    monkeypatch.setattr(server, "upload_reference_image_to_gcs", fake_upload_reference_image_to_gcs)
    monkeypatch.setattr(server, "extract_user_input", fake_extract_user_input)
    monkeypatch.setattr(
        server,
        "get_plan_by_format",
        lambda _fmt: {
            "id": "plan",
            "feature_name": "reference_images",
            "implementation_tasks": [{"category": "qa"}],
        },
    )
    monkeypatch.setattr(
        server,
        "get_specs_by_format",
        lambda _fmt: {"id": "specs", "feature_name": "reference_images"},
    )
    monkeypatch.setattr(
        server,
        "get_specs_json_by_format",
        lambda _fmt: {"id": "json"},
    )

    client = TestClient(server.app)
    try:
        yield client, metadata
    finally:
        reference_cache.configure_reference_cache(original_backend)
