import asyncio
from types import SimpleNamespace

import pytest

from google.adk.events import Event

from app.agents.storybrand_gate import StoryBrandQualityGate
from app.config import config


class DummyAgent:
    def __init__(self, name: str):
        self.name = name
        self.called = False

    async def run_async(self, ctx):
        self.called = True
        yield Event(author=self.name)


def make_ctx(state=None):
    state = state or {}
    session = SimpleNamespace(state=state)
    return SimpleNamespace(session=session)


@pytest.mark.asyncio
async def test_gate_runs_happy_path_when_score_high(monkeypatch):
    monkeypatch.setattr(config, "enable_storybrand_fallback", True)
    monkeypatch.setattr(config, "enable_new_input_fields", True)
    monkeypatch.setattr(config, "min_storybrand_completeness", 0.5)
    monkeypatch.setattr(config, "storybrand_gate_debug", False)

    planning = DummyAgent("planning")
    fallback = DummyAgent("fallback")
    gate = StoryBrandQualityGate(planning_agent=planning, fallback_agent=fallback)

    ctx = make_ctx({"storybrand_analysis": {"completeness_score": 0.8}})

    events = []
    async for event in gate._run_async_impl(ctx):
        events.append(event)

    assert planning.called is True
    assert fallback.called is False
    metrics = ctx.session.state["storybrand_gate_metrics"]
    assert metrics["decision_path"] == "happy_path"
    assert metrics["is_forced_fallback"] is False


@pytest.mark.asyncio
async def test_gate_triggers_fallback_when_score_low(monkeypatch):
    monkeypatch.setattr(config, "enable_storybrand_fallback", True)
    monkeypatch.setattr(config, "enable_new_input_fields", True)
    monkeypatch.setattr(config, "min_storybrand_completeness", 0.9)

    planning = DummyAgent("planning")
    fallback = DummyAgent("fallback")
    gate = StoryBrandQualityGate(planning_agent=planning, fallback_agent=fallback)

    ctx = make_ctx({"landing_page_context": {"storybrand_completeness": 0.4}})

    async for _ in gate._run_async_impl(ctx):
        pass

    assert planning.called is True
    assert fallback.called is True
    metrics = ctx.session.state["storybrand_gate_metrics"]
    assert metrics["decision_path"] == "fallback"
    assert metrics["is_forced_fallback"] is False


@pytest.mark.asyncio
async def test_gate_respects_force_flag(monkeypatch):
    monkeypatch.setattr(config, "enable_storybrand_fallback", True)
    monkeypatch.setattr(config, "enable_new_input_fields", True)
    monkeypatch.setattr(config, "min_storybrand_completeness", 0.2)

    planning = DummyAgent("planning")
    fallback = DummyAgent("fallback")
    gate = StoryBrandQualityGate(planning_agent=planning, fallback_agent=fallback)

    ctx = make_ctx({
        "storybrand_analysis": {"completeness_score": 0.95},
        "force_storybrand_fallback": True,
    })

    async for _ in gate._run_async_impl(ctx):
        pass

    assert planning.called is True
    assert fallback.called is True
    metrics = ctx.session.state["storybrand_gate_metrics"]
    assert metrics["decision_path"] == "fallback"
    assert metrics["is_forced_fallback"] is True


@pytest.mark.asyncio
async def test_gate_blocks_when_flags_disabled(monkeypatch):
    monkeypatch.setattr(config, "enable_storybrand_fallback", False)
    monkeypatch.setattr(config, "enable_new_input_fields", False)
    monkeypatch.setattr(config, "min_storybrand_completeness", 0.9)

    planning = DummyAgent("planning")
    fallback = DummyAgent("fallback")
    gate = StoryBrandQualityGate(planning_agent=planning, fallback_agent=fallback)

    ctx = make_ctx({
        "landing_page_context": {"storybrand_completeness": 0.1},
        "force_storybrand_fallback": True,
    })

    async for _ in gate._run_async_impl(ctx):
        pass

    assert planning.called is True
    assert fallback.called is False
    metrics = ctx.session.state["storybrand_gate_metrics"]
    assert metrics["decision_path"] == "happy_path"
    assert metrics.get("block_reason") == "fallback_disabled"
