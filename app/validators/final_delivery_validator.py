"""Deterministic validator for the final ad delivery payload."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part
from pydantic import ValidationError

from app.config import config
from app.schemas.final_delivery import StrictAdItem, model_dump
from app.utils.audit import append_delivery_audit_event
from app.utils.delivery_status import write_failure_meta
from app.utils.json_tools import try_parse_json_string


logger = logging.getLogger(__name__)


class FinalDeliveryValidatorAgent(BaseAgent):
    """Validate and normalize the final delivery JSON stored in the session state."""

    def __init__(self, name: str = "final_delivery_validator") -> None:
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        issues: list[str] = []
        normalized_payload: dict[str, Any] | None = None
        variations_data: list[dict[str, Any]] = []

        raw_delivery = state.get("final_code_delivery")
        logger.info("FinalDeliveryValidatorAgent: raw_delivery_type=%s", type(raw_delivery))

        try:
            variations_data = self._parse_variations(raw_delivery)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            issues.append(f"Erro ao ler final_code_delivery: {exc}")

        validated_variations: list[StrictAdItem] = []
        if not variations_data:
            if not issues:
                issues.append("final_code_delivery vazio ou ausente.")
        else:
            validated_variations, validation_issues = self._validate_variations(
                state=state, raw_variations=variations_data
            )
            issues.extend(validation_issues)

        if validated_variations:
            normalized_payload = model_dump(validated_variations)

        if normalized_payload:
            state["final_code_delivery_parsed"] = normalized_payload["variations"]

        grade = "pass" if not issues and normalized_payload else "fail"
        result: dict[str, Any] = {
            "grade": grade,
            "issues": issues,
            "normalized_payload": normalized_payload,
            "source": "validator",
        }
        state["deterministic_final_validation"] = result
        state["deterministic_final_blocked"] = grade != "pass"

        detail = "; ".join(issues[:3]) if issues else None
        append_delivery_audit_event(
            state,
            stage="deterministic_final_validation",
            status=grade,
            detail=detail,
            issue_count=len(issues),
        )

        if grade == "pass" and normalized_payload:
            state["final_code_delivery"] = json.dumps(
                normalized_payload["variations"], ensure_ascii=False
            )
            state.pop("deterministic_final_validation_failed", None)
            state.pop("deterministic_final_validation_failure_reason", None)
            message = "Validação determinística concluída com sucesso."
        else:
            state["deterministic_final_validation_failed"] = True
            failure_message = detail or "Validação determinística falhou."
            state["deterministic_final_validation_failure_reason"] = failure_message
            self._persist_failure_meta(ctx, failure_message, normalized_payload)
            message = f"❌ Validação determinística falhou: {failure_message}"

        yield Event(
            author=self.name,
            content=Content(parts=[Part(text=message)]),
        )

    def _parse_variations(self, raw: Any) -> list[dict[str, Any]]:
        if raw is None:
            raise ValueError("final_code_delivery ausente")

        if isinstance(raw, str):
            parsed, value = try_parse_json_string(raw)
            if parsed:
                raw = value
            else:
                raw = json.loads(raw)

        if isinstance(raw, dict):
            maybe_variations = raw.get("variations")
            if isinstance(maybe_variations, list):
                raw = maybe_variations

        if not isinstance(raw, list):
            raise TypeError("final_code_delivery deve ser uma lista de variações")

        variations: list[dict[str, Any]] = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                raise TypeError(
                    f"Variação na posição {idx} deve ser um objeto JSON."
                )
            variations.append(item)
        return variations

    def _validate_variations(
        self,
        *,
        state: dict[str, Any],
        raw_variations: list[dict[str, Any]],
    ) -> tuple[list[StrictAdItem], list[str]]:
        issues: list[str] = []
        validated: list[StrictAdItem] = []
        objective = (state.get("objetivo_final") or "").strip().lower()
        cta_by_objective = {
            key.lower(): value for key, value in config.cta_by_objective.items()
        }
        allowed_ctas = cta_by_objective.get(objective)

        if len(raw_variations) != 3:
            issues.append(
                f"Esperado 3 variações, recebido {len(raw_variations)}."
            )

        for idx, variation in enumerate(raw_variations):
            try:
                item = StrictAdItem(**variation)
            except ValidationError as exc:
                issues.append(f"Variação {idx}: {exc}")
                continue

            if allowed_ctas:
                if item.copy.cta_texto not in allowed_ctas:
                    issues.append(
                        f"Variação {idx}: CTA do texto não permitido para objetivo {objective}."
                    )
                if item.cta_instagram not in allowed_ctas:
                    issues.append(
                        f"Variação {idx}: CTA Instagram não permitido para objetivo {objective}."
                    )

            validated.append(item)

        duplicates = self._detect_duplicates(validated)
        issues.extend(duplicates)

        return validated, issues

    def _detect_duplicates(self, variations: list[StrictAdItem]) -> list[str]:
        issues: list[str] = []
        seen: dict[tuple[str, ...], int] = {}
        for idx, item in enumerate(variations):
            signature = (
                item.copy.headline.strip().lower(),
                item.copy.corpo.strip().lower(),
                item.visual.descricao_imagem.strip().lower(),
                item.visual.prompt_estado_atual.strip().lower(),
                item.visual.prompt_estado_intermediario.strip().lower(),
                item.visual.prompt_estado_aspiracional.strip().lower(),
            )
            previous = seen.get(signature)
            if previous is not None:
                issues.append(
                    f"Variações {previous} e {idx} duplicadas (headline/corpo/prompts)."
                )
            else:
                seen[signature] = idx
        return issues

    def _persist_failure_meta(
        self,
        ctx: InvocationContext,
        failure_message: str,
        normalized_payload: dict[str, Any] | None,
    ) -> None:
        state = ctx.session.state
        session_identifier = (
            str(getattr(ctx.session, "id", ""))
            or str(state.get("session_id") or "anonymous")
        )
        user_id = str(state.get("user_id") or "anonymous")
        extra = {"stage": "deterministic_final_validation"}
        if normalized_payload:
            extra["normalized_payload"] = normalized_payload

        write_failure_meta(
            session_id=session_identifier,
            user_id=user_id,
            reason="deterministic_final_validation_failed",
            message=failure_message,
            extra=extra,
        )

