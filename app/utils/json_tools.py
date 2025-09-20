"""Helper utilities for sanitizing JSON strings returned by LLMs."""

from __future__ import annotations

import json
from typing import Any, Tuple


def _strip_markdown_fence(value: str) -> str:
    """Remove Markdown fences (```json ... ```), preserving inner JSON."""

    text = value.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if not lines:
        return ""

    # Drop opening fence (``` or ```json)
    if lines[0].startswith("```"):
        lines = lines[1:]

    # Drop closing fence(s)
    while lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def try_parse_json_string(raw: str) -> Tuple[bool, Any]:
    """Attempt to parse a JSON string that may be wrapped in Markdown fences."""

    if not isinstance(raw, str):
        return False, raw

    stripped = _strip_markdown_fence(raw)
    if not stripped:
        return False, raw

    try:
        return True, json.loads(stripped)
    except json.JSONDecodeError:
        return False, raw


__all__ = ["try_parse_json_string"]
