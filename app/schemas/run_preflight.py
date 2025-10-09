"""Schemas for validating the `/run_preflight` payload."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunPreflightMessagePart(BaseModel):
    """Represents a single Gemini chat part."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    text: str | None = None


class RunPreflightNewMessage(BaseModel):
    """Wrapper for the Gemini `newMessage` payload."""

    model_config = ConfigDict(extra="ignore")

    parts: list[RunPreflightMessagePart] = Field(default_factory=list)


class RunPreflightReferenceImagePayload(BaseModel):
    """Reference image information provided by the client."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: str | None = None
    user_description: str | None = Field(default=None, alias="user_description")

    @field_validator("id")
    @classmethod
    def _normalize_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("user_description")
    @classmethod
    def _normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class RunPreflightReferenceImages(BaseModel):
    """Top-level container for reference image inputs."""

    model_config = ConfigDict(extra="ignore")

    character: RunPreflightReferenceImagePayload | None = None
    product: RunPreflightReferenceImagePayload | None = None

    def to_payload_mapping(self) -> dict[str, dict[str, Any] | None]:
        payload: dict[str, dict[str, Any] | None] = {"character": None, "product": None}
        if self.character is not None:
            payload["character"] = self.character.model_dump(by_alias=True, exclude_none=True)
        if self.product is not None:
            payload["product"] = self.product.model_dump(by_alias=True, exclude_none=True)
        return payload


class RunPreflightRequest(BaseModel):
    """Validated request body for `/run_preflight`."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, str_strip_whitespace=True)

    text: str | None = None
    new_message: RunPreflightNewMessage | None = Field(default=None, alias="newMessage")
    reference_images: RunPreflightReferenceImages | None = None
    force_storybrand_fallback: Any | None = Field(default=None, alias="force_storybrand_fallback")

    def resolve_text(self) -> str | None:
        """Return the first non-empty text segment from the payload."""

        if self.text:
            return self.text

        if self.new_message:
            for part in self.new_message.parts:
                if part.text:
                    return part.text

        return None

    def reference_images_payload(self) -> dict[str, dict[str, Any] | None]:
        if self.reference_images is None:
            return {"character": None, "product": None}
        return self.reference_images.to_payload_mapping()

    def raw_payload(self) -> dict[str, Any]:
        """Return a dictionary representation keeping client field names."""

        return self.model_dump(by_alias=True, exclude_none=True)


__all__ = [
    "RunPreflightMessagePart",
    "RunPreflightNewMessage",
    "RunPreflightReferenceImagePayload",
    "RunPreflightReferenceImages",
    "RunPreflightRequest",
]
