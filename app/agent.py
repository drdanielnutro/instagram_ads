
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import contextlib
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from collections.abc import AsyncGenerator
from typing import Any, Dict, Literal

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import google_search, FunctionTool
from google.genai.types import Content, Part
from pydantic import BaseModel, Field, ValidationError

from .config import config
from .schemas.reference_assets import ReferenceImageMetadata
from .tools.generate_transformation_images import generate_transformation_images
from .tools.web_fetch import web_fetch_tool
from .utils.audit import append_delivery_audit_event
from .utils.json_tools import try_parse_json_string


logger = logging.getLogger(__name__)
from .agents.gating import RunIfPassed, ResetDeterministicValidationState
from .agents.storybrand_fallback import fallback_storybrand_pipeline
from .agents.storybrand_gate import StoryBrandQualityGate
from .callbacks.landing_page_callbacks import process_and_extract_sb7, enrich_landing_context_with_storybrand
from .callbacks.persist_outputs import (
    persist_final_delivery,
    sanitize_reference_images,
)
from .schemas.storybrand import StoryBrandAnalysis
from .validators.final_delivery_validator import FinalDeliveryValidatorAgent
from .utils.logging_helpers import log_struct_event


# ────────────────────────────────────────────────────────────────────────────────
# Structured Models
# ────────────────────────────────────────────────────────────────────────────────

class SearchQuery(BaseModel):
    search_query: str = Field(description="A highly specific and targeted query for web search.")


class Feedback(BaseModel):
    grade: Literal["pass", "fail"]
    comment: str
    follow_up_queries: list[SearchQuery] | None = None


# Modelos documentais para Ads (auxiliam reviewers/refiners; não são usados para serialização direta)
class AdCopy(BaseModel):
    headline: str
    corpo: str
    cta_texto: str


class AdVisual(BaseModel):
    descricao_imagem: str  # MUDANÇA: era descricao
    prompt_estado_atual: str  # Prompt técnico (inglês) para o estado de dor
    prompt_estado_intermediario: str  # Prompt técnico (inglês) para a ação imediata mantendo cenário/vestuário
    prompt_estado_aspiracional: str  # Prompt técnico (inglês) para o estado transformado
    aspect_ratio: Literal["9:16", "1:1", "4:5", "16:9"]
    # REMOVIDO: duracao (apenas imagens, sem vídeos)


class AdItem(BaseModel):
    landing_page_url: str
    formato: Literal["Reels", "Stories", "Feed"]
    copy: AdCopy  # Manter renomeado
    visual: AdVisual
    cta_instagram: Literal["Saiba mais", "Enviar mensagem", "Ligar", "Comprar agora", "Cadastre-se"]
    fluxo: str
    referencia_padroes: str
    contexto_landing: str  # NOVO CAMPO: contexto extraído da landing page


class ImplementationTask(BaseModel):
    """
    Ampliado para Ads sem quebrar compatibilidade com categorias pré-existentes de Flutter.
    """
    id: str
    category: Literal[
        # Legado Flutter:
        "MODEL", "PROVIDER", "WIDGET", "SERVICE", "UTIL",
        # Ads (alto rigor por etapa):
        "STRATEGY",          # diretrizes estratégicas (público, promessa, posicionamento)
        "RESEARCH",          # referências/padrões
        "COPY_DRAFT",        # rascunho de copy
        "COPY_QA",           # validação copy
        "VISUAL_DRAFT",      # rascunho de visual
        "VISUAL_QA",         # validação visual
        "COMPLIANCE_QA",     # validação de conformidade (políticas Instagram/saúde)
        "ASSEMBLY"           # montagem do JSON final
    ]
    title: str
    description: str
    file_path: str
    action: Literal["CREATE", "MODIFY", "EXTEND"]
    dependencies: list[str]


class ImplementationPlan(BaseModel):
    feature_name: str
    estimated_time: str
    implementation_tasks: list[ImplementationTask]


# ────────────────────────────────────────────────────────────────────────────────
# Callbacks utilitários
# ────────────────────────────────────────────────────────────────────────────────

def collect_code_snippets_callback(callback_context: CallbackContext) -> None:
    """
    Coleta/empilha fragmentos aprovados (podem ser JSONs parciais por categoria).
    """
    existing_snippets = callback_context.state.get("approved_code_snippets", [])
    code_snippets = list(existing_snippets)
    if "generated_code" in callback_context.state:
        task_info = callback_context.state.get("current_task_info", {}) or {}
        category = task_info.get("category", "UNKNOWN")
        snippet_type = str(category) if isinstance(category, str) else "UNKNOWN"
        task_id = task_info.get("id", "unknown")
        code_content = callback_context.state["generated_code"]
        snippet_payload = f"{task_id}::{snippet_type}::{code_content}".encode("utf-8")
        snippet_id = hashlib.sha256(snippet_payload).hexdigest()
        approved_at = datetime.now(timezone.utc).isoformat()
        code_snippets.append({
            "task_id": task_id,
            "category": category,
            "snippet_type": snippet_type,
            "status": "approved",
            "approved_at": approved_at,
            "snippet_id": snippet_id,
            "task_description": task_info.get("description", ""),
            "file_path": task_info.get("file_path", ""),
            "code": code_content
        })
    callback_context.state["approved_code_snippets"] = code_snippets

    visual_drafts = [
        {
            "snippet_id": snippet.get("snippet_id"),
            "task_id": snippet.get("task_id"),
            "approved_at": snippet.get("approved_at"),
            "code": snippet.get("code"),
            "status": snippet.get("status"),
            "snippet_type": snippet.get("snippet_type"),
        }
        for snippet in code_snippets
        if snippet.get("snippet_type") == "VISUAL_DRAFT" and snippet.get("status") == "approved"
    ]
    callback_context.state["approved_visual_drafts"] = visual_drafts


def unpack_extracted_input_callback(callback_context: CallbackContext) -> None:
    """
    Prepara estado a partir do extracted_input.
    Suporta novo formato (landing_page_url, objetivo_final, perfil_cliente) e legado.
    """
    if "extracted_input" not in callback_context.state:
        return

    raw = callback_context.state["extracted_input"]
    try:
        if isinstance(raw, str):
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            data = json.loads(raw)
        elif isinstance(raw, dict):
            data = raw
        else:
            return

        if isinstance(data, dict):
            for k, v in data.items():
                callback_context.state[k] = v

            # Compatibilidade com documentos legados (não usados em Ads, mas preservados)
            docs = {
                "ui_spec": callback_context.state.get("especificacao_tecnica_da_ui", "") or "",
                "api_context": callback_context.state.get("contexto_api", "") or "",
                "ux_truth": callback_context.state.get("fonte_da_verdade_ux", "") or "",
            }
            callback_context.state["original_docs"] = docs

            # Garante as novas chaves
            for k in ["landing_page_url", "objetivo_final", "perfil_cliente", "formato_anuncio", "foco"]:
                if k not in callback_context.state:
                    callback_context.state[k] = ""
    except (json.JSONDecodeError, IndexError):
        pass


def make_failure_handler(
    state_key: str,
    reason: str,
    *,
    expected_grades: tuple[str, ...] | str = ("pass",),
    failure_flag_key: str | None = None,
    failure_reason_key: str | None = None,
):
    if isinstance(expected_grades, str):
        expected_set = {expected_grades}
    else:
        expected_set = set(expected_grades)

    def _callback(callback_context: CallbackContext) -> None:
        state = callback_context.state
        result = state.get(state_key)
        grade: str | None
        if isinstance(result, dict):
            grade = result.get("grade")
        elif isinstance(result, str):
            grade = result
        else:
            grade = None

        if grade not in expected_set:
            flag_key = failure_flag_key or f"{state_key}_failed"
            reason_key = failure_reason_key or f"{state_key}_failure_reason"
            state[flag_key] = True
            if not state.get(reason_key):
                state[reason_key] = reason

            # Preserve legacy compatibility for final validation naming.
            if state_key == "semantic_visual_review":
                state.setdefault("final_validation_result_failed", True)
                if not state.get("final_validation_result_failure_reason"):
                    state["final_validation_result_failure_reason"] = state.get(reason_key, reason)

    return _callback


def task_execution_failure_handler(callback_context: CallbackContext) -> None:
    tasks = callback_context.state.get("implementation_tasks", [])
    idx = callback_context.state.get("current_task_index", 0)
    if idx < len(tasks):
        callback_context.state["task_execution_failed"] = True
        callback_context.state["task_execution_failure_reason"] = (
            "Limite de tentativas atingido antes de completar todas as tarefas."
        )


# ────────────────────────────────────────────────────────────────────────────────
# Agentes básicos de controle
# ────────────────────────────────────────────────────────────────────────────────

class EscalationChecker(BaseAgent):
    def __init__(self, name: str, review_key: str):
        super().__init__(name=name)
        self._review_key = review_key

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        result = ctx.session.state.get(self._review_key)
        if result and result.get("grade") == "pass":
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)


class TaskCompletionChecker(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        idx = ctx.session.state.get("current_task_index", 0)
        tasks = ctx.session.state.get("implementation_tasks", [])
        if idx >= len(tasks):
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)


class EscalationBarrier(BaseAgent):
    def __init__(self, name: str, agent: BaseAgent):
        super().__init__(name=name)
        self._agent = agent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for ev in self._agent.run_async(ctx):
            if ev.actions and ev.actions.escalate:
                ev.actions.escalate = False
            yield ev


