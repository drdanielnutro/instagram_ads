"""Helpers for analyzing reference images using Google Cloud Vision."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Literal, Sequence

from google.api_core import exceptions as google_exceptions

try:
    from google.cloud import vision
except ImportError:  # pragma: no cover - handled at runtime when dependency missing
    vision = None  # type: ignore[assignment]

from app.schemas.reference_assets import ReferenceImageMetadata


logger = logging.getLogger(__name__)

SAFE_SEARCH_FIELDS: tuple[str, ...] = ("adult", "violence", "racy", "medical", "spoof")
BLOCKING_LEVELS: frozenset[str] = frozenset({"LIKELY", "VERY_LIKELY"})


class ReferenceImageAnalysisError(RuntimeError):
    """Generic Vision analysis failure."""


class ReferenceImageUnsafeError(ReferenceImageAnalysisError):
    """Raised when SafeSearch identifies disallowed content."""


def _likelihood_name(value: object) -> str:
    if hasattr(value, "name"):
        return str(getattr(value, "name"))
    if isinstance(value, int) and vision is not None:
        try:
            return vision.Likelihood(value).name  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - defensive
            return str(value)
    return str(value)


def _extract_labels(label_annotations: Sequence[object]) -> list[str]:
    labels: list[str] = []
    for annotation in label_annotations:
        description = getattr(annotation, "description", "")
        if description:
            labels.append(str(description))
        if len(labels) >= 10:
            break
    return labels


def _build_safe_search_flags(annotation: object) -> dict[str, str]:
    flags: dict[str, str] = {}
    for field in SAFE_SEARCH_FIELDS:
        value = getattr(annotation, field, None)
        if value is None:
            continue
        flags[field] = _likelihood_name(value)
    return flags


async def _call_vision(method: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    return await asyncio.to_thread(method, *args, **kwargs)


async def analyze_reference_image(
    *,
    image_bytes: bytes,
    reference_type: Literal["character", "product"],
    reference_id: str,
    gcs_uri: str,
    signed_url: str,
    uploaded_at: datetime | None = None,
    vision_client: "vision.ImageAnnotatorClient | None" = None,
) -> ReferenceImageMetadata:
    """Run SafeSearch and label detection for the uploaded reference image."""

    if not image_bytes:
        raise ReferenceImageAnalysisError("image_bytes payload is empty")

    if vision_client is None:
        if vision is None:
            raise ReferenceImageAnalysisError(
                "google-cloud-vision is not installed. Install google-cloud-vision>=3.4.0"
            )
        vision_client = vision.ImageAnnotatorClient()

    image = vision.Image(content=image_bytes)  # type: ignore[attr-defined]

    try:
        safe_search_response = await _call_vision(
            vision_client.safe_search_detection, image=image
        )
    except (
        google_exceptions.GoogleAPICallError
    ) as exc:  # pragma: no cover - network failure
        logger.error("Vision SafeSearch call failed for %s: %s", reference_id, exc)
        raise ReferenceImageAnalysisError("Vision SafeSearch detection failed") from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Vision SafeSearch unexpected error for %s: %s", reference_id, exc)
        raise ReferenceImageAnalysisError("Vision SafeSearch detection failed") from exc

    safe_annotation = getattr(safe_search_response, "safe_search_annotation", None)
    safe_flags = _build_safe_search_flags(safe_annotation) if safe_annotation else {}

    blocked = [
        category for category, flag in safe_flags.items() if flag in BLOCKING_LEVELS
    ]
    if blocked:
        logger.warning(
            "Reference image %s blocked by SafeSearch: %s", reference_id, blocked
        )
        raise ReferenceImageUnsafeError(
            f"SafeSearch blocked categories: {', '.join(blocked)}"
        )

    try:
        label_response = await _call_vision(vision_client.label_detection, image=image)
    except (
        google_exceptions.GoogleAPICallError
    ) as exc:  # pragma: no cover - network failure
        logger.error("Vision label detection failed for %s: %s", reference_id, exc)
        raise ReferenceImageAnalysisError("Vision label detection failed") from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "Vision label detection unexpected error for %s: %s", reference_id, exc
        )
        raise ReferenceImageAnalysisError("Vision label detection failed") from exc

    label_annotations: Iterable[object] = getattr(
        label_response, "label_annotations", []
    )
    labels = _extract_labels(tuple(label_annotations))

    metadata = ReferenceImageMetadata(
        id=reference_id,
        type=reference_type,
        gcs_uri=gcs_uri,
        signed_url=signed_url,
        labels=labels,
        safe_search_flags=safe_flags,
        uploaded_at=uploaded_at or datetime.now(timezone.utc),
    )

    logger.info(
        "Reference image %s analysed successfully with %d labels",
        reference_id,
        len(labels),
    )
    return metadata


__all__ = [
    "ReferenceImageAnalysisError",
    "ReferenceImageUnsafeError",
    "analyze_reference_image",
]
