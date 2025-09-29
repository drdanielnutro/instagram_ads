from types import SimpleNamespace

import pytest
from google.adk.events import Event

from app.agent import LandingPageStage
from app.config import config


class DummyLandingPageAgent:
    def __init__(self) -> None:
        self.called = False

    async def run_async(self, ctx):
        self.called = True
        yield Event(author="dummy_landing_agent")


def make_ctx(state=None):
    state = state or {}
    session = SimpleNamespace(state=state)
    return SimpleNamespace(session=session)


@pytest.mark.asyncio
async def test_landing_page_stage_skips_when_debug_forces(monkeypatch):
    monkeypatch.setattr(config, "enable_storybrand_fallback", True)
    monkeypatch.setattr(config, "enable_new_input_fields", True)
    monkeypatch.setattr(config, "storybrand_gate_debug", True)

    dummy = DummyLandingPageAgent()
    stage = LandingPageStage(landing_page_agent=dummy)

    ctx = make_ctx()

    events = []
    async for event in stage._run_async_impl(ctx):
        events.append(event)

    assert events == []
    assert dummy.called is False
    assert isinstance(ctx.session.state.get("landing_page_context"), dict)


@pytest.mark.asyncio
async def test_landing_page_stage_skips_when_force_flag(monkeypatch):
    monkeypatch.setattr(config, "enable_storybrand_fallback", True)
    monkeypatch.setattr(config, "enable_new_input_fields", True)
    monkeypatch.setattr(config, "storybrand_gate_debug", False)

    dummy = DummyLandingPageAgent()
    stage = LandingPageStage(landing_page_agent=dummy)

    ctx = make_ctx({"force_storybrand_fallback": True})

    events = []
    async for event in stage._run_async_impl(ctx):
        events.append(event)

    assert events == []
    assert dummy.called is False
    assert isinstance(ctx.session.state.get("landing_page_context"), dict)


@pytest.mark.asyncio
async def test_landing_page_stage_runs_agent_when_not_forced(monkeypatch):
    monkeypatch.setattr(config, "enable_storybrand_fallback", True)
    monkeypatch.setattr(config, "enable_new_input_fields", True)
    monkeypatch.setattr(config, "storybrand_gate_debug", False)

    dummy = DummyLandingPageAgent()
    stage = LandingPageStage(landing_page_agent=dummy)

    ctx = make_ctx()

    events = []
    async for event in stage._run_async_impl(ctx):
        events.append(event)

    assert dummy.called is True
    assert events and events[0].author == "dummy_landing_agent"
