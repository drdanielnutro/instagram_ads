
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
import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any, Dict, Literal

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import google_search, FunctionTool
from google.genai.types import Content, Part
from pydantic import BaseModel, Field

from .config import config
from .tools.web_fetch import web_fetch_tool
from .tools.generate_transformation_images import generate_transformation_images
from .utils.json_tools import try_parse_json_string


logger = logging.getLogger(__name__)
from .callbacks.landing_page_callbacks import process_and_extract_sb7, enrich_landing_context_with_storybrand
from .callbacks.persist_outputs import persist_final_delivery
from .schemas.storybrand import StoryBrandAnalysis


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
    code_snippets = callback_context.state.get("approved_code_snippets", [])
    if "generated_code" in callback_context.state:
        task_info = callback_context.state.get("current_task_info", {}) or {}
        code_snippets.append({
            "task_id": task_info.get("id", "unknown"),
            "category": task_info.get("category", "UNKNOWN"),
            "task_description": task_info.get("description", ""),
            "file_path": task_info.get("file_path", ""),
            "code": callback_context.state["generated_code"]
        })
    callback_context.state["approved_code_snippets"] = code_snippets


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


def make_failure_handler(state_key: str, reason: str):
    def _callback(callback_context: CallbackContext) -> None:
        result = callback_context.state.get(state_key)
        grade = result.get("grade") if isinstance(result, dict) else result
        if grade != "pass":
            callback_context.state[f"{state_key}_failed"] = True
            callback_context.state[f"{state_key}_failure_reason"] = reason
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
        if not tasks:
            text = "🔄 **FASE: PLANEJAMENTO** – preparando plano de tarefas (Ads)..."
        elif "final_code_delivery" in st:
            text = "✅ **PRONTO** – JSON final do anúncio disponível."
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
        yield Event(author=self.name, content=Content(parts=[Part(text=text)]))


class ImageAssetsAgent(BaseAgent):
    """Gera e anexa imagens consistentes ao JSON final."""

    def __init__(self, name: str = "image_assets_agent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        # Debug: verificar o que está no state
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"ImageAssetsAgent: Keys in state: {list(state.keys())}")
        logger.info(f"ImageAssetsAgent: final_code_delivery exists: {'final_code_delivery' in state}")

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
                    # Salvar de volta no state para próximos agentes
                    state["final_code_delivery"] = raw_delivery
            except Exception as e:
                logger.warning(f"ImageAssetsAgent: Failed to load from file: {e}")

        if not getattr(config, "enable_image_generation", True):
            yield Event(
                author=self.name,
                content=Content(parts=[Part(
                    text="ℹ️ Geração de imagens desativada pela configuração ENABLE_IMAGE_GENERATION."
                )]),
            )
            return

        if not raw_delivery:
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
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=f"❌ JSON final inválido para geração de imagens: {exc}")]),
            )
            return

        if not isinstance(variations, list) or not variations:
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

        summary: list[Dict[str, Any]] = []

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
                })
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

            metadata = {
                "user_id": user_id,
                "session_id": session_identifier,
                "formato": variation.get("formato"),
                "aspect_ratio": visual.get("aspect_ratio"),
            }

            task = asyncio.create_task(
                generate_transformation_images(
                    prompt_atual=visual["prompt_estado_atual"],
                    prompt_intermediario=visual["prompt_estado_intermediario"],
                    prompt_aspiracional=visual["prompt_estado_aspiracional"],
                    variation_idx=idx,
                    metadata=metadata,
                    progress_callback=progress_callback,
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
                            # Task is done, get the result before breaking
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
                # Debug: log what actually happened
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Image generation failed for variation {idx}: error={error}, assets={assets}")

                error_message = error or "Falha desconhecida na geração de imagens."
                visual["image_generation_error"] = error_message
                summary.append({
                    "variation_index": idx,
                    "status": "error",
                    "error": error_message,
                })
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
            if "meta" in assets:
                visual["image_generation_meta"] = assets["meta"]

            summary.append({
                "variation_index": idx,
                "status": "ok",
                "assets": assets,
            })

            yield Event(
                author=self.name,
                content=Content(parts=[Part(
                    text=f"🎉 Variação {variation_number}: imagens geradas e anexadas ao JSON."
                )]),
            )

        try:
            state["final_code_delivery"] = json.dumps(variations, ensure_ascii=False)
        except Exception as exc:  # pragma: no cover
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=f"❌ Erro ao serializar JSON final com imagens: {exc}")]),
            )
            return

        state["image_assets"] = summary

        try:
            persist_final_delivery(ctx)
        except Exception as exc:  # pragma: no cover - persistência externa
            logger.error("Falha ao persistir JSON atualizado com imagens: %s", exc, exc_info=True)
            yield Event(
                author=self.name,
                content=Content(parts=[Part(
                    text="⚠️ Imagens geradas, mas houve erro ao persistir a entrega final.""\n" + str(exc)
                )]),
            )
            return

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

