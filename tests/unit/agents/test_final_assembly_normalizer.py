from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace

import pytest

from google.adk.agents.invocation_context import InvocationContext

from app.agent import FinalAssemblyNormalizer


def _make_ctx(state: dict) -> InvocationContext:
    """Create a valid InvocationContext for testing.

    Updated to comply with ADK InvocationContext API requirements.
    """
    from google.adk.sessions import InMemorySessionService, Session
    from google.adk.agents import BaseAgent

    session_service = InMemorySessionService()
    agent = BaseAgent(name="test_agent", description="Test agent for unit tests")

    session = Session(
        id="test-session",
        app_name="test-app",
        user_id="test-user",
        state=state
    )

    return InvocationContext(
        session_service=session_service,
        invocation_id=f"e-{uuid.uuid4()}",
        agent=agent,
        session=session
    )


def _variation() -> dict[str, object]:
    return {
        "landing_page_url": "https://example.com",
        "formato": "Reels",
        "cta_instagram": "Saiba mais",
        "fluxo": "Instagram → Landing Page",
        "referencia_padroes": "StoryBrand",
        "contexto_landing": {"hero": "consultas"},
        "copy": {
            "headline": "Transforme o atendimento",
            "corpo": "Automatize processos",
            "cta_texto": "Saiba mais",
        },
        "visual": {
            "descricao_imagem": "Pessoa usando aplicativo",
            "prompt_estado_atual": "cliente confuso",
            "prompt_estado_intermediario": "cliente testando app",
            "prompt_estado_aspiracional": "cliente satisfeito",
            "aspect_ratio": "9:16",
        },
    }


def _collect(agent, ctx):
    async def _gather():
        events = []
        async for event in agent.run_async(ctx):
            events.append(event)
        return events

    return asyncio.run(_gather())


def test_normalizer_successfully_transforms_payload():
    normalizer = FinalAssemblyNormalizer()
    variations = [_variation(), _variation(), _variation()]
    state = {
        "final_code_delivery": json.dumps(variations, ensure_ascii=False),
        "delivery_audit_trail": [],
    }
    ctx = _make_ctx(state)

    events = _collect(normalizer, ctx)

    # Read state from session context
    state = ctx.session.state

    assert events
    result = state["deterministic_final_validation"]
    assert result["grade"] == "pending"
    assert state["deterministic_final_blocked"] is False
    assert len(state["final_code_delivery_parsed"]) == 3
    assert isinstance(json.loads(state["final_code_delivery"]), list)


def test_normalizer_fails_with_invalid_payload():
    normalizer = FinalAssemblyNormalizer()
    state = {
        "final_code_delivery": "{}",
        "delivery_audit_trail": [],
    }
    ctx = _make_ctx(state)

    events = _collect(normalizer, ctx)

    # Read state from session context
    state = ctx.session.state

    assert len(events) == 1
    failure = state["deterministic_final_validation"]
    assert failure["grade"] == "fail"
    assert failure["source"] == "normalizer"
    assert state["deterministic_final_validation_failed"] is True