class RunIfFailed(BaseAgent):
    """Runs the wrapped agent only if the given review key is not pass.

    Useful to avoid unnecessary refiner/fixer calls when a previous reviewer graded pass.
    """

    def __init__(self, name: str, review_key: str, agent: BaseAgent):
        super().__init__(name=name)
        self._review_key = review_key
        self._agent = agent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        result = ctx.session.state.get(self._review_key)
        grade = result.get("grade") if isinstance(result, dict) else None
        if grade == "pass":
            # Skip running the wrapped agent
            yield Event(author=self.name, content=Content(parts=[Part(text=f"Skipping {self._agent.name}; review passed.")]))
            return
        async for ev in self._agent.run_async(ctx):
            yield ev


class PlanningOrRunSynth(BaseAgent):
    """Runs only the synthesizer when a fixed plan is provided; otherwise runs full planning."""

    def __init__(self, synth_agent: BaseAgent, planning_agent: BaseAgent):
        super().__init__(name="planning_or_run_synth")
        self._synth = synth_agent
        self._planning = planning_agent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state
        if st.get("planning_mode") == "fixed" and st.get("implementation_plan"):
            # Run only the context synthesizer to build the briefing, then skip planning loop
            async for ev in self._synth.run_async(ctx):
                yield ev
            yield Event(author=self.name, content=Content(parts=[Part(text="Bypassed planning (fixed plan provided).")]))
            return
        # Run full planning (includes synthesizer + plan review loop)
        async for ev in self._planning.run_async(ctx):
            yield ev


