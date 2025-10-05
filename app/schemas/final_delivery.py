"""Strict schemas for final ad delivery payloads."""

from __future__ import annotations

import json
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import CTA_INSTAGRAM_CHOICES
from app.format_specifications import FORMAT_SPECS


def _collect_aspect_ratios(specs: Iterable[dict[str, Any]]) -> set[str]:
    ratios: set[str] = set()
    for spec in specs:
        visual = spec.get("visual", {})
        ratio = visual.get("aspect_ratio")
        if isinstance(ratio, str):
            ratios.add(ratio)
        permitted = visual.get("permitidos")
        if isinstance(permitted, (list, tuple, set)):
            ratios.update({r for r in permitted if isinstance(r, str)})
    return ratios


ALLOWED_FORMATS: tuple[str, ...] = tuple(sorted(FORMAT_SPECS.keys()))
ALLOWED_ASPECT_RATIOS: tuple[str, ...] = tuple(sorted(_collect_aspect_ratios(FORMAT_SPECS.values())))
HEADLINE_LIMIT_BY_FORMAT: dict[str, int] = {
    fmt: spec.get("copy", {}).get("headline_max_chars", 60) for fmt, spec in FORMAT_SPECS.items()
}
MAX_HEADLINE_LENGTH: int = max(HEADLINE_LIMIT_BY_FORMAT.values() or [60])


class StrictBaseModel(BaseModel):
    """Base configuration shared by strict models."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StrictAdCopy(StrictBaseModel):
    """Strict representation of ad copy content."""

    headline: str = Field(..., min_length=1, max_length=MAX_HEADLINE_LENGTH)
    corpo: str = Field(..., min_length=1)
    cta_texto: str = Field(..., min_length=1)

    @field_validator("cta_texto")
    @classmethod
    def validate_cta_texto(cls, value: str) -> str:
        if value not in CTA_INSTAGRAM_CHOICES:
            raise ValueError(f"cta_texto must be one of {CTA_INSTAGRAM_CHOICES}")
        return value


class StrictAdVisual(StrictBaseModel):
    """Strict representation of visual prompts for an ad variation."""

    descricao_imagem: str = Field(..., min_length=1)
    prompt_estado_atual: str = Field(..., min_length=1)
    prompt_estado_intermediario: str = Field(..., min_length=1)
    prompt_estado_aspiracional: str = Field(..., min_length=1)
    aspect_ratio: str

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        if value not in ALLOWED_ASPECT_RATIOS:
            raise ValueError(f"aspect_ratio must be one of {ALLOWED_ASPECT_RATIOS}")
        return value


class StrictAdItem(StrictBaseModel):
    """Strict schema for a final ad variation."""

    landing_page_url: str = Field(..., min_length=1)
    formato: str
    copy: StrictAdCopy
    visual: StrictAdVisual
    cta_instagram: str = Field(..., min_length=1)
    fluxo: str = Field(..., min_length=1)
    referencia_padroes: str = Field(..., min_length=1)
    contexto_landing: str | dict[str, Any] | None = Field(default=None)

    @field_validator("formato")
    @classmethod
    def validate_formato(cls, value: str) -> str:
        if value not in ALLOWED_FORMATS:
            raise ValueError(f"formato must be one of {ALLOWED_FORMATS}")
        return value

    @field_validator("cta_instagram")
    @classmethod
    def validate_cta_instagram(cls, value: str) -> str:
        if value not in CTA_INSTAGRAM_CHOICES:
            raise ValueError(f"cta_instagram must be one of {CTA_INSTAGRAM_CHOICES}")
        return value

    @field_validator("contexto_landing", mode="before")
    @classmethod
    def normalize_contexto_landing(cls, value: Any) -> str | dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return ""
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return stripped
            if isinstance(parsed, dict):
                return parsed
            return stripped
        raise TypeError("contexto_landing must be a string or dict")

    @model_validator(mode="after")
    def validate_with_format_specs(self) -> "StrictAdItem":
        specs = FORMAT_SPECS.get(self.formato, {})
        copy_specs = specs.get("copy", {})
        max_chars = copy_specs.get("headline_max_chars")
        if isinstance(max_chars, int) and max_chars > 0:
            if len(self.copy.headline) > max_chars:
                raise ValueError(
                    f"headline length {len(self.copy.headline)} exceeds limit {max_chars} for formato {self.formato}"
                )

        visual_specs = specs.get("visual", {})
        allowed_ratios: set[str] = set()
        ratio = visual_specs.get("aspect_ratio")
        if isinstance(ratio, str):
            allowed_ratios.add(ratio)
        permitted = visual_specs.get("permitidos")
        if isinstance(permitted, (list, tuple, set)):
            allowed_ratios.update({r for r in permitted if isinstance(r, str)})
        if allowed_ratios and self.visual.aspect_ratio not in allowed_ratios:
            raise ValueError(
                f"aspect_ratio {self.visual.aspect_ratio} not allowed for formato {self.formato}: {sorted(allowed_ratios)}"
            )
        return self

    def canonical_dict(self) -> dict[str, Any]:
        """Dump the variation ensuring contexto_landing follows the supported types."""

        data = self.model_dump(mode="python")
        contexto = data.get("contexto_landing")
        if contexto is None:
            data["contexto_landing"] = ""
        return data

    @classmethod
    def from_state(cls, state: dict[str, Any], **variation: Any) -> "StrictAdItem":
        """Build a variation merging state defaults with variation payload."""

        base_context = state.get("contexto_landing")
        context_value = variation.get("contexto_landing", base_context)
        payload = {
            "landing_page_url": variation.get("landing_page_url") or state.get("landing_page_url"),
            "formato": variation.get("formato") or state.get("formato_anuncio"),
            "copy": variation.get("copy"),
            "visual": variation.get("visual"),
            "cta_instagram": variation.get("cta_instagram") or variation.get("copy", {}).get("cta_texto"),
            "fluxo": variation.get("fluxo") or state.get("fluxo") or state.get("fluxo_padrao"),
            "referencia_padroes": variation.get("referencia_padroes") or state.get("referencia_padroes"),
            "contexto_landing": context_value,
        }
        filtered_payload = {
            key: value
            for key, value in payload.items()
            if value is not None or key == "contexto_landing"
        }
        return cls(**filtered_payload)


def model_dump(variations: Iterable[StrictAdItem]) -> dict[str, Any]:
    """Dump a list of validated variations into canonical structure."""

    return {"variations": [variation.canonical_dict() for variation in variations]}

