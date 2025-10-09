"""Schemas for handling reference image metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReferenceImageMetadata(BaseModel):
    """Metadata captured for an uploaded reference image."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(..., min_length=1)
    type: Literal["character", "product"]
    gcs_uri: str = Field(..., min_length=1)
    signed_url: str = Field(..., min_length=1)
    labels: list[str] = Field(default_factory=list)
    safe_search_flags: dict[str, str] = Field(default_factory=dict)
    user_description: str | None = None
    uploaded_at: datetime

    @field_validator("labels", mode="before")
    @classmethod
    def _normalize_labels(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            cleaned = [item for item in value if isinstance(item, str) and item.strip()]
            return list(dict.fromkeys(cleaned))
        raise TypeError("labels must be a sequence of strings")

    @field_validator("safe_search_flags", mode="before")
    @classmethod
    def _normalize_safe_search_flags(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if isinstance(value, dict):
            normalized: dict[str, str] = {}
            for key, flag in value.items():
                if isinstance(key, str) and isinstance(flag, str):
                    normalized[key] = flag
            return normalized
        raise TypeError(
            "safe_search_flags must be a mapping of string keys to string values"
        )

    @field_validator("user_description", mode="before")
    @classmethod
    def _normalize_description(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        raise TypeError("user_description must be a string or None")

    @field_validator("uploaded_at", mode="before")
    @classmethod
    def _ensure_timezone(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        raise TypeError("uploaded_at must be a datetime or ISO formatted string")

    def model_dump(self, *, mode: str = "json", **kwargs: Any) -> dict[str, Any]:
        """Dump the model ensuring JSON compatibility by default."""

        return super().model_dump(mode=mode, **kwargs)

    def to_state_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary suited for session state usage."""

        return self.model_dump(mode="json")


__all__ = ["ReferenceImageMetadata"]