- COPY_QA:
  {
    "validacao_copy": "ok|ajustar: <motivo>",
    "ajustes_copy_sugeridos": "..."
  }

- VISUAL_DRAFT:
  {
    "visual": {
      "descricao_imagem": "Descrição em pt-BR narrando a sequência: estado_atual (dor) → estado_intermediario (decisão imediata) → estado_aspiracional (transformação)...",
      "prompt_estado_atual": "Prompt técnico em inglês descrevendo o estado de dor (emoções, postura, cenário)...",
      "prompt_estado_intermediario": "Prompt técnico em inglês mantendo cenário/vestuário e mostrando a ação imediata de mudança...",
      "prompt_estado_aspiracional": "Prompt técnico em inglês descrevendo o estado transformado (emoções positivas, resultados visíveis, cenário)...",
      "aspect_ratio": "definido conforme especificação do formato"
    },
    "formato": "{formato_anuncio}"  # Usar o especificado pelo usuário
  }

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
  * Descrição visual com gancho, contexto e elementos on-screen
  * Narrativa deve mostrar a sequência: estado_atual (dor) → estado_intermediario (decisão imediata/mudança) → estado_aspiracional (transformação) mantendo coerência com a persona/contexto
  * Incluir prompts técnicos em inglês (`prompt_estado_atual`, `prompt_estado_intermediario`, `prompt_estado_aspiracional`) alinhados à narrativa e mostrando evolução honesta
  * Aspect ratio coerente com o formato (conforme {format_specs_json}); aparência nativa do posicionamento

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


final_assembler = LlmAgent(
    model=config.critic_model,
    name="final_assembler",  # mantido
    description="Monta o JSON final do anúncio a partir dos fragmentos aprovados.",
    instruction="""
## IDENTIDADE: Final Ads Assembler

Monte **3 variações** de anúncio combinando `approved_code_snippets`.

Campos obrigatórios (saída deve ser uma LISTA com 3 OBJETOS):
- "landing_page_url": usar {landing_page_url} (se vazio, inferir do briefing coerentemente)
- "formato": usar {formato_anuncio} especificado pelo usuário
- "copy": { "headline", "corpo", "cta_texto" } (COPY_DRAFT refinado - CRIAR 3 VARIAÇÕES)
- "visual": { "descricao_imagem", "prompt_estado_atual", "prompt_estado_intermediario", "prompt_estado_aspiracional", "aspect_ratio" } (sem duracao - apenas imagens)
- "cta_instagram": do COPY_DRAFT
- "fluxo": coerente com {objetivo_final}, por padrão "Instagram Ad → Landing Page → Botão WhatsApp"
- "referencia_padroes": do RESEARCH
- "contexto_landing": resumo do {landing_page_context}

Regras:
- Criar 3 variações diferentes de copy e visual
- Complete faltantes de forma conservadora.
- Se um "foco" foi definido, garanta que as variações respeitam e comunicam o tema.
- **Saída**: apenas JSON válido (sem markdown).
""",
    output_key="final_code_delivery",
    after_agent_callback=persist_final_delivery,
)

