"""Utility for loading and rendering StoryBrand fallback prompts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping


class PromptNotFoundError(FileNotFoundError):
    """Raised when a required prompt file is missing."""


@dataclass(frozen=True)
class PromptRenderError(Exception):
    """Raised when a prompt cannot be rendered with the provided context."""

    prompt_name: str
    missing_key: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Missing key '{self.missing_key}' while rendering prompt '{self.prompt_name}'."


class PromptLoader:
    """Loads prompts from disk, caching them for fast reuse."""

    def __init__(self, base_path: Path | str, required_prompts: Iterable[str] | None = None) -> None:
        self._base_path = Path(base_path)
        if not self._base_path.exists():
            raise PromptNotFoundError(f"Prompt directory '{self._base_path}' does not exist.")

        self._cache: Dict[str, str] = {}
        self._load_all()

        if required_prompts is not None:
            missing = [name for name in required_prompts if name not in self._cache]
            if missing:
                raise PromptNotFoundError(
                    f"Missing required prompt files: {', '.join(sorted(missing))}"
                )

    def _load_all(self) -> None:
        for path in self._base_path.glob("*.txt"):
            self._cache[path.stem] = path.read_text(encoding="utf-8").strip()

    def get_prompt(self, name: str) -> str:
        try:
            return self._cache[name]
        except KeyError as exc:
            raise PromptNotFoundError(f"Prompt '{name}' not found in '{self._base_path}'.") from exc

    def render(self, name: str, context: Mapping[str, object]) -> str:
        template = self.get_prompt(name)
        try:
            return template.format(**context)
        except KeyError as exc:  # pragma: no cover - simple exception conversion
            raise PromptRenderError(name, str(exc)) from exc
        except ValueError as exc:  # pragma: no cover - formatting error
            raise PromptRenderError(name, str(exc)) from exc

    @property
    def available_prompts(self) -> Dict[str, str]:
        return dict(self._cache)


__all__ = ["PromptLoader", "PromptNotFoundError", "PromptRenderError"]