class EnhancedStatusReporter(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state
        tasks = st.get("implementation_tasks", [])
        idx = st.get("current_task_index", 0)
        det_failed = st.get("deterministic_final_validation_failed")
        sem_failed = st.get("semantic_visual_review_failed")
        img_failed = st.get("image_assets_review_failed")
        det_review = st.get("deterministic_final_validation")
        det_grade = det_review.get("grade") if isinstance(det_review, dict) else det_review

        if det_failed:
            reason = st.get("deterministic_final_validation_failure_reason") or "Validação determinística reprovada."
            text = f"⚠️ **Validação Determinística** – {reason}"
        elif sem_failed:
            reason = st.get("semantic_visual_review_failure_reason") or "Revisão semântica reprovada."
            text = f"⚠️ **Revisão Semântica** – {reason}"
        elif img_failed:
            reason = st.get("image_assets_review_failure_reason") or "Geração de imagens reprovada."
            text = f"⚠️ **Revisão de Imagens** – {reason}"
        elif det_grade == "pending":
            text = "🧮 **Validação Determinística** – analisando JSON normalizado..."
        elif not tasks:
            text = "🔄 **FASE: PLANEJAMENTO** – preparando plano de tarefas (Ads)..."
        elif "final_code_delivery" in st:
            stage = st.get("final_delivery_status", {}).get("stage", "pipeline")
            grade = st.get("final_delivery_status", {}).get("grade")
            suffix = f" (estágio `{stage}`, nota `{grade}`)" if grade else ""
            text = f"✅ **PRONTO** – JSON final do anúncio disponível{suffix}."
        elif det_grade and det_grade not in ("pass", None):
            text = f"ℹ️ **Validação Determinística** – status `{det_grade}`."
        elif idx < len(tasks):
            progress = idx / len(tasks) if tasks else 0
            bar = "█" * int(progress * 10) + "░" * (10 - int(progress * 10))
            cur = tasks[idx]
            text = (
                f"🔧 **Tarefa {idx+1}/{len(tasks)}** [{bar}] {progress:.1%}\n"
                f"• {cur.get('title')}  \n"
                f"• Categoria: `{cur.get('category')}`  \n"
                f"• Ref: `{cur.get('file_path')}`"
            )
        else:
            text = "🧩 **Finalizando** – montagem/validação do JSON..."

        review_lines: list[str] = []
        for key, label in [
            ("deterministic_final_validation", "Validação determinística"),
            ("semantic_visual_review", "Revisão semântica"),
            ("image_assets_review", "Revisão de imagens"),
        ]:
            review = st.get(key)
            grade = review.get("grade") if isinstance(review, dict) else review
            if not grade:
                continue
            detail = grade
            if grade == "fail":
                reason = st.get(f"{key}_failure_reason")
                if not reason and isinstance(review, dict):
                    issues = review.get("issues")
                    if issues:
                        reason = issues[0]
                if reason:
                    detail = f"{grade} – {reason}"
            elif grade == "pending":
                detail = "pending…"
            review_lines.append(f"• {label}: `{detail}`")

        if review_lines:
            text = f"{text}\n\n" + "\n".join(review_lines)

        yield Event(author=self.name, content=Content(parts=[Part(text=text)]))


class ImageAssetsAgent(BaseAgent):
    """Gera e anexa imagens consistentes ao JSON final."""

    def __init__(self, name: str = "image_assets_agent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        # Debug: verificar o que está no state
        logger.info("ImageAssetsAgent: Keys in state: %s", list(state.keys()))
        logger.info(
            "ImageAssetsAgent: final_code_delivery exists: %s",
            "final_code_delivery" in state,
        )

        review = {
            "grade": "skipped",
            "issues": [],
            "summary": [],
            "source": self.name,
        }
        state["image_assets_review"] = review
        state.pop("image_assets_review_failed", None)

        reference_images_state = state.get("reference_images") or {}
        character_metadata: ReferenceImageMetadata | None = None
        product_metadata: ReferenceImageMetadata | None = None
        reference_parse_errors: list[str] = []

        if isinstance(reference_images_state, dict) and reference_images_state:
            character_payload = reference_images_state.get("character") or None
            if character_payload:
                try:
                    character_metadata = ReferenceImageMetadata.model_validate(
                        character_payload
                    )
                except ValidationError as exc:
                    reference_parse_errors.append(
                        f"character reference invalid: {exc.errors()}"
                    )
            product_payload = reference_images_state.get("product") or None
            if product_payload:
                try:
                    product_metadata = ReferenceImageMetadata.model_validate(
                        product_payload
                    )
                except ValidationError as exc:
                    reference_parse_errors.append(
                        f"product reference invalid: {exc.errors()}"
                    )

        if reference_parse_errors:
            review["issues"].extend(reference_parse_errors)
            logger.warning(
                "ImageAssetsAgent: invalid reference metadata detected: %s",
                reference_parse_errors,
            )

        state["character_reference_used"] = False
        state["product_reference_used"] = False

        safe_search_notes = state.get("reference_image_safe_search_notes")

        raw_delivery = state.get("final_code_delivery")

        # Fallback: tentar ler do arquivo se não estiver no state
        if not raw_delivery and state.get("final_delivery_local_path"):
            try:
                from pathlib import Path
                local_path = Path(state["final_delivery_local_path"])
                if local_path.exists():
                    with local_path.open("r", encoding="utf-8") as f:
                        raw_delivery = f.read()
                    logger.info(f"ImageAssetsAgent: Loaded JSON from file: {local_path}")
                    state["final_code_delivery"] = raw_delivery
            except Exception as exc:
                logger.warning(f"ImageAssetsAgent: Failed to load from file: {exc}")

        if not getattr(config, "enable_image_generation", True):
            review["issues"].append("Image generation disabled by configuration.")
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="skipped",
                detail="Image generation disabled",
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(
                    text="ℹ️ Geração de imagens desativada pela configuração ENABLE_IMAGE_GENERATION."
                )]),
            )
            return

        if not raw_delivery:
            review["issues"].append("Missing final_code_delivery payload; skipped image generation.")
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="skipped",
                detail="final_code_delivery ausente",
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text="ℹ️ JSON final ausente; geração de imagens não executada.")]),
            )
            return

        try:
            variations: list[Dict[str, Any]]
            if isinstance(raw_delivery, str):
                parsed, parsed_value = try_parse_json_string(raw_delivery)
                if not parsed:
                    parsed_value = json.loads(raw_delivery)
                variations = parsed_value
            elif isinstance(raw_delivery, list):
                variations = raw_delivery
            else:
                raise TypeError("Estrutura inesperada em final_code_delivery")
        except (json.JSONDecodeError, TypeError) as exc:
            message = f"❌ JSON final inválido para geração de imagens: {exc}"
            review["grade"] = "fail"
            review["issues"].append(str(exc))
            state["image_assets_review_failed"] = True
            state["image_assets_review_failure_reason"] = str(exc)
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="failed",
                detail=str(exc),
            )
            yield Event(author=self.name, content=Content(parts=[Part(text=message)]))
            return

        if not isinstance(variations, list) or not variations:
            review["issues"].append("Nenhuma variação encontrada para gerar imagens.")
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="skipped",
                detail="Nenhuma variação para processar",
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text="ℹ️ Nenhuma variação encontrada para gerar imagens.")]),
            )
            return

        total_variations = len(variations)
        user_id = str(state.get("user_id") or "anonymous")
        session_identifier = str(
            getattr(ctx.session, "id", "")
            or state.get("session_id")
            or "nosession"
        )

        sanitized_references = sanitize_reference_images(state)
        log_struct_event(
            logger,
            {
                "event": "image_assets_generation_start",
                "session_id": session_identifier,
                "user_id": user_id,
                "total_variations": total_variations,
                "character_reference_available": character_metadata is not None,
                "product_reference_available": product_metadata is not None,
                "reference_images_present": bool(sanitized_references),
                "reference_images": sanitized_references or None,
                "reference_parse_errors": reference_parse_errors or None,
                "safe_search_notes": safe_search_notes,
            },
        )

        summary: list[Dict[str, Any]] = []
        critical_errors: list[str] = []
        generated_any = False
        character_reference_used_overall = False
        product_reference_used_overall = False
        emotion_pattern = re.compile(r"Emotion:\s*([A-Za-z ]+)", re.IGNORECASE)
        emotion_fields = [
            "prompt_estado_atual",
            "prompt_estado_intermediario",
            "prompt_estado_aspiracional",
        ]

        for idx, variation in enumerate(variations):
            variation_number = idx + 1
            visual = variation.setdefault("visual", {}) or {}

            required_fields = [
                "prompt_estado_atual",
                "prompt_estado_intermediario",
                "prompt_estado_aspiracional",
            ]
            missing_fields = [field for field in required_fields if not visual.get(field)]
            if missing_fields:
                message = (
                    f"⚠️ Variação {variation_number}: campos ausentes para geração de imagens: "
                    + ", ".join(missing_fields)
                )
                visual["image_generation_error"] = message
                summary.append({
                    "variation_index": idx,
                    "status": "skipped",
                    "missing_fields": missing_fields,
                    "character_reference_used": False,
                    "product_reference_used": False,
                    "safe_search_notes": safe_search_notes,
                })
                review["issues"].append(
                    f"Variation {variation_number} skipped due to missing fields: {', '.join(missing_fields)}"
                )
                yield Event(author=self.name, content=Content(parts=[Part(text=message)]))
                continue

            yield Event(
                author=self.name,
                content=Content(parts=[Part(
                    text=f"🎨 Iniciando geração de imagens para variação {variation_number}/{total_variations}."
                )]),
            )

            progress_queue: asyncio.Queue[tuple[int, str]] = asyncio.Queue()

            async def progress_callback(stage_idx: int, stage_label: str) -> None:
                await progress_queue.put((stage_idx, stage_label))

            if character_metadata or product_metadata:
                reference_assets: Dict[str, Any] = {}
                if character_metadata:
                    reference_assets["character"] = {
                        "id": character_metadata.id,
                        "gcs_uri": character_metadata.gcs_uri,
                        "labels": character_metadata.labels,
                        "user_description": character_metadata.user_description,
                    }
                if product_metadata:
                    reference_assets["product"] = {
                        "id": product_metadata.id,
                        "gcs_uri": product_metadata.gcs_uri,
                        "labels": product_metadata.labels,
                        "user_description": product_metadata.user_description,
                    }
                if reference_assets:
                    visual["reference_assets"] = reference_assets
                else:
                    visual.pop("reference_assets", None)
            else:
                visual.pop("reference_assets", None)

            metadata = {
                "user_id": user_id,
                "session_id": session_identifier,
                "formato": variation.get("formato"),
                "aspect_ratio": visual.get("aspect_ratio"),
                "character_summary": state.get("reference_image_character_summary"),
                "product_summary": state.get("reference_image_product_summary"),
            }

            task = asyncio.create_task(
                generate_transformation_images(
                    prompt_atual=visual["prompt_estado_atual"],
                    prompt_intermediario=visual["prompt_estado_intermediario"],
                    prompt_aspiracional=visual["prompt_estado_aspiracional"],
                    variation_idx=idx,
                    metadata=metadata,
                    progress_callback=progress_callback,
                    reference_character=character_metadata,
                    reference_product=product_metadata,
                )
            )

            progress_task = asyncio.create_task(progress_queue.get())
            stage_labels = {
                1: "estado atual",
                2: "estado intermediário",
                3: "estado aspiracional",
            }

            assets: Dict[str, Any] | None = None
            error: str | None = None

            try:
                while True:
                    done, _ = await asyncio.wait(
                        {task, progress_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    if progress_task in done:
                        stage_idx, stage_label = progress_task.result()
                        pretty = stage_labels.get(stage_idx, stage_label)
                        yield Event(
                            author=self.name,
                            content=Content(parts=[Part(
                                text=f"✅ Variação {variation_number}: etapa {stage_idx}/3 ({pretty}) concluída."
                            )]),
                        )
                        progress_queue.task_done()
                        if task.done():
                            try:
                                assets = task.result()
                            except Exception as exc:  # pragma: no cover - depende de runtime externo
                                error = str(exc)
                            if progress_queue.empty():
                                break
                        else:
                            progress_task = asyncio.create_task(progress_queue.get())

                    if task in done:
                        try:
                            assets = task.result()
                        except Exception as exc:  # pragma: no cover - depende de runtime externo
                            error = str(exc)
                        break
            finally:
                if not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
                if progress_task and not progress_task.done():
                    progress_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await progress_task
                while not progress_queue.empty():
                    stage_idx, stage_label = await progress_queue.get()
                    pretty = stage_labels.get(stage_idx, stage_label)
                    yield Event(
                        author=self.name,
                        content=Content(parts=[Part(
                            text=f"✅ Variação {variation_number}: etapa {stage_idx}/3 ({pretty}) concluída."
                        )]),
                    )
                    progress_queue.task_done()

            if error or not assets:
                error_message = error or "Falha desconhecida na geração de imagens."
                visual["image_generation_error"] = error_message
                summary.append({
                    "variation_index": idx,
                    "status": "error",
                    "error": error_message,
                    "character_reference_used": False,
                    "product_reference_used": False,
                    "safe_search_notes": safe_search_notes,
                })
                critical_errors.append(error_message)
                review["issues"].append(
                    f"Erro ao gerar imagens da variação {variation_number}: {error_message}"
                )
                yield Event(
                    author=self.name,
                    content=Content(parts=[Part(
                        text=f"❌ Falha na geração de imagens da variação {variation_number}: {error_message}"
                    )]),
                )
                continue

            visual.pop("image_generation_error", None)
            visual["image_estado_atual_gcs"] = assets["estado_atual"]["gcs_uri"]
            visual["image_estado_atual_url"] = assets["estado_atual"].get("signed_url", "")
            visual["image_estado_intermediario_gcs"] = assets["estado_intermediario"]["gcs_uri"]
            visual["image_estado_intermediario_url"] = assets["estado_intermediario"].get("signed_url", "")
            visual["image_estado_aspiracional_gcs"] = assets["estado_aspiracional"]["gcs_uri"]
            visual["image_estado_aspiracional_url"] = assets["estado_aspiracional"].get("signed_url", "")
            assets_meta = assets.get("meta", {}) or {}
            if assets_meta:
                visual["image_generation_meta"] = assets_meta

            character_used = bool(assets_meta.get("reference_character_used"))
            product_used = bool(assets_meta.get("reference_product_used"))
            character_reference_used_overall = (
                character_reference_used_overall or character_used
            )
            product_reference_used_overall = (
                product_reference_used_overall or product_used
            )

            reference_errors: Dict[str, Any] = {}
            character_error = assets_meta.get("reference_character_error")
            product_error = assets_meta.get("reference_product_error")
            if character_error:
                reference_errors["character"] = character_error
                review["issues"].append(
                    f"Falha ao carregar referência de personagem: {character_error}"
                )
            if product_error:
                reference_errors["product"] = product_error
                review["issues"].append(
                    f"Falha ao carregar referência de produto: {product_error}"
                )

            emotions: Dict[str, str] = {}
            for field in emotion_fields:
                value = visual.get(field)
                if isinstance(value, str):
                    match = emotion_pattern.search(value)
                    if match:
                        emotions[field] = match.group(1).strip()

            summary.append({
                "variation_index": idx,
                "status": "ok",
                "assets": assets,
                "character_reference_used": character_used,
                "product_reference_used": product_used,
                "emotions": emotions,
                "safe_search_notes": safe_search_notes,
                "reference_errors": reference_errors or None,
            })
            generated_any = True

            yield Event(
                author=self.name,
                content=Content(parts=[Part(
                    text=f"🎉 Variação {variation_number}: imagens geradas e anexadas ao JSON."
                )]),
            )

        try:
            state["final_code_delivery"] = json.dumps(variations, ensure_ascii=False)
        except Exception as exc:  # pragma: no cover
            review["grade"] = "fail"
            review["issues"].append(str(exc))
            state["image_assets_review_failed"] = True
            state["image_assets_review_failure_reason"] = str(exc)
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="failed",
                detail="Erro ao serializar JSON final",
                error=str(exc),
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=f"❌ Erro ao serializar JSON final com imagens: {exc}")]),
            )
            return

        state["character_reference_used"] = character_reference_used_overall
        state["product_reference_used"] = product_reference_used_overall
        state["image_assets"] = summary

        if critical_errors:
            review["grade"] = "fail"
            state["image_assets_review_failed"] = True
            state["image_assets_review_failure_reason"] = "; ".join(review["issues"]) or "Falha na geração de imagens."
        elif generated_any:
            review["grade"] = "pass"
            state.pop("image_assets_review_failed", None)
            state.pop("image_assets_review_failure_reason", None)
        else:
            review["grade"] = "skipped"
            state.pop("image_assets_review_failed", None)
            state.pop("image_assets_review_failure_reason", None)

        review["summary"] = summary
        append_delivery_audit_event(
            state,
            stage=self.name,
            status=review["grade"],
            detail="Resumo da geração de imagens",
            summary=summary,
            issues=review["issues"],
        )

        log_struct_event(
            logger,
            {
                "event": "image_assets_generation_complete",
                "session_id": session_identifier,
                "user_id": user_id,
                "grade": review["grade"],
                "generated_variations": total_variations,
                "generated_any": generated_any,
                "critical_errors": critical_errors or None,
                "character_reference_used": character_reference_used_overall,
                "product_reference_used": product_reference_used_overall,
                "reference_images_present": bool(sanitized_references),
                "reference_images": sanitized_references or None,
                "reference_parse_errors": reference_parse_errors or None,
                "safe_search_notes": safe_search_notes,
            },
        )

        deterministic_flag = bool(getattr(config, "enable_deterministic_final_validation", False))
        if not deterministic_flag:
            try:
                persist_final_delivery(ctx)
            except Exception as exc:  # pragma: no cover - persistência externa
                logger.error(
                    "Falha ao persistir JSON atualizado com imagens: %s", exc, exc_info=True
                )
                yield Event(
                    author=self.name,
                    content=Content(parts=[Part(
                        text="⚠️ Imagens geradas, mas houve erro ao persistir a entrega final.""\n" + str(exc)
                    )]),
                )
                return

        if summary:
            summary_text = "\n".join(
                f"• Variação {item['variation_index'] + 1}: {item['status']}" for item in summary
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(
                    text=(
                        "📊 Resultado da geração de imagens:\n" + summary_text
                    )
                )]),
            )
        else:
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text="ℹ️ Nenhuma imagem gerada.")]),
            )

        if review["grade"] == "pass":
            sucesso = sum(1 for item in summary if item.get("status") == "ok")
            yield Event(
                author=self.name,
                content=Content(parts=[Part(
                    text=f"✅ Imagens geradas e salvas (variações bem-sucedidas: {sucesso}/{total_variations})."
                )]),
            )

