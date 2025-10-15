"""Unit tests for final delivery schemas (AdVariationsPayload, StrictAdItem)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.final_delivery import AdVariationsPayload, StrictAdItem


def _make_variation(headline: str = "Test Headline") -> dict[str, object]:
    """Create a valid variation dict for testing."""
    return {
        "landing_page_url": "https://example.com",
        "formato": "Reels",
        "copy": {
            "headline": headline,
            "corpo": "Descubra uma nova forma de trabalhar.",
            "cta_texto": "Saiba mais",
        },
        "visual": {
            "descricao_imagem": "Pessoa utilizando aplicativo",
            "prompt_estado_atual": "customer looking frustrated",
            "prompt_estado_intermediario": "customer testing solution",
            "prompt_estado_aspiracional": "customer celebrating success",
            "aspect_ratio": "9:16",
        },
        "cta_instagram": "Saiba mais",
        "fluxo": "Instagram → Landing Page",
        "referencia_padroes": "StoryBrand",
        "contexto_landing": {"hero": "transformação digital"},
    }


def test_ad_variations_payload_accepts_exactly_3_variations():
    """AdVariationsPayload should accept exactly 3 variations."""
    variations = [
        _make_variation("Headline 1"),
        _make_variation("Headline 2"),
        _make_variation("Headline 3"),
    ]
    payload = AdVariationsPayload(variations=variations)
    assert len(payload.variations) == 3
    assert payload.variations[0].copy.headline == "Headline 1"


def test_ad_variations_payload_rejects_less_than_3():
    """AdVariationsPayload should reject less than 3 variations."""
    variations = [
        _make_variation("Headline 1"),
        _make_variation("Headline 2"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        AdVariationsPayload(variations=variations)

    error_msg = str(exc_info.value)
    assert "at least 3 items" in error_msg.lower() or "min_length" in error_msg.lower()


def test_ad_variations_payload_rejects_more_than_3():
    """AdVariationsPayload should reject more than 3 variations."""
    variations = [
        _make_variation("Headline 1"),
        _make_variation("Headline 2"),
        _make_variation("Headline 3"),
        _make_variation("Headline 4"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        AdVariationsPayload(variations=variations)

    error_msg = str(exc_info.value)
    assert "at most 3 items" in error_msg.lower() or "max_length" in error_msg.lower()


def test_strict_ad_item_validates_required_fields():
    """StrictAdItem should validate all required fields are present."""
    variation = _make_variation()
    item = StrictAdItem(**variation)

    assert item.landing_page_url == "https://example.com"
    assert item.formato == "Reels"
    assert item.copy.headline == "Test Headline"
    assert item.visual.aspect_ratio == "9:16"
    assert item.cta_instagram == "Saiba mais"


def test_strict_ad_item_rejects_invalid_cta():
    """StrictAdItem should reject invalid CTA values."""
    variation = _make_variation()
    variation["cta_instagram"] = "Invalid CTA"

    with pytest.raises(ValidationError) as exc_info:
        StrictAdItem(**variation)

    assert "cta_instagram" in str(exc_info.value).lower()


def test_strict_ad_item_rejects_invalid_format():
    """StrictAdItem should reject invalid formato values."""
    variation = _make_variation()
    variation["formato"] = "InvalidFormat"

    with pytest.raises(ValidationError) as exc_info:
        StrictAdItem(**variation)

    assert "formato" in str(exc_info.value).lower()


def test_strict_ad_item_normalizes_contexto_landing():
    """StrictAdItem should normalize contexto_landing to string if needed."""
    variation = _make_variation()
    variation["contexto_landing"] = {"key": "value"}

    item = StrictAdItem(**variation)
    # After normalization, should be dict (validator handles conversion)
    assert item.contexto_landing is not None


def test_strict_ad_visual_accepts_reference_assets():
    """StrictAdVisual should accept optional reference_assets field."""
    variation = _make_variation()
    variation["visual"]["reference_assets"] = {
        "character": {
            "id": "char-123",
            "type": "character",
            "gcs_uri": "gs://bucket/char.jpg",
            "labels": ["professional", "smiling"],
            "user_description": "Business professional",
        }
    }

    item = StrictAdItem(**variation)
    assert item.visual.reference_assets is not None
    assert "character" in item.visual.reference_assets


def test_strict_ad_visual_reference_assets_optional():
    """StrictAdVisual should work without reference_assets."""
    variation = _make_variation()
    # Ensure no reference_assets field
    if "reference_assets" in variation.get("visual", {}):
        del variation["visual"]["reference_assets"]

    item = StrictAdItem(**variation)
    assert item.visual.reference_assets is None
