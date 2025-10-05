"""Gating utilities shared across deterministic validation stages."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Iterable, Sequence

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part


logger = logging.getLogger(__name__)


class RunIfPassed(BaseAgent):
    """Run the wrapped agent only when the review key matches the expected grade."""

    def __init__(
        self,
        *,
        name: str,
        review_key: str,
        agent: BaseAgent,
        expected_grade: str = "pass",
    ) -> None:
        super().__init__(name=name)
        self._review_key = review_key
        self._agent = agent
        self._expected_grade = expected_grade

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        result = state.get(self._review_key)
        grade: str | None = None
        if isinstance(result, dict):
            grade = result.get("grade")
        elif isinstance(result, str):
            grade = result

        if grade == self._expected_grade:
            async for event in self._agent.run_async(ctx):
                yield event
            return

        logger.info(
            "RunIfPassed: skipping %s because %s grade is %s (expected %s)",
            self._agent.name,
            self._review_key,
            grade,
            self._expected_grade,
        )
        reason = grade or "ausente"
        message = (
            f"Skipping {self._agent.name}; {self._review_key} grade é {reason!s} "
            f"(esperado {self._expected_grade})."
        )
        yield Event(
            author=self.name,
            content=Content(parts=[Part(text=message)]),
        )


class ResetDeterministicValidationState(BaseAgent):
    """Clear deterministic validation artifacts when the legacy path is used."""

    def __init__(
        self,
        *,
        name: str = "reset_deterministic_validation_state",
        keys: Iterable[str] | None = None,
    ) -> None:
        super().__init__(name=name)
        default_keys: Sequence[str] = (
            "approved_visual_drafts",
            "deterministic_final_validation",
            "deterministic_final_validation_failed",
            "deterministic_final_validation_failure_reason",
            "deterministic_final_blocked",
            "final_code_delivery_parsed",
        )
        self._keys = tuple(keys) if keys is not None else tuple(default_keys)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        removed: list[str] = []
        for key in self._keys:
            if key in state:
                removed.append(key)
            state.pop(key, None)

        if removed:
            logger.info(
                "ResetDeterministicValidationState: removed keys: %s", removed
            )
            message = (
                "Limpei estado determinístico anterior: " + ", ".join(removed)
            )
        else:
            message = "Nenhum estado determinístico para limpar."

        yield Event(author=self.name, content=Content(parts=[Part(text=message)]))


__all__ = ["ResetDeterministicValidationState", "RunIfPassed"]

