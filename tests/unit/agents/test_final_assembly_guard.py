from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from google.adk.agents.invocation_context import InvocationContext

from app.agent import FinalAssemblyGuardPre


def _make_ctx(state: dict) -> InvocationContext:
    return InvocationContext(session=SimpleNamespace(state=state))


def _collect(agent, ctx):
    async def _gather():
        events = []
        async for event in agent.run_async(ctx):
            events.append(event)
        return events

    return asyncio.run(_gather())


def test_guard_collects_visual_snippets_and_allows_progress():
    guard = FinalAssemblyGuardPre()
    snippet = {
        "snippet_type": "VISUAL_DRAFT",
        "status": "approved",
        "snippet_id": "abc123",
        "code": "{\"imagem\": \"descrição\"}",
        "approved_at": "2024-01-01T00:00:00Z",
    }
    state = {"approved_code_snippets": [snippet], "delivery_audit_trail": []}
    ctx = _make_ctx(state)

    events = _collect(guard, ctx)

    assert events
    assert state["approved_visual_drafts"][0]["snippet_id"] == "abc123"
    assert state["deterministic_final_blocked"] is False
    assert "deterministic_final_validation_failed" not in state


def test_guard_blocks_when_no_visual_snippets():
    guard = FinalAssemblyGuardPre()
    state = {"approved_code_snippets": [], "delivery_audit_trail": []}
    ctx = _make_ctx(state)

    events = _collect(guard, ctx)

    assert len(events) == 1
    event = events[0]
    assert event.actions and event.actions.escalate is True
    failure = state["deterministic_final_validation"]
    assert failure["grade"] == "fail"
    assert failure["source"] == "guard"
    assert state["deterministic_final_validation_failed"] is True
