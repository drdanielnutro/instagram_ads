from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace

import pytest

from google.adk.agents.invocation_context import InvocationContext

from app.validators.final_delivery_validator import FinalDeliveryValidatorAgent


def _make_variation(headline: str, cta: str = "Saiba mais") -> dict[str, object]:
    return {
        "landing_page_url": "https://example.com",
        "formato": "Reels",
        "copy": {
            "headline": headline,
            "corpo": "Descubra uma nova forma de vender.",
            "cta_texto": cta,
        },
        "visual": {
            "descricao_imagem": "Pessoa utilizando aplicativo",
            "prompt_estado_atual": "customer looking for options",
            "prompt_estado_intermediario": "customer comparing plans",
            "prompt_estado_aspiracional": "customer celebrating new plan",
            "aspect_ratio": "9:16",
        },
        "cta_instagram": cta,
        "fluxo": "Instagram → Landing Page",
        "referencia_padroes": "StoryBrand",
        "contexto_landing": "",
    }


def _make_ctx(state: dict[str, object]) -> InvocationContext:
    """Create a valid InvocationContext for testing.

    Updated to comply with ADK InvocationContext API requirements:
    - session_service: BaseSessionService (required)
    - invocation_id: str (required)
    - agent: BaseAgent (required)
    - session: Session (required)
    """
    from google.adk.sessions import InMemorySessionService, Session
    from google.adk.agents import BaseAgent

    # Create real session_service instance
    session_service = InMemorySessionService()

    # Create minimal agent instance
    agent = BaseAgent(name="test_agent", description="Test agent for unit tests")

    # Create session with proper ADK Session class
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


@pytest.fixture()
def validator(monkeypatch):
    captured: dict[str, object] = {}

    def fake_write_failure_meta(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(path="/tmp/meta.json")

    monkeypatch.setattr(
        "app.validators.final_delivery_validator.write_failure_meta",
        fake_write_failure_meta,
    )

    agent = FinalDeliveryValidatorAgent()
    return agent, captured


def _collect_events(agent, ctx):
    async def _gather():
        events = []
        async for event in agent.run_async(ctx):
            events.append(event)
        return events

    return asyncio.run(_gather())


def test_validator_passes_and_normalizes(validator):
    agent, captured = validator
    state = {
        "objetivo_final": "Leads",
        "final_code_delivery": json.dumps(
            [
                _make_variation("Chegou a solução completa", cta="Cadastre-se"),
                _make_variation("Transforme seu atendimento", cta="Cadastre-se"),
                _make_variation("Ganhe eficiência agora", cta="Cadastre-se"),
            ],
            ensure_ascii=False,
        ),
        "delivery_audit_trail": [],
    }
    ctx = _make_ctx(state)

    events = _collect_events(agent, ctx)

    # Read state from session context (agents modify ctx.session.state, not the original dict)
    state = ctx.session.state

    assert events, "esperava ao menos um evento"
    result = state["deterministic_final_validation"]
    assert result["grade"] == "pass"
    assert result["normalized_payload"]["variations"][0]["copy"]["headline"] == "Chegou a solução completa"
    assert isinstance(state["final_code_delivery"], str)
    assert not captured, "Não deveria gravar meta de falha em caso de sucesso"


def test_validator_detects_duplicates_and_cta_mismatch(validator):
    agent, captured = validator
    state = {
        "objetivo_final": "Vendas",
        "final_code_delivery": json.dumps(
            [
                _make_variation("Oferta imperdível", cta="Comprar agora"),
                _make_variation("Oferta imperdível", cta="Comprar agora"),
                _make_variation("Ganhe bônus", cta="Ligar"),
            ],
            ensure_ascii=False,
        ),
        "delivery_audit_trail": [],
    }
    ctx = _make_ctx(state)

    events = _collect_events(agent, ctx)

    # Read state from session context
    state = ctx.session.state

    result = state["deterministic_final_validation"]
    assert result["grade"] == "fail"
    issues = " ".join(result["issues"])
    assert "duplicadas" in issues
    assert "CTA" in issues
    assert state["deterministic_final_validation_failed"] is True
    assert captured["reason"] == "deterministic_final_validation_failed"


def test_validator_handles_invalid_payload(validator):
    agent, captured = validator
    state = {
        "objetivo_final": "Leads",
        "final_code_delivery": "not json",
        "delivery_audit_trail": [],
    }
    ctx = _make_ctx(state)

    events = _collect_events(agent, ctx)

    # Read state from session context
    state = ctx.session.state

    result = state["deterministic_final_validation"]
    assert result["grade"] == "fail"
    assert result["issues"]
    assert captured["reason"] == "deterministic_final_validation_failed"
