"""Sequential StoryBrand fallback pipeline implementation."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, Iterable, List, Optional

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from pydantic import BaseModel, Field

from app.config import config
from app.utils.json_tools import try_parse_json_string
from app.callbacks.persist_outputs import _upload_to_gcs
from app.utils.logging_helpers import log_struct_event
from app.utils.prompt_loader import PromptLoader
from app.utils.session_state import safe_session_id, safe_user_id

from .fallback_compiler import FallbackStorybrandCompiler
from .storybrand_sections import StoryBrandSectionConfig, build_storybrand_section_configs


logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts" / "storybrand_fallback"
SECTION_CONFIGS = build_storybrand_section_configs()
REQUIRED_PROMPTS = {
    "collector",
    "corrector",
    "review_masculino",
    "review_feminino",
    "compiler",
} | {section.writer_prompt_path.stem for section in SECTION_CONFIGS}
PROMPT_LOADER = PromptLoader(PROMPT_DIR, required_prompts=REQUIRED_PROMPTS)
FALLBACK_MODEL = getattr(config, "fallback_storybrand_model", None) or getattr(config, "worker_model", "gemini-2.5-flash")
MAX_ITERATIONS = getattr(config, "fallback_storybrand_max_iterations", 3)
REQUIRED_INPUT_KEYS = ("nome_empresa", "o_que_a_empresa_faz", "sexo_cliente_alvo")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


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
    duration_ms: Optional[int] = None,
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
            "duration_ms": duration_ms,
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


def _collect_text_fragments(value: object) -> List[str]:
    fragments: List[str] = []
    if isinstance(value, str):
        fragments.append(value)
    elif isinstance(value, list):
        for item in value:
            fragments.extend(_collect_text_fragments(item))
    elif isinstance(value, dict):
        for val in value.values():
            fragments.extend(_collect_text_fragments(val))
    return fragments


_SENSITIVE_REDACTIONS = (
    re.compile(r"(?i)(token=)([^&\s]+)"),
    re.compile(r"(?i)(signature=)([^&\s]+)"),
    re.compile(r"(?i)(sig=)([^&\s]+)"),
    re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+[^\s]+)"),
)


def _sanitize_section_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        sanitized = value
    else:
        try:
            sanitized = str(value)
        except Exception:
            sanitized = ""
    for pattern in _SENSITIVE_REDACTIONS:
        sanitized = pattern.sub(lambda match: match.group(1) + "[REDACTED]", sanitized)
    return sanitized


def _safe_jsonable(value: object) -> object:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): _safe_jsonable(val) for key, val in value.items()}
        if isinstance(value, list):
            return [_safe_jsonable(item) for item in value]
        return str(value)


FEMININE_MARKERS = {
    "ela",
    "dela",
    "delas",
    "mulher",
    "mulheres",
    "feminino",
    "feminina",
    "cliente feminina",
    "para ela",
}
MASCULINE_MARKERS = {
    "ele",
    "dele",
    "deles",
    "homem",
    "homens",
    "masculino",
    "masculina",
    "cliente masculino",
    "para ele",
}


def _infer_gender_from_context(context: object) -> str:
    if not isinstance(context, dict):
        return ""

    feminine_hits = 0
    masculine_hits = 0
    for fragment in _collect_text_fragments(context):
        lowered = fragment.lower()
        if any(token in lowered for token in FEMININE_MARKERS):
            feminine_hits += 1
        if any(token in lowered for token in MASCULINE_MARKERS):
            masculine_hits += 1

    if feminine_hits > masculine_hits and feminine_hits > 0:
        return "feminino"
    if masculine_hits > feminine_hits and masculine_hits > 0:
        return "masculino"
    return ""


def _log_section_event(
    *,
    section_key: Optional[str],
    stage: str,
    status: str,
    iteration: Optional[int],
    **extra: object,
) -> None:
    payload: Dict[str, object] = {
        "section_key": section_key,
        "stage": stage,
        "status": status,
        "iteration": iteration,
    }
    payload.update(extra)
    logger.info("storybrand_fallback_section", extra=payload)


def _coerce_review_result(value: object) -> FallbackReviewResult:
    if isinstance(value, FallbackReviewResult):
        return value
    if isinstance(value, dict):
        return FallbackReviewResult(**value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return FallbackReviewResult(**parsed)
        except json.JSONDecodeError:
            pass
    return FallbackReviewResult(grade="fail", comment="Formato inesperado retornado pelo revisor.")


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
    enriched_fields: Dict[str, object] = {}
    enriched_registry = state.get("storybrand_enriched_inputs")
    if not isinstance(enriched_registry, dict):
        enriched_registry = {}
        state["storybrand_enriched_inputs"] = enriched_registry

    def record_enrichment(key: str, value: str, source: str) -> None:
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        info = {"value": value, "source": source, "timestamp_utc": timestamp}
        enriched_fields[key] = info
        enriched_registry[key] = info

    for key in REQUIRED_INPUT_KEYS:
        current_value = state.get(key)
        extracted_value: Optional[str] = None
        if parsed_result:
            entry = parsed_result.get(key)
            if isinstance(entry, dict):
                maybe_value = entry.get("value")
                if isinstance(maybe_value, str):
                    extracted_value = maybe_value.strip()

        sanitized_current = current_value.strip() if isinstance(current_value, str) else ""
        value = sanitized_current
        if not value and extracted_value:
            value = extracted_value
            state[key] = value
            record_enrichment(key, value, "llm")

        if key == "sexo_cliente_alvo":
            normalized = _normalize_gender(value)
            if normalized:
                state[key] = normalized
                if not sanitized_current and normalized != value:
                    record_enrichment(key, normalized, "llm")
                continue

            inferred = _infer_gender_from_context(state.get("landing_page_context"))
            if inferred:
                state[key] = inferred
                record_enrichment(key, inferred, "landing_page_context")
            else:
                errors.append("sexo_cliente_alvo inválido")
        else:
            if not value:
                errors.append(f"{key} ausente")
            else:
                state[key] = value

    if errors:
        detail = {"errors": errors, "enriched_fields": enriched_fields}
        _append_audit_event(state, stage="collector", status="error", section_key=None, iteration=None, details=detail)
        callback_context.events.append(
            Event(author="fallback_input_collector", actions=EventActions(escalate=True))
        )
        raise RuntimeError(
            "Fallback StoryBrand não pode continuar sem inputs essenciais: " + ", ".join(errors)
        )

    _append_audit_event(
        state,
        stage="collector",
        status="completed",
        section_key=None,
        iteration=None,
        details={
            "inputs": {key: state.get(key) for key in REQUIRED_INPUT_KEYS},
            "enriched_fields": enriched_fields,
        },
    )


fallback_input_collector = LlmAgent(
    model=FALLBACK_MODEL,
    name="fallback_input_collector",
    description="Confirma e normaliza os inputs essenciais do fallback StoryBrand.",
    instruction=PROMPT_LOADER.get_prompt("collector"),
    output_key="fallback_input_review",
    after_agent_callback=fallback_input_collector_callback,
)


class SectionReviewerAgent(BaseAgent):
    def __init__(
        self,
        *,
        section: StoryBrandSectionConfig,
        gender: str,
        iteration_key: str,
        review_key: str,
    ) -> None:
        super().__init__(name=f"{section.state_key}_reviewer")
        self._section = section
        self._gender = gender
        self._iteration_key = iteration_key
        self._review_key = review_key

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        iteration = int(state.get(self._iteration_key, 1))
        start = time.perf_counter()
        _append_audit_event(
            state,
            stage="reviewer",
            status="started",
            section_key=self._section.state_key,
            iteration=iteration,
            details=None,
        )
        _log_section_event(
            section_key=self._section.state_key,
            stage="reviewer",
            status="started",
            iteration=iteration,
            display_name=self._section.display_name,
        )

        prompt_path = self._section.review_prompt_paths[self._gender]
        instruction = PROMPT_LOADER.render_from_path(
            prompt_path,
            {
                "section_key": self._section.state_key,
                "current_text": state.get(self._section.state_key, ""),
                "o_que_a_empresa_faz": state.get("o_que_a_empresa_faz", ""),
            },
        )
        reviewer = LlmAgent(
            model=FALLBACK_MODEL,
            name=self.name,
            description=f"Revisa a seção {self._section.state_key} do StoryBrand.",
            instruction=instruction,
            output_schema=FallbackReviewResult,
            output_key=self._review_key,
        )
        async for event in reviewer.run_async(ctx):
            yield event

        duration = int((time.perf_counter() - start) * 1000)
        review = _coerce_review_result(state.get(self._review_key))
        state[self._review_key] = review.model_dump()
        status = "pass" if review.is_pass else "fail"
        _append_audit_event(
            state,
            stage="reviewer",
            status=status,
            section_key=self._section.state_key,
            iteration=iteration,
            details=review.comment,
            duration_ms=duration,
        )
        _log_section_event(
            section_key=self._section.state_key,
            stage="reviewer",
            status=status,
            iteration=iteration,
            comment=review.comment,
        )


class SectionApprovalChecker(BaseAgent):
    def __init__(
        self,
        *,
        section: StoryBrandSectionConfig,
        iteration_key: str,
        review_key: str,
        approved_flag_key: str,
    ) -> None:
        super().__init__(name=f"{section.state_key}_approval_checker")
        self._section = section
        self._iteration_key = iteration_key
        self._review_key = review_key
        self._approved_flag_key = approved_flag_key

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        iteration = int(state.get(self._iteration_key, 1))
        review = _coerce_review_result(state.get(self._review_key))
        state[self._approved_flag_key] = review.is_pass
        status = "approved" if review.is_pass else "retry"
        _append_audit_event(
            state,
            stage="checker",
            status=status,
            section_key=self._section.state_key,
            iteration=iteration,
            details=review.comment,
            duration_ms=0,
        )
        _log_section_event(
            section_key=self._section.state_key,
            stage="checker",
            status=status,
            iteration=iteration,
            comment=review.comment,
        )
        if review.is_pass:
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)


class SectionCorrectorAgent(BaseAgent):
    def __init__(
        self,
        *,
        section: StoryBrandSectionConfig,
        iteration_key: str,
        review_key: str,
        approved_flag_key: str,
    ) -> None:
        super().__init__(name=f"{section.state_key}_corrector")
        self._section = section
        self._iteration_key = iteration_key
        self._review_key = review_key
        self._approved_flag_key = approved_flag_key

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        iteration = int(state.get(self._iteration_key, 1))
        if state.get(self._approved_flag_key):
            _append_audit_event(
                state,
                stage="corrector",
                status="skipped",
                section_key=self._section.state_key,
                iteration=iteration,
                details="Seção aprovada; correção não necessária.",
                duration_ms=0,
            )
            _log_section_event(
                section_key=self._section.state_key,
                stage="corrector",
                status="skipped",
                iteration=iteration,
            )
            yield Event(author=self.name)
            return

        review = _coerce_review_result(state.get(self._review_key))
        start = time.perf_counter()
        _append_audit_event(
            state,
            stage="corrector",
            status="started",
            section_key=self._section.state_key,
            iteration=iteration,
            details=review.comment,
        )
        _log_section_event(
            section_key=self._section.state_key,
            stage="corrector",
            status="started",
            iteration=iteration,
            comment=review.comment,
        )
        instruction = PROMPT_LOADER.render_from_path(
            self._section.corrector_prompt_path,
            {
                "nome_empresa": state.get("nome_empresa", ""),
                "o_que_a_empresa_faz": state.get("o_que_a_empresa_faz", ""),
                "section_key": self._section.state_key,
                "current_text": state.get(self._section.state_key, ""),
                "review_comment": review.comment,
            },
        )
        corrector = LlmAgent(
            model=FALLBACK_MODEL,
            name=self.name,
            description=f"Corrige a seção {self._section.state_key} com base no feedback.",
            instruction=instruction,
            output_key=self._section.state_key,
        )
        async for event in corrector.run_async(ctx):
            yield event

        duration = int((time.perf_counter() - start) * 1000)
        _append_audit_event(
            state,
            stage="corrector",
            status="completed",
            section_key=self._section.state_key,
            iteration=iteration,
            details={"length": len(str(state.get(self._section.state_key, "")))},
            duration_ms=duration,
        )
        _log_section_event(
            section_key=self._section.state_key,
            stage="corrector",
            status="completed",
            iteration=iteration,
        )
        state[self._iteration_key] = iteration + 1
        yield Event(author=self.name)


class StoryBrandSectionRunner(BaseAgent):
    """Executes the 16 sections loop with review and correction."""

    def __init__(self, sections: Iterable[StoryBrandSectionConfig]) -> None:
        super().__init__(name="section_pipeline_runner")
        self._sections = list(sections)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        for section in self._sections:
            async for event in self._run_section(ctx, state, section):
                yield event
            yield Event(author=self.name)

    async def _run_section(
        self,
        ctx: InvocationContext,
        state: Dict[str, object],
        section: StoryBrandSectionConfig,
    ) -> AsyncGenerator[Event, None]:
        gender = _normalize_gender(state.get("sexo_cliente_alvo"))
        if gender not in {"masculino", "feminino"}:
            raise ValueError("sexo_cliente_alvo inválido para execução do fallback")
        iteration_key = f"{section.state_key}_iteration"
        review_key = f"{section.state_key}_review"
        approved_flag_key = f"{section.state_key}_approved"

        state[iteration_key] = 1
        state[approved_flag_key] = False
        state.pop(review_key, None)

        _log_section_event(
            section_key=section.state_key,
            stage="section",
            status="start",
            iteration=1,
            display_name=section.display_name,
        )

        approved_sections = {
            cfg.state_key: state.get(cfg.state_key)
            for cfg in self._sections
            if isinstance(state.get(cfg.state_key), str) and state.get(cfg.state_key)
        }
        approved_dump = json.dumps(approved_sections, ensure_ascii=False)
        preparer_details = {
            "display_name": section.display_name,
            "approved_sections": list(approved_sections.keys()),
        }
        _append_audit_event(
            state,
            stage="preparer",
            status="completed",
            section_key=section.state_key,
            iteration=1,
            details=preparer_details,
            duration_ms=0,
        )
        _log_section_event(
            section_key=section.state_key,
            stage="preparer",
            status="completed",
            iteration=1,
            approved_sections=list(approved_sections.keys()),
        )

        writer_instruction = PROMPT_LOADER.render_from_path(
            section.writer_prompt_path,
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
        writer_start = time.perf_counter()
        _append_audit_event(
            state,
            stage="writer",
            status="started",
            section_key=section.state_key,
            iteration=1,
            details=section.narrative_goal,
        )
        _log_section_event(
            section_key=section.state_key,
            stage="writer",
            status="started",
            iteration=1,
            narrative_goal=section.narrative_goal,
        )
        async for event in writer_agent.run_async(ctx):
            yield event
        writer_duration = int((time.perf_counter() - writer_start) * 1000)
        section_text = str(state.get(section.state_key, ""))
        _append_audit_event(
            state,
            stage="writer",
            status="completed",
            section_key=section.state_key,
            iteration=1,
            details={"length": len(section_text)},
            duration_ms=writer_duration,
        )
        _log_section_event(
            section_key=section.state_key,
            stage="writer",
            status="completed",
            iteration=1,
            length=len(section_text),
        )

        reviewer_agent = SectionReviewerAgent(
            section=section,
            gender=gender,
            iteration_key=iteration_key,
            review_key=review_key,
        )
        approval_checker = SectionApprovalChecker(
            section=section,
            iteration_key=iteration_key,
            review_key=review_key,
            approved_flag_key=approved_flag_key,
        )
        corrector_agent = SectionCorrectorAgent(
            section=section,
            iteration_key=iteration_key,
            review_key=review_key,
            approved_flag_key=approved_flag_key,
        )

        def _review_loop_failure_handler(callback_context: CallbackContext) -> None:
            if not bool(callback_context.state.get(approved_flag_key)):
                failure_iteration = int(callback_context.state.get(iteration_key, MAX_ITERATIONS))
                detail = {
                    "reason": "Limite de iterações atingido",
                    "max_iterations": MAX_ITERATIONS,
                    "last_review": callback_context.state.get(review_key),
                }
                _append_audit_event(
                    callback_context.state,
                    stage="checker",
                    status="error",
                    section_key=section.state_key,
                    iteration=failure_iteration,
                    details=detail,
                )
                _log_section_event(
                    section_key=section.state_key,
                    stage="checker",
                    status="error",
                    iteration=failure_iteration,
                    reason="max_iterations",
                )
                callback_context.events.append(
                    Event(author=f"{section.state_key}_review_loop", actions=EventActions(escalate=True))
                )
                raise RuntimeError(
                    f"Seção {section.state_key} não atingiu aprovação após {MAX_ITERATIONS} iterações."
                )

        review_loop = LoopAgent(
            name=f"{section.state_key}_review_loop",
            max_iterations=MAX_ITERATIONS,
            sub_agents=[reviewer_agent, approval_checker, corrector_agent],
            after_agent_callback=_review_loop_failure_handler,
        )

        async for event in review_loop.run_async(ctx):
            yield event

        state.pop(approved_flag_key, None)
        state.pop(iteration_key, None)


class FallbackQualityReporter(BaseAgent):
    """Persists aggregated metadata about the fallback execution."""

    def __init__(self) -> None:
        super().__init__(name="fallback_quality_reporter")

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        audit = state.get("storybrand_audit_trail")
        if not isinstance(audit, list):
            audit = []
        sections = SECTION_CONFIGS
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


class PersistStorybrandSectionsAgent(BaseAgent):
    """Persist StoryBrand sections generated during fallback execution."""

    def __init__(self) -> None:
        super().__init__(name="persist_storybrand_sections")

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        session_id = safe_session_id(ctx)
        user_id = safe_user_id(ctx)
        enabled = bool(getattr(config, "persist_storybrand_sections", False))

        if not enabled:
            log_struct_event(
                logger,
                event="storybrand_sections_persisted",
                storybrand_sections_persisted="skipped",
                session_id=session_id,
                user_id=user_id,
                has_gcs_upload=False,
                sections_count=0,
                reason="feature_flag_disabled",
            )
            yield Event(author=self.name)
            return

        sections_payload: Dict[str, str] = {}
        for cfg in SECTION_CONFIGS:
            sections_payload[cfg.state_key] = _sanitize_section_text(state.get(cfg.state_key)) or ""

        audit = state.get("storybrand_audit_trail")
        if not isinstance(audit, list):
            audit = [] if audit is None else [audit]
        enriched_inputs = state.get("storybrand_enriched_inputs")
        if not isinstance(enriched_inputs, dict):
            enriched_inputs = {}

        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        payload = {
            "sections": sections_payload,
            "audit": _safe_jsonable(audit),
            "enriched_inputs": _safe_jsonable(enriched_inputs),
            "timestamp_utc": timestamp,
        }

        base_dir = Path("artifacts/storybrand")
        _ensure_dir(base_dir)
        local_path = base_dir / f"{session_id}.json"
        with local_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

        state["storybrand_sections_saved_path"] = str(local_path)

        gcs_uri = ""
        deliveries_bucket_uri = os.getenv("DELIVERIES_BUCKET", "").strip()
        if deliveries_bucket_uri.startswith("gs://"):
            try:
                prefix = f"deliveries/{user_id}/{session_id}"
                gcs_dest = f"{prefix}/storybrand_sections.json"
                gcs_uri = _upload_to_gcs(
                    deliveries_bucket_uri,
                    gcs_dest,
                    json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to upload StoryBrand sections to GCS: %s", exc)
        else:
            if os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"):
                logger.warning(
                    "DELIVERIES_BUCKET is not configured; skipping StoryBrand sections "
                    "GCS upload in production."
                )

        if gcs_uri:
            state["storybrand_sections_gcs_uri"] = gcs_uri

        log_struct_event(
            logger,
            event="storybrand_sections_persisted",
            storybrand_sections_persisted="persisted",
            session_id=session_id,
            user_id=user_id,
            local_path=str(local_path),
            gcs_uri=gcs_uri,
            has_gcs_upload=bool(gcs_uri),
            sections_count=len(sections_payload),
        )

        yield Event(author=self.name)


fallback_storybrand_pipeline = SequentialAgent(
    name="fallback_storybrand_pipeline",
    description="Reconstrói a narrativa StoryBrand completa com loops de revisão.",
    sub_agents=[
        FallbackInputInitializer(),
        fallback_input_collector,
        StoryBrandSectionRunner(SECTION_CONFIGS),
        PersistStorybrandSectionsAgent(),
        FallbackStorybrandCompiler(),
        FallbackQualityReporter(),
    ],
)


__all__ = [
    "fallback_storybrand_pipeline",
    "FallbackInputInitializer",
    "StoryBrandSectionRunner",
    "PersistStorybrandSectionsAgent",
    "FallbackQualityReporter",
]
