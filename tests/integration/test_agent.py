from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

from app.agent import FeatureOrchestrator


class DummyPipeline:
    def __init__(self) -> None:
        self.called = False

    async def run_async(self, ctx):
        self.called = True
        yield Event(author="dummy", content=Content(parts=[Part(text="pipeline executed")]))


def _ctx(state: dict) -> InvocationContext:
    session = SimpleNamespace(state=state)
    return InvocationContext(session=session)


def _collect(agent, ctx):
    async def _gather():
        events = []
        async for event in agent.run_async(ctx):
            events.append(event)
        return events

    return asyncio.run(_gather())


def test_orchestrator_emits_failure_when_deterministic_blocked():
    orchestrator = FeatureOrchestrator(complete_pipeline=DummyPipeline())
    state = {
        "deterministic_final_validation_failed": True,
        "deterministic_final_validation_failure_reason": "CTA inválido",
    }
    ctx = _ctx(state)

    messages = _collect(orchestrator, ctx)

    assert any("Validação Determinística" in (part.text or "") for event in messages for part in event.content.parts)


def test_orchestrator_runs_only_once():
    pipeline = DummyPipeline()
    orchestrator = FeatureOrchestrator(complete_pipeline=pipeline)
    state = {}
    ctx = _ctx(state)

    # primeira execução
    events = _collect(orchestrator, ctx)

    assert pipeline.called is True
    assert state.get("orchestrator_has_run") is False

    # segunda execução reinicia o fluxo
    pipeline.called = False
    events_second = _collect(orchestrator, ctx)

    assert pipeline.called is True
    assert any("Iniciando processamento" in (part.text or "") for event in events_second for part in event.content.parts)
