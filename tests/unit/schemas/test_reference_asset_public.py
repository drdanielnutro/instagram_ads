"""Unit tests for ReferenceAssetPublic schema."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.reference_assets import ReferenceAssetPublic, ReferenceImageMetadata


def test_reference_asset_public_creation():
    """ReferenceAssetPublic should create successfully with valid fields."""
    asset = ReferenceAssetPublic(
        id="asset-123",
        type="character",
        gcs_uri="gs://bucket/image.jpg",
        labels=["professional", "smiling"],
        user_description="Business professional in suit",
    )

    assert asset.id == "asset-123"
    assert asset.type == "character"
    assert asset.gcs_uri == "gs://bucket/image.jpg"
    assert asset.labels == ["professional", "smiling"]
    assert asset.user_description == "Business professional in suit"


def test_reference_asset_public_no_signed_url_field():
    """ReferenceAssetPublic should not have signed_url field."""
    asset = ReferenceAssetPublic(
        id="asset-123",
        type="product",
        gcs_uri="gs://bucket/product.jpg",
        labels=["tech", "gadget"],
    )

    # Verify signed_url is not in the model
    assert not hasattr(asset, "signed_url")
    dumped = asset.model_dump()
    assert "signed_url" not in dumped


def test_from_metadata_conversion():
    """from_metadata should convert ReferenceImageMetadata to ReferenceAssetPublic."""
    metadata = ReferenceImageMetadata(
        id="meta-456",
        type="character",
        gcs_uri="gs://bucket/char.jpg",
        signed_url="https://signed.url/char.jpg?expires=123",
        labels=["young", "energetic"],
        safe_search_flags={"adult": "VERY_UNLIKELY"},
        user_description="Energetic young professional",
        uploaded_at=datetime.now(timezone.utc),
    )

    public_asset = ReferenceAssetPublic.from_metadata(metadata)

    assert public_asset.id == "meta-456"
    assert public_asset.type == "character"
    assert public_asset.gcs_uri == "gs://bucket/char.jpg"
    assert public_asset.labels == ["young", "energetic"]
    assert public_asset.user_description == "Energetic young professional"
    # Verify signed_url was NOT copied
    assert not hasattr(public_asset, "signed_url")


def test_from_metadata_removes_signed_url():
    """from_metadata should not expose signed_url in the public asset."""
    metadata = ReferenceImageMetadata(
        id="secure-789",
        type="product",
        gcs_uri="gs://bucket/product.jpg",
        signed_url="https://should-not-be-exposed.com/secret",
        labels=["premium"],
        uploaded_at=datetime.now(timezone.utc),
    )

    public_asset = ReferenceAssetPublic.from_metadata(metadata)
    dumped = public_asset.model_dump()

    assert "signed_url" not in dumped
    assert dumped["gcs_uri"] == "gs://bucket/product.jpg"


def test_reference_asset_public_optional_fields():
    """ReferenceAssetPublic should work with optional fields (labels, user_description)."""
    asset = ReferenceAssetPublic(
        id="minimal-asset",
        type="product",
        gcs_uri="gs://bucket/minimal.jpg",
    )

    assert asset.labels == []
    assert asset.user_description is None


def test_reference_asset_public_forbids_extra_fields():
    """ReferenceAssetPublic should forbid extra fields (extra='forbid')."""
    with pytest.raises(ValidationError) as exc_info:
        ReferenceAssetPublic(
            id="asset-extra",
            type="character",
            gcs_uri="gs://bucket/test.jpg",
            extra_field="should_fail",
        )

    assert "extra_field" in str(exc_info.value).lower()


def test_reference_asset_public_requires_valid_type():
    """ReferenceAssetPublic should only accept 'character' or 'product' as type."""
    with pytest.raises(ValidationError) as exc_info:
        ReferenceAssetPublic(
            id="invalid-type",
            type="invalid",
            gcs_uri="gs://bucket/test.jpg",
        )

    error_msg = str(exc_info.value).lower()
    assert "type" in error_msg


def test_from_metadata_preserves_all_public_fields():
    """from_metadata should preserve all fields except private ones."""
    metadata = ReferenceImageMetadata(
        id="complete-meta",
        type="character",
        gcs_uri="gs://bucket/complete.jpg",
        signed_url="https://private.url",
        labels=["label1", "label2", "label3"],
        safe_search_flags={"adult": "UNLIKELY", "violence": "VERY_UNLIKELY"},
        user_description="Complete metadata description",
        uploaded_at=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
    )

    public_asset = ReferenceAssetPublic.from_metadata(metadata)

    assert public_asset.id == metadata.id
    assert public_asset.type == metadata.type
    assert public_asset.gcs_uri == metadata.gcs_uri
    assert public_asset.labels == metadata.labels
    assert public_asset.user_description == metadata.user_description
    # These should NOT be present
    assert not hasattr(public_asset, "signed_url")
    assert not hasattr(public_asset, "safe_search_flags")
    assert not hasattr(public_asset, "uploaded_at")