class TaskInitializer(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        impl = ctx.session.state.get("implementation_plan", {}) or {}
        tasks = impl.get("implementation_tasks", []) or []
        ctx.session.state["implementation_tasks"] = tasks
        ctx.session.state["current_task_index"] = 0
        ctx.session.state["total_tasks"] = len(tasks)
        ctx.session.state["approved_code_snippets"] = []
        yield Event(author=self.name)


class TaskManager(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        idx = ctx.session.state.get("current_task_index", 0)
        tasks = ctx.session.state.get("implementation_tasks", [])
        if idx < len(tasks):
            current = tasks[idx]
            ctx.session.state["current_task_info"] = current
            ctx.session.state["current_task_description"] = current["description"]
            yield Event(author=self.name, content=Content(parts=[Part(text=f"Starting task: {current['title']}")]))
        else:
            yield Event(author=self.name, actions=EventActions(escalate=True))


class TaskIncrementer(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        ctx.session.state["current_task_index"] = ctx.session.state.get("current_task_index", 0) + 1
        yield Event(author=self.name)


# ────────────────────────────────────────────────────────────────────────────────
# LANDING PAGE ANALYZER - Extração de conteúdo da página de destino
# ────────────────────────────────────────────────────────────────────────────────

landing_page_analyzer = LlmAgent(
    model=config.worker_model,
    name="landing_page_analyzer",
    description="Extrai e analisa conteúdo real da landing page com framework StoryBrand",
    instruction="""
## IDENTIDADE: Landing Page Analyzer com StoryBrand

Você analisa a URL fornecida extraindo o conteúdo REAL da página e aplicando análise StoryBrand.

## ENTRADA
- landing_page_url: {landing_page_url}
- foco (opcional): {foco}

## PROCESSO
1. Use a ferramenta web_fetch_tool para fazer o download completo do HTML da página
2. A ferramenta automaticamente aplicará análise StoryBrand ao conteúdo
3. Com base no conteúdo extraído e análise StoryBrand, compile as informações:
   - Título principal (H1/headline) - do HTML real
   - Proposta de valor única - baseada no StoryBrand Guide
   - Lista de benefícios principais - do StoryBrand Success
   - CTAs (call-to-actions) - do StoryBrand Action
   - Preços/ofertas especiais - extraídos do HTML
   - Provas sociais - autoridade do StoryBrand Guide
   - Tom de voz da marca - análise do texto
   - Palavras-chave principais - do conteúdo real
   - Diferenciais competitivos - do StoryBrand
   - Persona do cliente - do StoryBrand Character
   - Problemas/dores - do StoryBrand Problem
   - Transformação prometida - do StoryBrand Success

## ANÁLISE STORYBRAND DISPONÍVEL
Após o fetch, você terá acesso a:
- storybrand_analysis: Análise completa dos 7 elementos
- storybrand_summary: Resumo textual
- storybrand_ad_context: Contexto otimizado para anúncios

## SAÍDA (JSON)
{
  "landing_page_context": {
    "titulo_principal": "string (extraído do HTML real)",
    "proposta_valor": "string (baseado no StoryBrand)",
    "beneficios": ["do Success do StoryBrand"],
    "ctas_principais": ["do Action do StoryBrand"],
    "ofertas": "string",
    "provas_sociais": "string (autoridade do Guide)",
    "tom_voz": "string",
    "palavras_chave": ["do conteúdo real"],
    "diferenciais": ["do StoryBrand"],
    "persona_cliente": "do Character do StoryBrand",
    "problemas_dores": ["do Problem do StoryBrand"],
    "transformacao": "do Success do StoryBrand",
    "storybrand_completeness": "score de 0-1"
  }
}

IMPORTANTE: Use web_fetch_tool, NÃO google_search. O conteúdo deve vir do HTML real da página.
Observação: se houver um "foco" (ex.: campanha sazonal, liquidação), priorize mensagens, benefícios e CTAs relacionados a esse foco sem contrariar o conteúdo real da página.
""",
    tools=[FunctionTool(func=web_fetch_tool)],
    after_tool_callback=process_and_extract_sb7,  # Singular, sem lista
    output_key="landing_page_context"
)


class LandingPageStage(BaseAgent):
    """Wrapper that skips landing page analysis when fallback is forced."""

    def __init__(self, landing_page_agent: BaseAgent) -> None:
        super().__init__(name="landing_page_stage")
        self._landing_page_agent = landing_page_agent

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:  # type: ignore[override]
        state = ctx.session.state
        state["landing_page_analysis_failed"] = False
        fallback_enabled = bool(
            getattr(config, "enable_storybrand_fallback", False)
            and getattr(config, "enable_new_input_fields", False)
        )
        force_flag = bool(state.get("force_storybrand_fallback"))
        debug_flag = bool(getattr(config, "storybrand_gate_debug", False))

        if fallback_enabled and (force_flag or debug_flag):
            if not isinstance(state.get("landing_page_context"), dict):
                state["landing_page_context"] = {}
            state["landing_page_analysis_failed"] = True
            logger.info(
                "storybrand_landing_page_skipped",
                extra={
                    "reason": "forced_fallback",
                    "force_flag": force_flag,
                    "debug_flag": debug_flag,
                },
            )
            return

        async for event in self._landing_page_agent.run_async(ctx):
            yield event

        landing_ctx = state.get("landing_page_context")
        if not isinstance(landing_ctx, dict) or not landing_ctx:
            state["landing_page_analysis_failed"] = True


image_assets_agent = ImageAssetsAgent()


# ────────────────────────────────────────────────────────────────────────────────
# PLANEJAMENTO (Ads) – mantém estilo "tarefas a executar"
# ────────────────────────────────────────────────────────────────────────────────

context_synthesizer = LlmAgent(
    model=config.worker_model,
    name="context_synthesizer",
    description="Sintetiza entrada para briefing de anúncio Instagram com insights StoryBrand.",
    instruction="""
## IDENTIDADE: Context Synthesizer (Ads) com StoryBrand

Sua missão (tarefas):
1) Consolidar as entradas:
   - landing_page_url: {landing_page_url}
   - objetivo_final: {objetivo_final}
   - perfil_cliente: {perfil_cliente}
   - foco (opcional): {foco}
   - landing_page_context: {landing_page_context}
   - storybrand_analysis: {storybrand_analysis}
   - storybrand_ad_context: {storybrand_ad_context}
   - formato_anuncio: {formato_anuncio}

2) INTEGRAR elementos StoryBrand no briefing:
   - Persona: Combinar {perfil_cliente} com Character do StoryBrand
   - Dores: Usar os 3 níveis de Problem (external, internal, philosophical)
   - Guia: Posicionar marca com Authority e Empathy
   - Plano: Simplificar Plan em 3 passos claros
   - Ação: Destacar CTAs do Action
   - Urgência: Usar Failure para criar senso de urgência
   - Transformação: Usar Success como promessa principal

3) Formato definido pelo usuário: {formato_anuncio} - criar estratégia específica
4) Apontar restrições/políticas relevantes (Instagram e, se aplicável, saúde/medicina)
5) Produzir briefing 100% ALINHADO com conteúdo REAL da landing page

## SAÍDA (modelo)
ADS FEATURE BRIEFING
- Persona: [Character do StoryBrand + perfil_cliente]
- Dores Principais: [Problem - external, internal, philosophical]
- Nossa Posição: [Guide - autoridade + empatia]
- Benefícios/Transformação: [Success do StoryBrand]
- Plano Simplificado: [3 passos do Plan]
- CTAs Principais: [Action - primário e secundário]
- Urgência: [Failure - o que evitar]
- Objetivo: {objetivo_final}
- Formato: {formato_anuncio}
- Mensagens-chave: [baseadas no conteúdo real]
- Restrições: [políticas Instagram]
- StoryBrand Score: [completeness_score]
""",
    after_agent_callback=enrich_landing_context_with_storybrand,  # Singular
    output_key="feature_briefing",
)

feature_planner = LlmAgent(
    model=config.worker_model,
    name="feature_planner",
    description="Cria um plano detalhado e sequenciado de tarefas para Ads.",
    output_schema=ImplementationPlan,
    instruction="""
## IDENTIDADE: Marketing Tech Lead

Tarefas a executar:
1) Gerar um plano **atômico** (15–30min por tarefa) usando **EXATAMENTE** as categorias:
   STRATEGY → RESEARCH → COPY_DRAFT → COPY_QA → VISUAL_DRAFT → VISUAL_QA → COMPLIANCE_QA → ASSEMBLY
2) Incluir dependências corretas (ex.: COPY_QA depende de COPY_DRAFT).
3) Preencher `file_path` (placeholder) para compatibilidade, ex.: "ads/TASK-002.json".
4) O plano deve convergir para um **único JSON final** conforme o schema do projeto.
5) Se houver "foco" (tema/gancho de campanha), inclua-o como critério de direção nas tarefas de STRATEGY/COPY/ASSEMBLY.

## ENTRADA
{feature_briefing}

## SAÍDA (Pydantic)
- feature_name
- estimated_time
- implementation_tasks: lista de objetos ImplementationTask
""",
    output_key="implementation_plan",
)

plan_reviewer = LlmAgent(
    model=config.critic_model,
    name="plan_reviewer",
    description="Revisa completude, sequência, granularidade e aderência ao objetivo (Ads).",
    instruction="""
## IDENTIDADE: Principal Ads Strategist

Avalie o plano:
- Completude (todas as categorias requeridas)
- Sequência lógica e dependências
- Granularidade (15–30min)
- Clareza (títulos e descrições acionáveis)
- Aderência ao objetivo_final: {objetivo_final}
- Aderência ao foco (se informado): {foco}

## SAÍDA
{"grade":"pass"|"fail","comment":"...","follow_up_queries":[{"search_query":"..."}]}
""",
    output_schema=Feedback,
    output_key="plan_review_result",
)


# ────────────────────────────────────────────────────────────────────────────────
# EXECUÇÃO (Ads) – mantém nomes dos agentes geradores/avaliadores/refinadores
# ────────────────────────────────────────────────────────────────────────────────

code_generator = LlmAgent(
    model=config.worker_model,
    name="code_generator",  # mantido
    description="Gera fragmentos JSON por tarefa de Ads.",
    instruction="""
## IDENTIDADE: Senior Ads Content Developer

Contexto:
- Briefing: {feature_briefing}
- landing_page_url: {landing_page_url}
- objetivo_final: {objetivo_final}
- perfil_cliente: {perfil_cliente}
- foco: {foco}
- landing_page_context: {landing_page_context}
- formato_anuncio: {formato_anuncio}
 - format_specs: {format_specs_json}
- Task atual: {current_task_info}

Regras gerais:
- **Saída sempre em JSON válido**, sem markdown/comentários.
- pt-BR e adequado a Instagram.
- Evite alegações médicas indevidas e promessas irrealistas.
- Quando "foco" for fornecido (tema/gancho da campanha), direcione headline/corpo/CTA e elementos visuais para refletir esse foco.
 - Respeite as especificações do formato em {format_specs_json} (ex.: aspect_ratio, limites de caracteres/tom da copy, aparência nativa do formato).

Formatação por categoria (retorne somente o fragmento daquela categoria):

- STRATEGY:
  {
    "mensagens_chave": ["...", "..."],
    "posicionamento": "...",
    "promessa_central": "...",
    "diferenciais": ["...", "..."]
  }

- RESEARCH:
  {
    "referencia_padroes": "Padrões de criativos com alta performance (Brasil, 2024–2025): ... (síntese objetiva)"
  }

- COPY_DRAFT:
  {
    "copy": {
      "headline": "...",
      "corpo": "...",
      "cta_texto": "..."
    },
    "cta_instagram": "Saiba mais" | "Enviar mensagem" | "Ligar" | "Comprar agora" | "Cadastre-se"
  }
  Referências aprovadas disponíveis:
  - Personagem: {reference_image_character_summary}
  - Produto/serviço: {reference_image_product_summary}
  Diretrizes condicionais:
  - Se houver personagem aprovado, alinhe a narrativa à descrição real e mantenha tom consistente com as imagens.
  - Se somente o produto existir, destaque atributos reais e **não invente** personagens ou histórias não fornecidas.
  - Quando ambos estiverem presentes, conecte persona e produto de forma coerente nas três variações.

- COPY_QA:
  {
    "validacao_copy": "ok|ajustar: <motivo>",
    "ajustes_copy_sugeridos": "..."
  }

- VISUAL_DRAFT:
  {
    "visual": {
      "descricao_imagem": "OBRIGATÓRIO: descreva em pt-BR uma sequência de três cenas numeradas (1, 2, 3) com a mesma persona vivenciando: 1) o estado atual com dor ou frustração específica, 2) o estado intermediário mostrando a decisão ou primeiro passo mantendo cenário/vestuário coerentes, 3) o estado aspiracional depois da transformação. Nunca mencione 'imagem única' nem omita cenas. Inclua menções explícitas ao personagem/produto real quando `reference_images` estiverem disponíveis e registre notas do SafeSearch: {reference_image_safe_search_notes}.",
      "prompt_estado_atual": "OBRIGATÓRIO: prompt técnico em inglês descrevendo somente a cena 1 (estado atual), com emoção negativa clara, postura coerente e cenário alinhado ao problema, sempre com a mesma persona. Se {reference_image_character_summary} existir, preserve traços físicos (tom de pele, cabelo, formato do rosto) e cite explicitamente que se trata da mesma pessoa. Termine com `Emotion: despair` para rastrear a expressão aplicada.",
      "prompt_estado_intermediario": "OBRIGATÓRIO: prompt técnico em inglês descrevendo somente a cena 2 (estado intermediário), destacando o momento de ação ou decisão, mantendo persona, cenário e elementos visuais em transição positiva. Use `Emotion: determined` no final e, quando houver produto aprovado ({reference_image_product_summary}), destaque sua presença sem alterar identidade da persona.",
      "prompt_estado_aspiracional": "OBRIGATÓRIO: prompt técnico em inglês descrevendo somente a cena 3 (estado aspiracional), mostrando resultados visíveis, emoções positivas e ambiente coerente com o sucesso da mesma persona. Se houver produto aprovado, instrua a cena a integrar o item real. Finalize com `Emotion: joyful` para permitir auditoria.",
      "aspect_ratio": "definido conforme especificação do formato"
    },
    "formato": "{formato_anuncio}"  # Usar o especificado pelo usuário
  }

  Referências visuais disponíveis:
  - Personagem: {reference_image_character_summary}
  - Produto: {reference_image_product_summary}
  - SafeSearch: {reference_image_safe_search_notes}

  ```markdown
  if reference_image_character_summary:
      prompt_visual = (
          "Describe the same {reference_image_character_summary} person, preserve skin tone, hair texture, facial structure;"
          " adapt expression to each stage (Emotion: despair → Emotion: determined → Emotion: joyful)."
      )
  else:
      prompt_visual = original_visual_draft_instruction
  ```

  Se qualquer campo do bloco "visual" ficar vazio, nulo ou repetir outra cena, regenere o fragmento antes de responder.

- VISUAL_QA:
  {
    "validacao_visual": "ok|ajustar: <motivo>",
    "ajustes_visual_sugeridos": "..."
  }

- COMPLIANCE_QA:
  {
    "conformidade": "ok|ajustar: <motivo>",
    "observacoes_politicas": "Resumo objetivo de riscos e como mitigar"
  }

- ASSEMBLY:
  {
    "obrigatorio": ["landing_page_url","formato","copy","visual","cta_instagram","fluxo","referencia_padroes"]
  }
""",
    output_key="generated_code",
)

code_reviewer = LlmAgent(
    model=config.critic_model,
    name="code_reviewer",  # mantido
    description="Revisa o fragmento JSON de acordo com a categoria atual.",
    instruction="""
## IDENTIDADE: Principal Ads Reviewer

Analise {generated_code} para a tarefa {current_task_info}. 
VALIDE ALINHAMENTO com {landing_page_context} e CONFORMIDADE com {format_specs_json}

Aplique critérios **por categoria**:

- ALINHAMENTO_LP:
  * Copy consistente com landing page?
  * Benefícios mencionados existem na página?
  * Tom de voz alinhado?
 
- ALINHAMENTO_FOCO (se {foco} informado):
  * Headline/CTA/mensagens refletem o foco declarado?
  * Não desviar do tema (ex.: "liquidação de inverno").

- STRATEGY:
  * Mensagens claras e coerentes com {objetivo_final} e {perfil_cliente}
  * Nada vago ou genérico

- RESEARCH:
  * Referência alinhada a Brasil 2024–2025
  * Útil (insights aplicáveis), sem "lorem ipsum"

- COPY_DRAFT:
  * Headline específica e benefício claro
  * Corpo objetivo, sem promessas irreais/alegações médicas indevidas
  * CTA coerente com {objetivo_final} e com a landing_page_url
  * VALIDAR: Conteúdo alinhado com {landing_page_context}
  * Respeitar limites/estilo definidos em {format_specs_json} (ex.: headline curta em Reels/Stories)

- COPY_QA:
  * Avaliação honesta; se "ajustar", razões acionáveis

- VISUAL_DRAFT:
  * Verificar que a descricao_imagem explicita três cenas distintas (estado atual, intermediário e aspiracional) da mesma persona; reprovar se aparecer "imagem única" ou menção a apenas uma cena.
  * Reprovar automaticamente se qualquer `prompt_estado_*` estiver ausente, vazio, nulo, repetido ou incoerente com a cena correspondente; informe qual campo precisa ser corrigido.
  * Garantir continuidade narrativa entre os três prompts (mesma persona, cenário evoluindo de dor → decisão → transformação) e que cada um descreve apenas a sua cena.
  * Conferir se o aspect_ratio segue {format_specs_json} e se o conteúdo é acionável para geração de imagem.

- VISUAL_QA:
  * Avaliação honesta; se "ajustar", razões acionáveis
  * Confirmar que descricao_imagem e os três prompts (estado atual, estado intermediario e aspiracional) são consistentes, verossímeis e acionáveis para IA

- COMPLIANCE_QA:
  * Checagem de conformidade (Instagram; se saúde/medicina, tom responsável)
  * Sem termos proibidos

- ASSEMBLY:
  * Lista "obrigatorio" contempla todas as chaves exigidas

## SAÍDA
{"grade":"pass"|"fail","comment":"...","follow_up_queries":[{"search_query":"..."}]}
""",
    output_schema=Feedback,
    output_key="code_review_result",
)

code_refiner = LlmAgent(
    model=config.worker_model,
    name="code_refiner",  # mantido
    description="Refina o fragmento conforme o review; usa busca quando necessário.",
    instruction="""
## IDENTIDADE: Ads Refinement Specialist

Tarefas:
1) Aplique TODAS as correções do review {code_review_result} ao fragmento {generated_code}.
2) Se houver `follow_up_queries`, execute-as via `google_search` e incorpore boas práticas.
3) Retorne o **mesmo fragmento** corrigido em **JSON válido**.

Se o review apontar ausência ou inconsistência em `prompt_estado_atual`, `prompt_estado_intermediario` ou `prompt_estado_aspiracional`, complete cada campo antes de responder. Utilize {landing_page_context}: dores e obstáculos alimentam o estado atual, proposta/CTA alimenta o estado intermediário e benefícios/transformação alimentam o estado aspiracional. Nunca devolva campos vazios; se não for possível completar, explique o motivo ao revisor.
""",
    tools=[google_search],
    output_key="generated_code",
)

code_approver = LlmAgent(
    model=config.worker_model,
    name="code_approver",  # mantido
    description="Registra fragmento aprovado no estado.",
    instruction="""
## IDENTIDADE: Code Approval Manager

Confirme registro:
- Task: {current_task_info}
- JSON: {generated_code}

Responda com confirmação simples.
""",
    output_key="approval_confirmation",
    after_agent_callback=collect_code_snippets_callback,
)


class FinalAssemblyGuardPre(BaseAgent):
    """Valida a presença de snippets VISUAL_DRAFT antes da montagem final."""

    def __init__(self, name: str = "final_assembly_guard_pre") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        snippets = state.get("approved_code_snippets") or []
        visual_snippets: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        issues: list[str] = []

        for snippet in snippets:
            if not isinstance(snippet, dict):
                continue
            if snippet.get("snippet_type") != "VISUAL_DRAFT":
                continue
            if snippet.get("status") != "approved":
                continue
            snippet_id = str(
                snippet.get("snippet_id")
                or snippet.get("task_id")
                or f"snippet-{len(visual_snippets)}"
            )
            if snippet_id in seen_ids:
                issues.append(f"Snippet VISUAL_DRAFT duplicado: {snippet_id}")
                continue
            seen_ids.add(snippet_id)
            code = snippet.get("code")
            if not code:
                issues.append(f"Snippet {snippet_id} sem conteúdo.")
                continue
            normalized_code = code
            parsed, parsed_value = try_parse_json_string(code)
            if parsed and parsed_value is not None:
                try:
                    normalized_code = json.dumps(parsed_value, ensure_ascii=False)
                except (TypeError, ValueError):
                    normalized_code = code
            visual_snippets.append(
                {
                    "snippet_id": snippet_id,
                    "task_id": snippet.get("task_id"),
                    "approved_at": snippet.get("approved_at"),
                    "code": normalized_code,
                    "status": snippet.get("status"),
                    "snippet_type": snippet.get("snippet_type"),
                }
            )

        if issues or not visual_snippets:
            if not visual_snippets:
                issues.append("Nenhum snippet VISUAL_DRAFT aprovado disponível.")
            detail = "; ".join(issues)
            state["approved_visual_drafts"] = []
            state["deterministic_final_validation"] = {
                "grade": "fail",
                "issues": issues,
                "source": "guard",
            }
            state["deterministic_final_blocked"] = True
            state["deterministic_final_validation_failed"] = True
            state["deterministic_final_validation_failure_reason"] = detail
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="failed",
                detail=detail,
                issues=issues,
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=f"❌ Guard do assembler bloqueou execução: {detail}")]),
                actions=EventActions(escalate=True),
            )
            return

        state["approved_visual_drafts"] = visual_snippets
        state["deterministic_final_blocked"] = False
        state.pop("deterministic_final_validation_failed", None)
        state.pop("deterministic_final_validation_failure_reason", None)
        append_delivery_audit_event(
            state,
            stage=self.name,
            status="passed",
            detail=f"{len(visual_snippets)} VISUAL_DRAFT aprovados.",
        )
        yield Event(
            author=self.name,
            content=Content(
                parts=[Part(text=f"✅ {len(visual_snippets)} VISUAL_DRAFT aprovados prontos para montagem.")]
            ),
        )


