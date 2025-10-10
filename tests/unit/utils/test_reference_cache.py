from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import pytest

from app.schemas.reference_assets import ReferenceImageMetadata
from app.utils import reference_cache


@pytest.fixture(autouse=True)
def _reset_cache_backend() -> Iterator[reference_cache.InMemoryReferenceMetadataCache]:
    original_backend = reference_cache._backend
    backend = reference_cache.InMemoryReferenceMetadataCache(ttl_seconds=5)
    reference_cache.configure_reference_cache(backend)
    try:
        yield backend
    finally:
        reference_cache.configure_reference_cache(original_backend)


def _make_metadata(reference_id: str, **overrides: object) -> ReferenceImageMetadata:
    payload: dict[str, object] = {
        "id": reference_id,
        "type": "character",
        "gcs_uri": f"gs://bucket/{reference_id}",
        "signed_url": f"https://signed/{reference_id}",
        "labels": ["hero", "confident"],
        "safe_search_flags": {"medical": "POSSIBLE"},
        "uploaded_at": datetime(2025, 1, 4, 12, tzinfo=timezone.utc),
        "user_description": "Cliente confiante",
    }
    payload.update(overrides)
    return ReferenceImageMetadata.model_validate(payload)


def test_cache_returns_deep_copy_and_respects_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata = _make_metadata("ref-1")

    times = iter([100.0, 104.0, 106.5, 110.0])

    def fake_monotonic() -> float:
        try:
            return next(times)
        except StopIteration:
            return 110.0

    monkeypatch.setattr(reference_cache.time, "monotonic", fake_monotonic)

    reference_cache.cache_reference_metadata(metadata)

    cached_before_expiry = reference_cache.resolve_reference_metadata("ref-1")
    assert cached_before_expiry is not None
    assert cached_before_expiry.id == metadata.id
    assert cached_before_expiry is not metadata

    cached_before_expiry.labels.append("joyful")
    assert "joyful" not in metadata.labels

    expired_entry = reference_cache.resolve_reference_metadata("ref-1")
    assert expired_entry is None

    # Subsequent lookups remain empty after expiration.
    assert reference_cache.resolve_reference_metadata("ref-1") is None


@pytest.mark.parametrize(
    "description,expected",
    [
        ("Cliente animado", "Cliente animado"),
        ("   ", "Cliente confiante"),
        (None, "Cliente confiante"),
    ],
)
def test_merge_user_description_prefers_user_input(description: str | None, expected: str | None) -> None:
    metadata = _make_metadata("ref-merge", user_description="Cliente confiante")

    merged = reference_cache.merge_user_description(metadata, description)
    assert merged is not None
    assert merged["id"] == "ref-merge"
    assert merged["user_description"] == expected


def test_merge_user_description_without_metadata() -> None:
    merged = reference_cache.merge_user_description(None, "Personagem sorridente")
    assert merged == {"user_description": "Personagem sorridente"}

    empty_result = reference_cache.merge_user_description(None, "   ")
    assert empty_result is None


def test_build_reference_summary_includes_safe_search_notes() -> None:
    reference_images = {
        "character": {
            "user_description": "Cliente confiante",
            "labels": ["hero", "smile"],
            "safe_search_flags": {"medical": "LIKELY", "adult": "VERY_UNLIKELY"},
        },
        "product": {
            "user_description": "Seringa sem agulha",
            "labels": ["clinic"],
            "safe_search_flags": {"violence": "UNLIKELY"},
        },
    }

    summary = reference_cache.build_reference_summary(reference_images, payload={})

    assert summary["character"] == "Cliente confiante | Labels: hero, smile"
    assert summary["product"] == "Seringa sem agulha | Labels: clinic"
    assert summary["safe_search_notes"] == "character: medical=LIKELY"


def test_purge_expired_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = reference_cache.InMemoryReferenceMetadataCache(ttl_seconds=5)
    metadata = _make_metadata("ref-purge")

    sequence = iter([50.0, 70.0, 80.0])

    def fake_monotonic() -> float:
        try:
            return next(sequence)
        except StopIteration:
            return 80.0

    monkeypatch.setattr(reference_cache.time, "monotonic", fake_monotonic)

    backend.set(metadata)
    backend.purge_expired()
    # The entry expires because the purge occurs after TTL.
    assert backend.get(metadata.id) is None
