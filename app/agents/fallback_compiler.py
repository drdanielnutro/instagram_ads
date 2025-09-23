"""
Fallback StoryBrand Compiler

Compila 16 seções narrativas do fallback em um objeto StoryBrandAnalysis (7 elementos),
persistindo também o summary e o ad_context no estado.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

from app.schemas.storybrand import (
    StoryBrandAnalysis,
    CharacterElement,
    ProblemElement,
    ProblemTypes,
    GuideElement,
    PlanElement,
    ActionElement,
    FailureElement,
    SuccessElement,
    StoryBrandMetadata,
)


logger = logging.getLogger(__name__)


def _get_str(state: Dict[str, Any], key: str) -> str:
    value = state.get(key)
    if isinstance(value, str):
        return value.strip()
    return ""


def _synthesize_problem_description(parts: List[str]) -> str:
    tokens: List[str] = [p.strip() for p in parts if isinstance(p, str) and p.strip()]
    if not tokens:
        return ""
    # Estratégia simples: unir sentenças curtas mantendo coerência mínima
    # Preferimos as duas primeiras evidências, depois adicionamos um sumário curto
    head = ". ".join(tokens[:2])
    tail = "" if len(tokens) <= 2 else " " + "; ".join(tokens[2:4])
    return (head + tail).strip()


def _split_steps(plan_text: str) -> List[str]:
    if not plan_text:
        return []
    # Tenta dividir por quebras de linha ou marcadores simples
    raw = [s.strip(" -•\t") for s in plan_text.replace("\r", "").split("\n")]
    steps = [s for s in raw if s]
    if steps:
        return steps[:6]
    # Fallback: dividir por ponto e ponto-e-vírgula
    import re

    parts = re.split(r"[.;]\s+", plan_text)
    return [p.strip() for p in parts if p.strip()][:6]


def _extract_ctas(action_text: str) -> tuple[str, str]:
    if not action_text:
        return "", ""
    lines = [l.strip(" -•\t") for l in action_text.replace("\r", "").split("\n")]
    lines = [l for l in lines if l]
    if not lines:
        return action_text.strip(), ""
    if len(lines) == 1:
        return lines[0], ""
    return lines[0], lines[1]


class FallbackStorybrandCompiler(BaseAgent):
    """Compila as 16 seções do fallback no schema StoryBrandAnalysis."""

    def __init__(self, name: str = "fallback_storybrand_compiler") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext):  # type: ignore[override]
        state = ctx.session.state

        # Coletar fontes das 16 seções (nomes padronizados)
        character_text = _get_str(state, "storybrand_character")
        exposition_1 = _get_str(state, "exposition_1")
        inciting_1 = _get_str(state, "inciting_incident_1")
        exposition_2 = _get_str(state, "exposition_2")
        inciting_2 = _get_str(state, "inciting_incident_2")
        unmet_needs = _get_str(state, "unmet_needs_summary")

        problem_external = _get_str(state, "storybrand_problem_external")
        problem_internal = _get_str(state, "storybrand_problem_internal")
        problem_philo = _get_str(state, "storybrand_problem_philosophical")

        guide_text = _get_str(state, "storybrand_guide")
        value_proposition = _get_str(state, "storybrand_value_proposition")

        plan_text = _get_str(state, "storybrand_plan")
        action_text = _get_str(state, "storybrand_action")
        failure_text = _get_str(state, "storybrand_failure")
        success_text = _get_str(state, "storybrand_success")
        identity_text = _get_str(state, "storybrand_identity")

        # Montar elementos
        character = CharacterElement(
            description=character_text,
            evidence=[character_text] if character_text else [],
            confidence=0.9 if character_text else 0.0,
        )

        problem_types = ProblemTypes(
            external=problem_external,
            internal=problem_internal,
            philosophical=problem_philo,
        )
        problem_evidence = [t for t in [problem_external, problem_internal, problem_philo] if t]
        problem_description = _synthesize_problem_description(
            [exposition_1, inciting_1, exposition_2, inciting_2, unmet_needs]
        )
        if not problem_description:
            # fallback mínimo
            problem_description = "; ".join([p for p in [problem_external, problem_internal, problem_philo] if p])
        problem = ProblemElement(
            description=problem_description,
            evidence=problem_evidence,
            types=problem_types,
            confidence=0.9 if (problem_description or problem_evidence) else 0.0,
        )

        # Guide: descrição composta de autoridade+empatia quando possível
        guide_authority = guide_text if guide_text else ""
        guide_empathy = ""
        guide_description_parts: List[str] = []
        if value_proposition:
            guide_description_parts.append(value_proposition)
        if guide_authority:
            guide_description_parts.append(guide_authority)
        guide_description = "; ".join([p for p in guide_description_parts if p])
        guide = GuideElement(
            description=guide_description or value_proposition or guide_text,
            authority=guide_authority,
            empathy=guide_empathy,
            evidence=[t for t in [value_proposition, guide_text] if t],
            confidence=0.85 if (guide_description or value_proposition or guide_text) else 0.0,
        )

        steps = _split_steps(plan_text)
        plan = PlanElement(
            description=plan_text or (steps[0] if steps else ""),
            steps=steps,
            evidence=[plan_text] if plan_text else [],
            confidence=0.85 if (plan_text or steps) else 0.0,
        )

        cta_primary, cta_secondary = _extract_ctas(action_text)
        action = ActionElement(
            primary=cta_primary,
            secondary=cta_secondary,
            evidence=[action_text] if action_text else [],
            confidence=0.8 if (cta_primary or cta_secondary) else 0.0,
        )

        failure = FailureElement(
            description=failure_text or (""),
            consequences=[failure_text] if failure_text else [],
            evidence=[failure_text] if failure_text else [],
            confidence=0.75 if failure_text else 0.0,
        )

        # Success: tentativa simples de separar benefícios; fallback coloca tudo como benefício único
        benefits: List[str] = []
        if success_text:
            lines = [l.strip(" -•\t") for l in success_text.replace("\r", "").split("\n")]
            benefits = [l for l in lines if l]
        success = SuccessElement(
            description=success_text or identity_text,
            benefits=benefits[:5] if benefits else ([success_text] if success_text else []),
            transformation=identity_text,
            evidence=[t for t in [success_text, identity_text] if t],
            confidence=0.85 if (success_text or identity_text) else 0.0,
        )

        metadata = StoryBrandMetadata(
            text_length=sum(len(s) for s in [
                character_text,
                exposition_1,
                inciting_1,
                exposition_2,
                inciting_2,
                unmet_needs,
                problem_external,
                problem_internal,
                problem_philo,
                guide_text,
                value_proposition,
                plan_text,
                action_text,
                failure_text,
                success_text,
                identity_text,
            ])
        )

        analysis = StoryBrandAnalysis(
            character=character,
            problem=problem,
            guide=guide,
            plan=plan,
            action=action,
            failure=failure,
            success=success,
            completeness_score=1.0,
            metadata=metadata,
        )

        # Persistir no estado: objeto validado + derivados
        state["storybrand_analysis"] = analysis.model_dump()
        state["storybrand_summary"] = analysis.to_summary()
        state["storybrand_ad_context"] = analysis.to_ad_context()

        # Sincronizar score com landing_page_context
        lp_ctx = state.get("landing_page_context")
        if isinstance(lp_ctx, dict):
            lp_ctx["storybrand_completeness"] = 1.0
            state["landing_page_context"] = lp_ctx

        # Relato breve
        yield Event(
            author=self.name,
            content=Content(parts=[Part(text="✅ Fallback StoryBrand compilado para StoryBrandAnalysis (score 1.0).")]),
        )