class FinalAssemblyNormalizer(BaseAgent):
    """Normaliza a saída do assembler e prepara estado para validação determinística."""

    def __init__(self, name: str = "final_assembly_normalizer") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        raw_payload = state.get("final_code_delivery")

        if not raw_payload:
            detail = "final_code_delivery ausente após montagem."
            state["deterministic_final_validation"] = {
                "grade": "fail",
                "issues": [detail],
                "source": "normalizer",
            }
            state["deterministic_final_blocked"] = True
            state["deterministic_final_validation_failed"] = True
            state["deterministic_final_validation_failure_reason"] = detail
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="failed",
                detail=detail,
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=f"❌ Normalização falhou: {detail}")]),
                actions=EventActions(escalate=True),
            )
            return

        try:
            if isinstance(raw_payload, str):
                parsed, parsed_value = try_parse_json_string(raw_payload)
                if not parsed:
                    parsed_value = json.loads(raw_payload)
                variations = parsed_value
            elif isinstance(raw_payload, list):
                variations = raw_payload
            else:
                raise TypeError("Estrutura inesperada recebida pelo normalizer")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            detail = f"Payload inválido: {exc}"
            state["deterministic_final_validation"] = {
                "grade": "fail",
                "issues": [detail],
                "source": "normalizer",
            }
            state["deterministic_final_blocked"] = True
            state["deterministic_final_validation_failed"] = True
            state["deterministic_final_validation_failure_reason"] = detail
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="failed",
                detail=detail,
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=f"❌ Normalização falhou: {detail}")]),
                actions=EventActions(escalate=True),
            )
            return

        if not isinstance(variations, list) or not variations:
            detail = "Lista de variações vazia ou inválida."
            state["deterministic_final_validation"] = {
                "grade": "fail",
                "issues": [detail],
                "source": "normalizer",
            }
            state["deterministic_final_blocked"] = True
            state["deterministic_final_validation_failed"] = True
            state["deterministic_final_validation_failure_reason"] = detail
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="failed",
                detail=detail,
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=f"❌ Normalização falhou: {detail}")]),
                actions=EventActions(escalate=True),
            )
            return

        def _is_blank(value: Any) -> bool:
            if value is None:
                return True
            if isinstance(value, str) and not value.strip():
                return True
            return False

        normalized_variations: list[dict[str, Any]] = []
        structural_issues: list[str] = []

        for idx, variation in enumerate(variations):
            if not isinstance(variation, dict):
                structural_issues.append(f"Variação {idx + 1} não é um objeto JSON.")
                continue

            required_fields = [
                "landing_page_url",
                "formato",
                "cta_instagram",
                "fluxo",
                "referencia_padroes",
                "contexto_landing",
            ]
            missing = [field for field in required_fields if _is_blank(variation.get(field))]

            copy_block = variation.get("copy") or {}
            visual_block = variation.get("visual") or {}
            if not isinstance(copy_block, dict) or not isinstance(visual_block, dict):
                structural_issues.append(
                    f"Variação {idx + 1} possui 'copy' ou 'visual' inválidos."
                )
                continue

            copy_missing = [
                field for field in ("headline", "corpo", "cta_texto") if _is_blank(copy_block.get(field))
            ]
            visual_missing = [
                field
                for field in (
                    "descricao_imagem",
                    "prompt_estado_atual",
                    "prompt_estado_intermediario",
                    "prompt_estado_aspiracional",
                    "aspect_ratio",
                )
                if _is_blank(visual_block.get(field))
            ]

            if missing or copy_missing or visual_missing:
                details = []
                if missing:
                    details.append(
                        "campos principais: " + ", ".join(sorted(set(missing)))
                    )
                if copy_missing:
                    details.append("copy: " + ", ".join(copy_missing))
                if visual_missing:
                    details.append("visual: " + ", ".join(visual_missing))
                structural_issues.append(
                    f"Variação {idx + 1} incompleta ({'; '.join(details)})."
                )
                continue

            contexto = variation.get("contexto_landing")
            if isinstance(contexto, (dict, list)):
                variation["contexto_landing"] = json.dumps(contexto, ensure_ascii=False)

            normalized_variations.append(variation)

        if structural_issues:
            detail = "; ".join(structural_issues)
            state["deterministic_final_validation"] = {
                "grade": "fail",
                "issues": structural_issues,
                "source": "normalizer",
            }
            state["deterministic_final_blocked"] = True
            state["deterministic_final_validation_failed"] = True
            state["deterministic_final_validation_failure_reason"] = detail
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="failed",
                detail=detail,
                issues=structural_issues,
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=f"❌ Normalização falhou: {detail}")]),
                actions=EventActions(escalate=True),
            )
            return

        state["final_code_delivery_parsed"] = normalized_variations
        state["final_code_delivery"] = json.dumps(normalized_variations, ensure_ascii=False)
        state["deterministic_final_validation"] = {
            "grade": "pending",
            "issues": [],
            "source": "normalizer",
        }
        state["deterministic_final_blocked"] = False
        state.pop("deterministic_final_validation_failed", None)
        state.pop("deterministic_final_validation_failure_reason", None)
        append_delivery_audit_event(
            state,
            stage=self.name,
            status="pending",
            detail="Payload normalizado; aguardando validador determinístico.",
        )
        yield Event(
            author=self.name,
            content=Content(parts=[Part(text="🧮 JSON final normalizado para validação determinística.")]),
        )


