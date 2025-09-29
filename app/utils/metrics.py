from __future__ import annotations

from typing import Mapping

from opentelemetry import metrics

_meter = metrics.get_meter("instagram_ads.storybrand")

_vertex_429_counter = _meter.create_counter(
    name="storybrand.vertex429.count",
    description="Count of Vertex AI RESOURCE_EXHAUSTED errors seen during StoryBrand extraction",
    unit="1",
)

_fallback_counter = _meter.create_counter(
    name="storybrand.fallback.triggered",
    description="Number of times the StoryBrand fallback pipeline was triggered",
    unit="1",
)

_delivery_failure_counter = _meter.create_counter(
    name="storybrand.delivery_failure.count",
    description="Number of StoryBrand delivery failures surfaced to the frontend",
    unit="1",
)


def _normalize_attributes(attributes: Mapping[str, str] | None = None) -> Mapping[str, str]:
    if not attributes:
        return {}
    return {str(key): str(value) for key, value in attributes.items()}


def record_vertex_429(attributes: Mapping[str, str] | None = None) -> None:
    _vertex_429_counter.add(1, _normalize_attributes(attributes))


def record_storybrand_fallback(reason: str) -> None:
    _fallback_counter.add(1, {"reason": reason})


def record_delivery_failure(reason: str) -> None:
    _delivery_failure_counter.add(1, {"reason": reason})
