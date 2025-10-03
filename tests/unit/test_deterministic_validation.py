import asyncio
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

with patch("google.cloud.storage.Client", return_value=MagicMock()):
    with patch("google.genai.Client", return_value=MagicMock()):
        from app.agent import (  # noqa: WPS433 (module import inside context)
            FinalAssemblyGuardPre,
            FinalAssemblyNormalizer,
            ResetDeterministicValidationState,
            RunIfPassed,
            collect_code_snippets_callback,
        )

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai.types import Content, Part


class DummySession:
    def __init__(self, state: dict[str, Any]):
        self.state = state
        self.id = "dummy"
        self.user_id = "tester"


class DummyInvocationContext:
    def __init__(self, state: dict[str, Any]):
        self.session = DummySession(state)


class DummyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="dummy_agent")

    async def _run_async_impl(self, ctx: DummyInvocationContext) -> Any:  # type: ignore[override]
        ctx.session.state["dummy_agent_executed"] = True
        yield Event(author=self.name, content=Content(parts=[Part(text="ran")]))


class DummySimpleAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="dummy_simple_agent")

    async def run_async(self, ctx: DummyInvocationContext) -> Any:  # type: ignore[override]
        ctx.session.state["dummy_agent_executed"] = True
        yield Event(author=self.name, content=Content(parts=[Part(text="ran")]))


def run_agent(agent: BaseAgent, state: dict[str, Any]) -> list[Event]:
    ctx = DummyInvocationContext(state)

    async def _collect() -> list[Event]:
        events: list[Event] = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)
        return events

    return asyncio.run(_collect())


def test_collect_code_snippets_callback_adds_metadata() -> None:
    class DummyCallbackContext:
        def __init__(self):
            self.state: dict[str, Any] = {}

    ctx = DummyCallbackContext()
    ctx.state["generated_code"] = "{\"visual\": {}}"
    ctx.state["current_task_info"] = {
        "id": "task-1",
        "category": "VISUAL_DRAFT",
        "description": "Generate visual",
        "file_path": "visual.json",
    }

    collect_code_snippets_callback(ctx)

    assert ctx.state["approved_code_snippets"], "Snippet collection should not be empty"
    snippet = ctx.state["approved_code_snippets"][0]
    assert snippet["status"] == "approved"
    assert snippet["snippet_type"] == "VISUAL_DRAFT"
    assert "approved_at" in snippet
    assert "snippet_id" in snippet and len(snippet["snippet_id"]) == 64


@pytest.mark.asyncio
async def test_final_assembly_guard_pre_collects_visual_snippets() -> None:
    state = {
        "approved_code_snippets": [
            {
                "category": "VISUAL_DRAFT",
                "code": json.dumps({"visual": {"descricao": "sample"}}),
                "task_id": "t-1",
            }
        ]
    }
    agent = FinalAssemblyGuardPre()
    ctx = DummyInvocationContext(state)

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert state["approved_visual_drafts"], "Guard should populate approved_visual_drafts"
    assert state["final_delivery_validation"]["grade"] == "pending"
    assert events, "Guard should emit at least one event"


@pytest.mark.asyncio
async def test_final_assembly_normalizer_serializes_context() -> None:
    state = {
        "final_code_delivery": json.dumps([
            {
                "contexto_landing": {"foo": "bar"},
                "visual": {},
            }
        ]),
        "approved_visual_drafts": [
            {
                "snippet_id": "abc",
                "content": {"visual": {"descricao_imagem": "ok"}},
            }
        ],
    }
    agent = FinalAssemblyNormalizer()
    ctx = DummyInvocationContext(state)

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert json.loads(state["final_code_delivery"])[0]["contexto_landing"] == json.dumps({"foo": "bar"}, ensure_ascii=False, sort_keys=True)
    assert state["final_code_delivery_parsed"][0]["visual"]["descricao_imagem"] == "ok"


def test_reset_deterministic_validation_state_removes_keys() -> None:
    state = {
        "approved_visual_drafts": [1],
        "final_delivery_validation": {"grade": "fail"},
        "final_delivery_validation_failed": True,
        "final_delivery_validation_failure_reason": "err",
        "final_code_delivery_parsed": [1],
    }
    agent = ResetDeterministicValidationState()
    run_agent(agent, state)

    for key in [
        "approved_visual_drafts",
        "final_delivery_validation",
        "final_delivery_validation_failed",
        "final_delivery_validation_failure_reason",
        "final_code_delivery_parsed",
    ]:
        assert key not in state


def test_run_if_passed_executes_only_on_pass() -> None:
    child = DummySimpleAgent()
    wrapper = RunIfPassed(name="run_if_passed_test", review_key="final_validation_result", agent=child)

    state = {"final_validation_result": {"grade": "fail"}}
    events = run_agent(wrapper, state)
    assert "dummy_agent_executed" not in state
    assert "Skipping" in events[0].content.parts[0].text  # type: ignore[index]

    state["final_validation_result"] = {"grade": "pass"}
    events = run_agent(wrapper, state)
    assert state["dummy_agent_executed"] is True
    assert events, "Events should be emitted when wrapped agent runs"