class PersistFinalDeliveryAgent(BaseAgent):
    """Encapsula a persistência do JSON final normalizado."""

    def __init__(self, name: str = "persist_final_delivery_agent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        try:
            persist_final_delivery(ctx)
        except Exception as exc:  # pragma: no cover - persistência externa
            append_delivery_audit_event(
                state,
                stage=self.name,
                status="failed",
                detail=str(exc),
            )
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=f"❌ Falha ao persistir entrega final: {exc}")]),
            )
            return

        append_delivery_audit_event(
            state,
            stage=self.name,
            status="completed",
            detail="Persistência concluída.",
        )
        yield Event(
            author=self.name,
            content=Content(parts=[Part(text="💾 JSON final persistido com sucesso.")]),
        )


final_assembler_instruction = """
## IDENTIDADE: Final Ads Assembler

Monte **3 variações** de anúncio combinando `approved_code_snippets`.

Referências visuais aprovadas (aplicar somente quando disponíveis):
- Personagem: {reference_image_character_summary} (GCS: {reference_image_character_gcs_uri}, Labels: {reference_image_character_labels}, Descrição: {reference_image_character_user_description})
- Produto: {reference_image_product_summary} (GCS: {reference_image_product_gcs_uri}, Labels: {reference_image_product_labels}, Descrição: {reference_image_product_user_description})
- SafeSearch: {reference_image_safe_search_notes}

Campos obrigatórios (saída deve ser uma LISTA com 3 OBJETOS):
- "landing_page_url": usar {landing_page_url} (se vazio, inferir do briefing coerentemente)
- "formato": usar {formato_anuncio} especificado pelo usuário
- "copy": { "headline", "corpo", "cta_texto" } (COPY_DRAFT refinado - CRIAR 3 VARIAÇÕES)
- "visual": { "descricao_imagem", "prompt_estado_atual", "prompt_estado_intermediario", "prompt_estado_aspiracional", "aspect_ratio" } (sem duração - apenas imagens)
  - Quando houver referências aprovadas, inclua `"reference_assets"` com:
    ```json
    {
      "character": {"id": "...", "gcs_uri": "...", "labels": [...], "user_description": "..."},
      "product": {"id": "...", "gcs_uri": "...", "labels": [...], "user_description": "..."}
    }
    ```
    Remova entradas nulas para tipos não fornecidos e **nunca exponha `signed_url`**.
- "cta_instagram": do COPY_DRAFT
- "fluxo": coerente com {objetivo_final}, por padrão "Instagram Ad → Landing Page → Botão WhatsApp"
- "referencia_padroes": do RESEARCH
- "contexto_landing": OBRIGATÓRIO em TODAS as variações. Copie integralmente {landing_page_context} ou, se ausente, gere resumo com as chaves StoryBrand (storybrand_persona, storybrand_dores, storybrand_proposta, storybrand_beneficios, storybrand_transformacao, storybrand_cta_principal, storybrand_completeness)

Regras:
- Criar 3 variações diferentes de copy e visual reutilizando os snippets aprovados sempre que possível.
- Se qualquer variação chegar sem descrição completa ou sem os três prompts de visual, gere o conteúdo faltante usando o contexto StoryBrand (mesma persona, cenas 1-3) antes de finalizar.
- Não devolva prompts vazios; se não conseguir completar, pare e sinalize que o snippet VISUAL_DRAFT precisa ser refeito.
- Se um "foco" foi definido, garanta que as variações respeitam e comunicam o tema.
- Quando apenas o produto estiver aprovado, mantenha a narrativa centrada nele e evite criar personagens inexistentes.
- Quando apenas o personagem estiver aprovado, preserve aparência física e cite a persona real nas descrições e prompts.
- Quando ambos existirem, garanta interação coerente entre persona e produto em todas as variações.
- Mantenha exatamente três prompts sequenciais (`estado_atual`, `estado_intermediario`, `estado_aspiracional`) alinhados às instruções fixas de `code_generator`, `code_reviewer` e `code_refiner`.
- **Saída**: apenas JSON válido (sem markdown).
"""

