from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from google.adk.agents.invocation_context import InvocationContext
from google.genai.types import Content, Part

from app.agent import (
    FinalAssemblyGuardPre,
    FinalAssemblyNormalizer,
    PersistFinalDeliveryAgent,
)
from app.agents.gating import RunIfPassed
from app.validators.final_delivery_validator import FinalDeliveryValidatorAgent


class DummySemanticStage:
    def __init__(self) -> None:
        self.called = False

    async def run_async(self, ctx):
        self.called = True
        ctx.session.state["semantic_visual_review"] = {"grade": "pass"}
        yield SimpleNamespace(author="semantic_stage", content=Content(parts=[Part(text="semantic ok")]))


class DummyImageStage:
    def __init__(self) -> None:
        self.called = False

    async def run_async(self, ctx):
        self.called = True
        ctx.session.state["image_assets_review"] = {"grade": "skipped"}
        yield SimpleNamespace(author="image_stage", content=Content(parts=[Part(text="images skipped")]))


def _variation(idx: int) -> dict[str, object]:
    return {
        "landing_page_url": f"https://example.com/{idx}",
        "formato": "Reels",
        "cta_instagram": "Cadastre-se",
        "fluxo": "Instagram → Landing Page",
        "referencia_padroes": "StoryBrand",
        "contexto_landing": {"hero": "consultas"},
        "copy": {
            "headline": f"Versão {idx}",
            "corpo": "Automatize o agendamento.",
            "cta_texto": "Cadastre-se",
        },
        "visual": {
            "descricao_imagem": f"Pessoa usando app {idx}",
            "prompt_estado_atual": "cliente confuso",
            "prompt_estado_intermediario": "cliente testando app",
            "prompt_estado_aspiracional": "cliente satisfeito",
            "aspect_ratio": "9:16",
        },
    }


def _ctx(state: dict) -> InvocationContext:
    session = SimpleNamespace(id="sess-flow", user_id="user-flow", state=state)
    return InvocationContext(session=session)


def _collect(agent, ctx):
    async def _gather():
        events = []
        async for event in agent.run_async(ctx):
            events.append(event)
        return events

    return asyncio.run(_gather())


def test_deterministic_pipeline_flow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DELIVERIES_BUCKET", "")

    guard = FinalAssemblyGuardPre()
    normalizer = FinalAssemblyNormalizer()
    validator = FinalDeliveryValidatorAgent()
    semantic_stage = DummySemanticStage()
    image_stage = DummyImageStage()
    persist_agent = PersistFinalDeliveryAgent()

    semantic_gate = RunIfPassed(
        name="semantic_if_passed",
        review_key="deterministic_final_validation",
        agent=semantic_stage,
    )
    image_gate = RunIfPassed(
        name="image_if_passed",
        review_key="semantic_visual_review",
        agent=image_stage,
        expected_grade="pass",
    )
    persist_gate = RunIfPassed(
        name="persist_if_passed",
        review_key="image_assets_review",
        agent=persist_agent,
        expected_grade=("pass", "skipped"),
    )

    state: dict[str, object] = {
        "approved_code_snippets": [
            {
                "snippet_type": "VISUAL_DRAFT",
                "status": "approved",
                "snippet_id": "draft-1",
                "code": json.dumps({"descricao": "ok"}, ensure_ascii=False),
            }
        ],
        "final_code_delivery": json.dumps([_variation(1), _variation(2), _variation(3)], ensure_ascii=False),
        "delivery_audit_trail": [],
        "objetivo_final": "Leads",
    }
    ctx = _ctx(state)

    events = []
    events.extend(_collect(guard, ctx))
    events.extend(_collect(normalizer, ctx))
    events.extend(_collect(validator, ctx))
    events.extend(_collect(semantic_gate, ctx))
    events.extend(_collect(image_gate, ctx))
    events.extend(_collect(persist_gate, ctx))

    assert semantic_stage.called is True
    assert image_stage.called is True
    assert Path(state["final_delivery_local_path"]).exists()
    assert state["final_delivery_status"]["stage"] == "deterministic_final_validation"
    assert state["image_assets_review"]["grade"] == "skipped"

