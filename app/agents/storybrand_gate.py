"""StoryBrandQualityGate agent implementation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from app.config import config
from app.utils.metrics import record_storybrand_fallback


logger = logging.getLogger(__name__)


def _extract_score(state: dict[str, object]) -> Optional[float]:
    score = None
    storybrand = state.get("storybrand_analysis")
    if isinstance(storybrand, dict):
        score = storybrand.get("completeness_score")
    if score is None:
        landing_page = state.get("landing_page_context")
        if isinstance(landing_page, dict):
            score = landing_page.get("storybrand_completeness")
    if isinstance(score, (int, float)):
        return float(score)
    try:
        if isinstance(score, str):
            return float(score)
    except (TypeError, ValueError):
        return None
    return None


class StoryBrandQualityGate(BaseAgent):
    """Decides whether to trigger the StoryBrand fallback pipeline."""

    def __init__(self, planning_agent: BaseAgent, fallback_agent: BaseAgent) -> None:
        super().__init__(name="storybrand_quality_gate")
        self._planning_agent = planning_agent
        self._fallback_agent = fallback_agent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        threshold = getattr(config, "min_storybrand_completeness", 0.0)
        score = _extract_score(state)
        fallback_enabled = bool(getattr(config, "enable_storybrand_fallback", False) and getattr(config, "enable_new_input_fields", False))
        debug_flag = bool(getattr(config, "storybrand_gate_debug", False))
        force_flag = bool(state.get("force_storybrand_fallback"))

        should_force = fallback_enabled and (force_flag or debug_flag)
        score_missing = score is None
        score_below_threshold = score is not None and score < threshold

        should_run_fallback = False
        forced_reason = False
        block_reason: Optional[str] = None

        if should_force:
            should_run_fallback = True
            forced_reason = True
        elif not fallback_enabled:
            should_run_fallback = False
            if force_flag or debug_flag:
                block_reason = "fallback_disabled"
        elif score_missing:
            should_run_fallback = True
            forced_reason = True
        elif score_below_threshold:
            should_run_fallback = True

        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        metrics = {
            "score_obtained": score,
            "score_threshold": threshold,
            "decision_path": "fallback" if should_run_fallback else "happy_path",
            "timestamp_utc": timestamp,
            "is_forced_fallback": forced_reason,
            "debug_flag_active": debug_flag,
        }

        state["storybrand_gate_metrics"] = metrics

        debug_payload = {
            "force_flag_active": force_flag,
            "fallback_enabled": fallback_enabled,
        }
        if block_reason:
            debug_payload["block_reason"] = block_reason

        state["storybrand_gate_debug"] = debug_payload

        logger.info(
            "storybrand_gate_decision",
            extra={
                "score": score,
                "threshold": threshold,
                "decision_path": metrics["decision_path"],
                "forced": forced_reason,
                "fallback_enabled": fallback_enabled,
                "force_flag": force_flag,
                "debug_flag": debug_flag,
                "block_reason": block_reason,
            },
        )

        if should_run_fallback:
            if forced_reason:
                fallback_reason = "forced"
            elif score_missing:
                fallback_reason = "missing_score"
            elif score_below_threshold:
                fallback_reason = "score_below_threshold"
            else:
                fallback_reason = "unknown"
            record_storybrand_fallback(fallback_reason)
            async for event in self._fallback_agent.run_async(ctx):
                yield event

        async for event in self._planning_agent.run_async(ctx):
            yield event