final_assembler_llm = LlmAgent(
    model=config.critic_model,
    name="final_assembler_llm",
    description="Gera o JSON final a partir dos snippets aprovados.",
    instruction=final_assembler_instruction,
    output_key="final_code_delivery",
)

legacy_final_assembler_llm = LlmAgent(
    model=config.critic_model,
    name="final_assembler",  # manter nome legado
    description="Monta o JSON final do anúncio a partir dos fragmentos aprovados.",
    instruction=final_assembler_instruction,
    output_key="final_code_delivery",
    after_agent_callback=persist_final_delivery,
)

final_assembly_guard_pre = FinalAssemblyGuardPre()
final_assembly_normalizer = FinalAssemblyNormalizer()
persist_final_delivery_agent = PersistFinalDeliveryAgent()

deterministic_final_assembly_stage = SequentialAgent(
    name="final_assembly_stage",
    sub_agents=[
        final_assembly_guard_pre,
        final_assembler_llm,
        final_assembly_normalizer,
    ],
)


def _mirror_semantic_review(callback_context: CallbackContext) -> None:
    result = callback_context.state.get("semantic_visual_review")
    if isinstance(result, dict):
        callback_context.state["final_validation_result"] = result


semantic_visual_reviewer = LlmAgent(
    model=config.critic_model,
    name="semantic_visual_reviewer",
    description="Avalia narrativa, consistência visual e aderência ao briefing após validação determinística.",
    instruction=r"""
## IDENTIDADE: Semantic Visual Reviewer

Analise `final_code_delivery` (JSON já normalizado) verificando:
1. Consistência narrativa entre copy e visual de cada variação.
2. Aderência ao objetivo final `{objetivo_final}` e ao foco `{foco}` (se informado).
3. Fidelidade ao conteúdo real da landing page `{landing_page_context}` e ao StoryBrand.
4. Coerência dos prompts visuais com as descrições e com o formato `{formato_anuncio}`.
5. Ausência de promessas indevidas, termos proibidos ou discrepâncias gritantes.

Não repita validações estruturais já cobertas pelo validador determinístico (campos obrigatórios, enums, etc.).

Retorne `grade="pass"` quando todas as variações estiverem coerentes. Caso contrário, `grade="fail"` e detalhe problemas específicos em `comment`.
""",
    output_schema=Feedback,
    output_key="semantic_visual_review",
    after_agent_callback=_mirror_semantic_review,
)

semantic_fix_agent = LlmAgent(
    model=config.worker_model,
    name="semantic_fix_agent",
    description="Corrige incoerências narrativas apontadas pelo revisor semântico.",
    instruction="""
## IDENTIDADE: Semantic Fixer

Tarefas:
1) Leia `final_code_delivery` (JSON).
2) Leia `semantic_visual_review.comment` e corrija APENAS os pontos citados (consistência narrativa, tom, aderência ao foco/objetivo).
3) Preserve estrutura validada (chaves, enums) – não remova campos obrigatórios.
4) Garanta coerência com:
   - landing_page_url: {landing_page_url}
   - objetivo_final: {objetivo_final}
   - perfil_cliente: {perfil_cliente}
   - formato_anuncio: {formato_anuncio}
   - foco: {foco}
   - landing_page_context: {landing_page_context}
5) Retorne **apenas** o JSON final ajustado com 3 variações.
""",
    output_key="final_code_delivery",
)


# ────────────────────────────────────────────────────────────────────────────────
# INPUT PROCESSOR (Ads + legado)
# ────────────────────────────────────────────────────────────────────────────────

