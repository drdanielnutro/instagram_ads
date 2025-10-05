from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from google.adk.agents.invocation_context import InvocationContext

from app.agent import build_execution_pipeline


def _agent_names(pipeline) -> list[str]:
    return [getattr(agent, "name", "") for agent in pipeline.sub_agents]


def _collect(agent, ctx):
    async def _gather():
        events = []
        async for event in agent.run_async(ctx):
            events.append(event)
        return events

    return asyncio.run(_gather())


def test_pipeline_switches_agents_based_on_flag():
    deterministic_pipeline = build_execution_pipeline(True)
    names_on = _agent_names(deterministic_pipeline)

    assert "final_assembly_stage" in names_on
    assert "semantic_validation_if_passed" in names_on
    assert any(name.startswith("persist_final_delivery") for name in names_on)

    legacy_pipeline = build_execution_pipeline(False)
    names_off = _agent_names(legacy_pipeline)
    assert "reset_deterministic_validation_state" in names_off
    assert "final_assembly_stage" not in names_off  # usa caminho legado

    reset_agent = next(
        agent for agent in legacy_pipeline.sub_agents if agent.name == "reset_deterministic_validation_state"
    )
    state = {
        "approved_visual_drafts": [1],
        "deterministic_final_validation": {"grade": "fail"},
        "deterministic_final_blocked": True,
        "final_code_delivery_parsed": [1, 2, 3],
    }
    ctx = InvocationContext(session=SimpleNamespace(state=state))

    events = _collect(reset_agent, ctx)

    assert not state
    assert events[0].author == "reset_deterministic_validation_state"
