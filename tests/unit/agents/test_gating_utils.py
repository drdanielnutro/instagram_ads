from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

from app.agents.gating import ResetDeterministicValidationState, RunIfPassed


class DummyAgent:
    def __init__(self, name: str = "dummy") -> None:
        self.name = name
        self.called = False

    async def run_async(self, ctx):
        self.called = True
        yield Event(author=self.name, content=Content(parts=[Part(text="executed")]))


def _ctx(state: dict) -> InvocationContext:
    return InvocationContext(session=SimpleNamespace(state=state))


def _collect(agent, ctx):
    async def _gather():
        events = []
        async for event in agent.run_async(ctx):
            events.append(event)
        return events

    return asyncio.run(_gather())


def test_run_if_passed_executes_when_grade_matches():
    state = {
        "deterministic_final_validation": {"grade": "pass"},
        "delivery_audit_trail": [],
    }
    agent = DummyAgent(name="semantic")
    wrapper = RunIfPassed(
        name="semantic_if_passed",
        review_key="deterministic_final_validation",
        agent=agent,
    )
    ctx = _ctx(state)

    events = _collect(wrapper, ctx)

    assert agent.called is True
    assert events[0].author == "semantic"


def test_run_if_passed_skips_and_logs_when_grade_missing():
    state = {"delivery_audit_trail": []}
    agent = DummyAgent()
    wrapper = RunIfPassed(
        name="semantic_if_passed",
        review_key="semantic_visual_review",
        agent=agent,
        expected_grade=("pass", "skipped"),
    )
    ctx = _ctx(state)

    events = _collect(wrapper, ctx)

    assert agent.called is False
    assert events[0].author == "semantic_if_passed"
    assert state["delivery_audit_trail"][-1]["status"] == "skipped"


def test_reset_deterministic_validation_state_clears_keys():
    state = {
        "approved_visual_drafts": [1],
        "deterministic_final_validation": {"grade": "fail"},
        "deterministic_final_validation_failed": True,
        "deterministic_final_validation_failure_reason": "erro",
        "deterministic_final_blocked": True,
        "final_code_delivery_parsed": [1, 2, 3],
    }
    reset_agent = ResetDeterministicValidationState()
    ctx = _ctx(state)

    events = _collect(reset_agent, ctx)

    assert not state
    assert events[0].author == "reset_deterministic_validation_state"