input_processor = LlmAgent(
    model=config.worker_model,
    name="input_processor",
    description="Extrai campos estruturados da entrada do usuário (Ads) com compatibilidade legada.",
    instruction="""
## IDENTIDADE: Input Processor

Extraia os campos:

### NOVO (Ads)
- landing_page_url
- objetivo_final (contato, leads, vendas, agendamentos, etc.)
- perfil_cliente (storybrand/persona)
- formato_anuncio (OBRIGATÓRIO: "Reels", "Stories" ou "Feed")
- foco (opcional): tema/gancho da campanha (ex.: "liquidação de inverno")

Formas aceitas:
- Linhas "chave: valor" (ex.: "landing_page_url: https://...")
- Tags: [landing_page_url]...[/landing_page_url], [objetivo_final]...[/objetivo_final], 
        [perfil_cliente]...[/perfil_cliente], [formato_anuncio]...[/formato_anuncio]
        [foco]...[/foco]

### LEGADO (se houver)
- [feature_snippet]...[/feature_snippet]
- [especificacao_tecnica_da_ui]...[/especificacao_tecnica_da_ui]
- [contexto_api]...[/contexto_api]
- [fonte_da_verdade_ux]...[/fonte_da_verdade_ux]

Regras:
- Preserve exatamente conteúdo entre tags.
- Se não houver tags, parseie linhas "chave: valor".
- extraction_status = "success" se ANY campo foi encontrado.

### SAÍDA (JSON)
{
  "landing_page_url": "string|null",
  "objetivo_final": "string|null",
  "perfil_cliente": "string|null",
  "formato_anuncio": "string|null",
  "foco": "string|null",
  "feature_snippet": "string|null",
  "especificacao_tecnica_da_ui": "string|null",
  "contexto_api": "string|null",
  "fonte_da_verdade_ux": "string|null",
  "extraction_status": "success" | "no_feature_found"
}
""",
    output_key="extracted_input",
    after_agent_callback=unpack_extracted_input_callback,
)


# ────────────────────────────────────────────────────────────────────────────────
# PIPELINES
# ────────────────────────────────────────────────────────────────────────────────

plan_review_loop = LoopAgent(
    name="plan_review_loop",
    max_iterations=config.max_plan_review_iterations if hasattr(config, "max_plan_review_iterations") else 5,
    sub_agents=[
        feature_planner,
        plan_reviewer,
        EscalationChecker(name="plan_escalation_checker", review_key="plan_review_result"),
    ],
    after_agent_callback=make_failure_handler(
        "plan_review_result",
        "Não foi possível atender aos critérios de revisão após as iterações."
    ),
)

final_delivery_validator_agent = FinalDeliveryValidatorAgent()
reset_deterministic_validation_state = ResetDeterministicValidationState()

planning_pipeline = SequentialAgent(
    name="planning_pipeline",
    description="Gera briefing e plano de tarefas (Ads).",
    sub_agents=[
        context_synthesizer,
        EscalationBarrier(name="plan_review_stage", agent=plan_review_loop),
    ],
)

planning_or_run_synth = PlanningOrRunSynth(
    synth_agent=context_synthesizer,
    planning_agent=planning_pipeline
)

landing_page_stage = LandingPageStage(landing_page_agent=landing_page_analyzer)

storybrand_quality_gate = StoryBrandQualityGate(
    planning_agent=planning_or_run_synth,
    fallback_agent=fallback_storybrand_pipeline
)

code_review_loop = LoopAgent(
    name="code_review_loop",
    max_iterations=config.max_code_review_iterations if hasattr(config, "max_code_review_iterations") else 5,
    sub_agents=[
        code_reviewer,
        EscalationChecker(name="code_escalation_checker", review_key="code_review_result"),
        RunIfFailed(name="refine_if_failed", review_key="code_review_result", agent=code_refiner),
    ],
    after_agent_callback=make_failure_handler(
        "code_review_result",
        "Não foi possível atender aos critérios de revisão de conteúdo após as iterações."
    ),
)

single_task_pipeline = SequentialAgent(
    name="single_task_pipeline",
    sub_agents=[
        TaskManager(name="task_manager"),
        code_generator,
        EscalationBarrier(name="code_review_stage", agent=code_review_loop),
        code_approver,
        TaskIncrementer(name="task_incrementer"),
    ],
)

task_execution_loop = LoopAgent(
    name="task_execution_loop",
    max_iterations=config.max_task_iterations if hasattr(config, "max_task_iterations") else 20,
    sub_agents=[
        single_task_pipeline,
        TaskCompletionChecker(name="task_completion_checker"),
    ],
    after_agent_callback=task_execution_failure_handler,
)

semantic_validation_loop = LoopAgent(
    name="semantic_validation_loop",
    max_iterations=3,
    sub_agents=[
        semantic_visual_reviewer,
        EscalationChecker(name="semantic_validation_escalator", review_key="semantic_visual_review"),
        RunIfFailed(
            name="semantic_fix_if_failed",
            review_key="semantic_visual_review",
            agent=semantic_fix_agent,
        ),
    ],
    after_agent_callback=make_failure_handler(
        "semantic_visual_review",
        "Não foi possível garantir coerência narrativa após as iterações.",
    ),
)

semantic_validation_stage = EscalationBarrier(
    name="semantic_validation_stage", agent=semantic_validation_loop
)

deterministic_validation_stage = SequentialAgent(
    name="deterministic_validation_stage",
    sub_agents=[final_delivery_validator_agent],
    after_agent_callback=make_failure_handler(
        "deterministic_final_validation",
        "JSON final não passou na validação determinística.",
    ),
)


def build_execution_pipeline(flag_enabled: bool) -> SequentialAgent:
    base_agents = [
        TaskInitializer(name="task_initializer"),
        EnhancedStatusReporter(name="status_reporter_start"),
        task_execution_loop,
        EnhancedStatusReporter(name="status_reporter_assembly"),
    ]

    if flag_enabled:
        deterministic_agents = [
            deterministic_final_assembly_stage,
            deterministic_validation_stage,
            RunIfPassed(
                name="semantic_validation_if_passed",
                review_key="deterministic_final_validation",
                agent=semantic_validation_stage,
            ),
            RunIfPassed(
                name="image_assets_if_passed",
                review_key="semantic_visual_review",
                agent=image_assets_agent,
            ),
            RunIfPassed(
                name="persist_final_delivery_if_passed",
                review_key="image_assets_review",
                agent=persist_final_delivery_agent,
                expected_grade=("pass", "skipped"),
            ),
            EnhancedStatusReporter(name="status_reporter_final"),
        ]
        sub_agents = base_agents + deterministic_agents
    else:
        legacy_agents = [
            reset_deterministic_validation_state,
            legacy_final_assembler_llm,
            semantic_validation_stage,
            image_assets_agent,
            EnhancedStatusReporter(name="status_reporter_final"),
        ]
        sub_agents = base_agents + legacy_agents

    return SequentialAgent(
        name="execution_pipeline",
        description="Executa plano, gera fragmentos e monta/valida JSON final.",
        sub_agents=sub_agents,
    )


execution_pipeline = build_execution_pipeline(
    flag_enabled=config.enable_deterministic_final_validation
)

complete_pipeline = SequentialAgent(
    name="complete_pipeline",
    description="Pipeline completo (Ads): input → análise LP → planejamento → execução → montagem → validação.",
    sub_agents=[
        input_processor,
        landing_page_stage,
        storybrand_quality_gate,
        execution_pipeline
    ],
)


# ────────────────────────────────────────────────────────────────────────────────
# ORQUESTRADOR RAIZ (mantido)
# ────────────────────────────────────────────────────────────────────────────────

class FeatureOrchestrator(BaseAgent):
    def __init__(self, complete_pipeline: BaseAgent):
        super().__init__(
            name="FeatureOrchestrator",
            description="Orchestrates the complete feature implementation flow."
        )
        self._complete_pipeline = complete_pipeline

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        if ctx.session.state.get("orchestrator_has_run"):
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text="Processamento já concluído para esta sessão.")])
            )
            return

        ctx.session.state["orchestrator_has_run"] = True
        yield Event(author=self.name, content=Content(parts=[Part(text="Iniciando processamento...")]))

        async for event in self._complete_pipeline.run_async(ctx):
            yield event

        if ctx.session.state.get("plan_review_result_failed"):
            yield Event(author=self.name, content=Content(parts=[Part(
                text=f"⚠️ Falha no Planejamento: {ctx.session.state.get('plan_review_result_failure_reason')}"
            )]))
        elif ctx.session.state.get("code_review_result_failed"):
            yield Event(author=self.name, content=Content(parts=[Part(
                text=f"⚠️ Falha na Revisão de Conteúdo: {ctx.session.state.get('code_review_result_failure_reason')}"
            )]))
        elif ctx.session.state.get("task_execution_failed"):
            yield Event(author=self.name, content=Content(parts=[Part(
                text=f"⚠️ Falha na Execução: {ctx.session.state.get('task_execution_failure_reason')}"
            )]))
        elif ctx.session.state.get("deterministic_final_validation_failed"):
            yield Event(author=self.name, content=Content(parts=[Part(
                text=f"⚠️ Falha na Validação Determinística: {ctx.session.state.get('deterministic_final_validation_failure_reason')}"
            )]))
        elif ctx.session.state.get("semantic_visual_review_failed"):
            yield Event(author=self.name, content=Content(parts=[Part(
                text=f"⚠️ Falha na Revisão Semântica: {ctx.session.state.get('semantic_visual_review_failure_reason')}"
            )]))
        elif ctx.session.state.get("image_assets_review_failed"):
            yield Event(author=self.name, content=Content(parts=[Part(
                text=f"⚠️ Falha na Geração de Imagens: {ctx.session.state.get('image_assets_review_failure_reason', 'Ver detalhes em image_assets_review')}"
            )]))
        elif ctx.session.state.get("final_validation_result_failed"):
            yield Event(author=self.name, content=Content(parts=[Part(
                text=f"⚠️ Falha na Validação Final: {ctx.session.state.get('final_validation_result_failure_reason')}"
            )]))
        elif "final_code_delivery" in ctx.session.state:
            yield Event(author=self.name, content=Content(parts=[Part(text="✅ Anúncio (JSON) gerado e validado!")]))

        ctx.session.state["orchestrator_has_run"] = False


root_agent = FeatureOrchestrator(complete_pipeline=complete_pipeline)