# Validador final (schema estrito + coerência)
final_validator = LlmAgent(
    model=config.critic_model,
    name="final_validator",
    description="Valida o JSON final contra o schema e regras de coerência.",
    instruction=r"""
## IDENTIDADE: Final Schema & Coherence Validator

Valide `final_code_delivery` (string JSON).
Critérios (deve ser **pass** se TODOS forem verdadeiros):
1) JSON válido e lista com 3 objetos (3 variações).
2) Chaves obrigatórias presentes:
   landing_page_url, formato, copy{headline,corpo,cta_texto}, 
   visual{descricao_imagem,prompt_estado_atual,prompt_estado_intermediario,prompt_estado_aspiracional,aspect_ratio}, cta_instagram, fluxo, referencia_padroes, contexto_landing
3) Enums:
   - formato ∈ {"Reels","Stories","Feed"}
   - aspect_ratio ∈ {"9:16","1:1","4:5","16:9"}
   - cta_instagram ∈ {"Saiba mais","Enviar mensagem","Ligar","Comprar agora","Cadastre-se"}
4) Coerência com objetivo_final: CTA e fluxo fazem sentido (ex.: leads → "Saiba mais" ou "Cadastre-se").
   Se houver "foco" definido, as mensagens devem refletir esse tema sem contradizer o conteúdo da landing page.
5) Campos não vazios/placeholder.
6) As 3 variações devem ser diferentes entre si.

7) Quando `format_specs_json` estiver presente:
   - O `aspect_ratio` e demais características do formato devem obedecer às especificações do formato selecionado.
   - A copy deve respeitar limites/estilo indicados (ex.: headline curta em Reels/Stories; informativa em Feed).

## SAÍDA
{"grade":"pass"|"fail","comment":"Se fail, liste campos/problemas específicos."}
""",
    output_schema=Feedback,
    output_key="final_validation_result",
)

# Fixador final (aplica correções apontadas pelo validador)
final_fix_agent = LlmAgent(
    model=config.worker_model,
    name="final_fix_agent",
    description="Corrige o JSON final com base no feedback do validador.",
    instruction="""
## IDENTIDADE: Final JSON Fixer

Tarefas:
1) Leia `final_code_delivery` (JSON).
2) Leia `final_validation_result.comment` e **corrija** exatamente os pontos citados (enums, chaves faltantes, etc.).
3) Garanta coerência com:
   - landing_page_url: {landing_page_url}
   - objetivo_final: {objetivo_final}
   - perfil_cliente: {perfil_cliente}
   - formato_anuncio: {formato_anuncio}
   - foco: {foco}
   - landing_page_context: {landing_page_context}
4) Retorne **apenas** o JSON final corrigido com 3 variações.
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

planning_pipeline = SequentialAgent(
    name="planning_pipeline",
    description="Gera briefing e plano de tarefas (Ads).",
    sub_agents=[
        context_synthesizer,
        EscalationBarrier(name="plan_review_stage", agent=plan_review_loop),
    ],
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

# Validação final em loop: valida → (pass?) → corrige → revalida
final_validation_loop = LoopAgent(
    name="final_validation_loop",
    max_iterations=3,
    sub_agents=[
        final_validator,
        EscalationChecker(name="final_validation_escalator", review_key="final_validation_result"),
        RunIfFailed(name="final_fix_if_failed", review_key="final_validation_result", agent=final_fix_agent),
    ],
    after_agent_callback=make_failure_handler(
        "final_validation_result",
        "JSON final não passou na validação de schema/coerência."
    ),
)

execution_pipeline = SequentialAgent(
    name="execution_pipeline",
    description="Executa plano, gera fragmentos e monta/valida JSON final.",
    sub_agents=[
        TaskInitializer(name="task_initializer"),
        EnhancedStatusReporter(name="status_reporter_start"),
        task_execution_loop,
        EnhancedStatusReporter(name="status_reporter_assembly"),
        final_assembler,
        EscalationBarrier(name="final_validation_stage", agent=final_validation_loop),
        image_assets_agent,
        EnhancedStatusReporter(name="status_reporter_final"),
    ],
)

complete_pipeline = SequentialAgent(
    name="complete_pipeline",
    description="Pipeline completo (Ads): input → análise LP → planejamento → execução → montagem → validação.",
    sub_agents=[
        input_processor,
        landing_page_analyzer,  # NOVO: adicionar aqui
        PlanningOrRunSynth(synth_agent=context_synthesizer, planning_agent=planning_pipeline),
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
        elif ctx.session.state.get("final_validation_result_failed"):
            yield Event(author=self.name, content=Content(parts=[Part(
                text=f"⚠️ Falha na Validação Final: {ctx.session.state.get('final_validation_result_failure_reason')}"
            )]))
        elif "final_code_delivery" in ctx.session.state:
            yield Event(author=self.name, content=Content(parts=[Part(text="✅ Anúncio (JSON) gerado e validado!")]))

        ctx.session.state["orchestrator_has_run"] = False


root_agent = FeatureOrchestrator(complete_pipeline=complete_pipeline)
