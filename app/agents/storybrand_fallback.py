"""Sequential StoryBrand fallback pipeline implementation."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, Iterable, List, Optional

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from pydantic import BaseModel, Field

from app.config import config
from app.utils.json_tools import try_parse_json_string
from app.utils.prompt_loader import PromptLoader

from .fallback_compiler import FallbackStorybrandCompiler
from .storybrand_sections import StoryBrandSectionConfig, build_storybrand_section_configs


logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts" / "storybrand_fallback"
SECTION_PROMPT_NAMES = {section.prompt_name for section in build_storybrand_section_configs()}
REQUIRED_PROMPTS = {"collector", "corrector", "review_masculino", "review_feminino", "compiler"} | SECTION_PROMPT_NAMES
PROMPT_LOADER = PromptLoader(PROMPT_DIR, required_prompts=REQUIRED_PROMPTS)
FALLBACK_MODEL = getattr(config, "fallback_storybrand_model", None) or getattr(config, "worker_model", "gemini-2.5-flash")
MAX_ITERATIONS = getattr(config, "fallback_storybrand_max_iterations", 3)
REQUIRED_INPUT_KEYS = ("nome_empresa", "o_que_a_empresa_faz", "sexo_cliente_alvo")


class FallbackReviewResult(BaseModel):
    grade: str = Field(..., description="Resultado da revisão: pass ou fail")
    comment: str = Field(default="", description="Feedback textual do revisor")

    @property
    def is_pass(self) -> bool:
        return self.grade.lower() == "pass"


class FallbackInputInitializer(BaseAgent):
    """Ensures initial state keys exist before running the fallback."""

    def __init__(self) -> None:
        super().__init__(name="fallback_input_initializer")

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        audit = state.get("storybrand_audit_trail")
        if not isinstance(audit, list):
            audit = []
        state["storybrand_audit_trail"] = audit

        for key in REQUIRED_INPUT_KEYS:
            state.setdefault(key, "")

        state.setdefault("force_storybrand_fallback", False)
        yield Event(author=self.name)


def _append_audit_event(
    state: Dict[str, object],
    *,
    stage: str,
    status: str,
    section_key: Optional[str] = None,
    iteration: Optional[int] = None,
    details: Optional[object] = None,
) -> None:
    audit_trail = state.get("storybrand_audit_trail")
    if not isinstance(audit_trail, list):
        audit_trail = []
        state["storybrand_audit_trail"] = audit_trail
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    audit_trail.append(
        {
            "stage": stage,
            "status": status,
            "section_key": section_key,
            "iteration": iteration,
            "details": details,
            "timestamp_utc": timestamp,
            "duration_ms": None,
        }
    )


def _normalize_gender(value: object) -> str:
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in {"masculino", "homem", "homens", "masc"}:
            return "masculino"
        if lower in {"feminino", "mulher", "mulheres", "fem"}:
            return "feminino"
    return ""


def fallback_input_collector_callback(callback_context: CallbackContext) -> None:
    state = callback_context.state
    raw_result = state.get("fallback_input_review")
    parsed_result: Optional[Dict[str, object]] = None
    if isinstance(raw_result, dict):
        parsed_result = raw_result
    elif isinstance(raw_result, str):
        parsed, value = try_parse_json_string(raw_result)
        if parsed and isinstance(value, dict):
            parsed_result = value

    errors: List[str] = []
    for key in REQUIRED_INPUT_KEYS:
        current_value = state.get(key)
        extracted_value: Optional[str] = None
        if parsed_result:
            entry = parsed_result.get(key)
            if isinstance(entry, dict):
                maybe_value = entry.get("value")
                if isinstance(maybe_value, str):
                    extracted_value = maybe_value.strip()
        if isinstance(current_value, str) and current_value.strip():
            value = current_value.strip()
        elif extracted_value:
            value = extracted_value
        else:
            value = ""

        if key == "sexo_cliente_alvo":
            normalized = _normalize_gender(value)
            if not normalized:
                errors.append("sexo_cliente_alvo inválido")
            else:
                state[key] = normalized
        else:
            if not value:
                errors.append(f"{key} ausente")
            else:
                state[key] = value

    if errors:
        detail = {"errors": errors}
        _append_audit_event(state, stage="collector", status="error", section_key=None, iteration=None, details=detail)
        raise ValueError(
            "Fallback StoryBrand não pode continuar sem inputs essenciais: " + ", ".join(errors)
        )

    _append_audit_event(
        state,
        stage="collector",
        status="completed",
        section_key=None,
        iteration=None,
        details={key: state.get(key) for key in REQUIRED_INPUT_KEYS},
    )


fallback_input_collector = LlmAgent(
    model=FALLBACK_MODEL,
    name="fallback_input_collector",
    description="Confirma e normaliza os inputs essenciais do fallback StoryBrand.",
    instruction=PROMPT_LOADER.get_prompt("collector"),
    output_key="fallback_input_review",
    after_agent_callback=fallback_input_collector_callback,
)


class StoryBrandSectionRunner(BaseAgent):
    """Executes the 16 sections loop with review and correction."""

    def __init__(self, sections: Iterable[StoryBrandSectionConfig]) -> None:
        super().__init__(name="section_pipeline_runner")
        self._sections = list(sections)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        for section in self._sections:
            await self._run_section(ctx, state, section)
            yield Event(author=self.name)

    async def _run_section(
        self,
        ctx: InvocationContext,
        state: Dict[str, object],
        section: StoryBrandSectionConfig,
    ) -> None:
        gender = _normalize_gender(state.get("sexo_cliente_alvo"))
        if gender not in {"masculino", "feminino"}:
            raise ValueError("sexo_cliente_alvo inválido para execução do fallback")

        for iteration in range(1, MAX_ITERATIONS + 1):
            approved_sections = {
                cfg.state_key: state.get(cfg.state_key)
                for cfg in self._sections
                if isinstance(state.get(cfg.state_key), str) and state.get(cfg.state_key)
            }
            approved_dump = json.dumps(approved_sections, ensure_ascii=False)

            writer_instruction = PROMPT_LOADER.render(
                section.prompt_name,
                {
                    "nome_empresa": state.get("nome_empresa", ""),
                    "o_que_a_empresa_faz": state.get("o_que_a_empresa_faz", ""),
                    "sexo_cliente_alvo": gender,
                    "landing_page_context": state.get("landing_page_context", {}),
                    "approved_sections": approved_dump,
                },
            )
            writer_agent = LlmAgent(
                model=FALLBACK_MODEL,
                name=f"{section.state_key}_writer",
                description=f"Gera a seção {section.state_key} do StoryBrand.",
                instruction=writer_instruction,
                output_key=section.state_key,
            )
            _append_audit_event(
                state,
                stage="writer",
                status="started",
                section_key=section.state_key,
                iteration=iteration,
                details=section.narrative_goal,
            )
            async for event in writer_agent.run_async(ctx):
                yield event
            _append_audit_event(
                state,
                stage="writer",
                status="completed",
                section_key=section.state_key,
                iteration=iteration,
                details={"length": len(str(state.get(section.state_key, "")))},
            )

            review_prompt_name = "review_masculino" if gender == "masculino" else "review_feminino"
            review_instruction = PROMPT_LOADER.render(
                review_prompt_name,
                {
                    "section_key": section.state_key,
                    "current_text": state.get(section.state_key, ""),
                    "o_que_a_empresa_faz": state.get("o_que_a_empresa_faz", ""),
                },
            )
            review_agent = LlmAgent(
                model=FALLBACK_MODEL,
                name=f"{section.state_key}_reviewer",
                description=f"Revisa a seção {section.state_key} do StoryBrand.",
                instruction=review_instruction,
                output_schema=FallbackReviewResult,
                output_key=f"{section.state_key}_review",
            )
            _append_audit_event(
                state,
                stage="reviewer",
                status="started",
                section_key=section.state_key,
                iteration=iteration,
                details=None,
            )
            async for event in review_agent.run_async(ctx):
                yield event

            review_data = state.get(f"{section.state_key}_review")
            if isinstance(review_data, FallbackReviewResult):
                review = review_data
            elif isinstance(review_data, dict):
                review = FallbackReviewResult(**review_data)
            else:
                review = FallbackReviewResult(grade="fail", comment="Revisor retornou formato inesperado.")

            if review.is_pass:
                _append_audit_event(
                    state,
                    stage="reviewer",
                    status="pass",
                    section_key=section.state_key,
                    iteration=iteration,
                    details=review.comment,
                )
                break

            _append_audit_event(
                state,
                stage="reviewer",
                status="fail",
                section_key=section.state_key,
                iteration=iteration,
                details=review.comment,
            )

            corrector_instruction = PROMPT_LOADER.render(
                "corrector",
                {
                    "nome_empresa": state.get("nome_empresa", ""),
                    "o_que_a_empresa_faz": state.get("o_que_a_empresa_faz", ""),
                    "section_key": section.state_key,
                    "current_text": state.get(section.state_key, ""),
                    "review_comment": review.comment,
                },
            )
            corrector_agent = LlmAgent(
                model=FALLBACK_MODEL,
                name=f"{section.state_key}_corrector",
                description=f"Corrige a seção {section.state_key} com base no feedback.",
                instruction=corrector_instruction,
                output_key=section.state_key,
            )
            _append_audit_event(
                state,
                stage="corrector",
                status="started",
                section_key=section.state_key,
                iteration=iteration,
                details=None,
            )
            async for event in corrector_agent.run_async(ctx):
                yield event
            _append_audit_event(
                state,
                stage="corrector",
                status="completed",
                section_key=section.state_key,
                iteration=iteration,
                details=None,
            )
        else:
            _append_audit_event(
                state,
                stage="reviewer",
                status="error",
                section_key=section.state_key,
                iteration=MAX_ITERATIONS,
                details="Limite de iterações atingido sem aprovação.",
            )
            raise RuntimeError(
                f"Seção {section.state_key} não atingiu aprovação após {MAX_ITERATIONS} iterações."
            )


class FallbackQualityReporter(BaseAgent):
    """Persists aggregated metadata about the fallback execution."""

    def __init__(self) -> None:
        super().__init__(name="fallback_quality_reporter")

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        audit = state.get("storybrand_audit_trail")
        if not isinstance(audit, list):
            audit = []
        sections = build_storybrand_section_configs()
        iterations: Dict[str, int] = {}
        for entry in audit:
            if not isinstance(entry, dict):
                continue
            section = entry.get("section_key")
            if not isinstance(section, str):
                continue
            iteration = entry.get("iteration")
            if isinstance(iteration, int):
                iterations[section] = max(iterations.get(section, 0), iteration)
        report = {
            "sections_completed": [cfg.state_key for cfg in sections if state.get(cfg.state_key)],
            "total_sections": len(sections),
            "iterations": iterations,
            "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        state["storybrand_recovery_report"] = report
        yield Event(author=self.name)


fallback_storybrand_pipeline = SequentialAgent(
    name="fallback_storybrand_pipeline",
    description="Reconstrói a narrativa StoryBrand completa com loops de revisão.",
    sub_agents=[
        FallbackInputInitializer(),
        fallback_input_collector,
        StoryBrandSectionRunner(build_storybrand_section_configs()),
        FallbackStorybrandCompiler(),
        FallbackQualityReporter(),
    ],
)


__all__ = [
    "fallback_storybrand_pipeline",
    "FallbackInputInitializer",
    "StoryBrandSectionRunner",
    "FallbackQualityReporter",
]
