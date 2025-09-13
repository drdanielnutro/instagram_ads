# app/agent.py
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

import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Literal

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import google_search
from google.genai.types import Content, Part
from pydantic import BaseModel, Field

from .config import config


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
    descricao: str
    aspect_ratio: Literal["9:16", "1:1", "4:5", "16:9"]
    duracao: str  # ex.: "15s", "30s"


class AdItem(BaseModel):
    landing_page_url: str
    formato: Literal["Reels", "Stories", "Feed"]
    copy: AdCopy
    visual: AdVisual
    cta_instagram: Literal["Saiba mais", "Enviar mensagem", "Ligar", "Comprar agora", "Cadastre-se"]
    fluxo: str
    referencia_padroes: str


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
            for k in ["landing_page_url", "objetivo_final", "perfil_cliente"]:
                callback_context.state.setdefault(k, "")
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
# PLANEJAMENTO (Ads) – mantém estilo "tarefas a executar"
# ────────────────────────────────────────────────────────────────────────────────

context_synthesizer = LlmAgent(
    model=config.worker_model,
    name="context_synthesizer",
    description="Sintetiza entrada para briefing de anúncio Instagram.",
    instruction="""
## IDENTIDADE: Context Synthesizer (Ads)

Sua missão (tarefas):
1) Consolidar as entradas:
   - landing_page_url: {landing_page_url}
   - objetivo_final: {objetivo_final}
   - perfil_cliente: {perfil_cliente}
2) Especificar persona, dores, benefícios, proposta de valor e prova social disponível.
3) Definir hipótese de formato (Reels/Feed/Stories) e ganchos possíveis.
4) Apontar restrições/políticas relevantes (Instagram e, se aplicável, saúde/medicina).
5) Produzir um briefing claro e acionável.

## SAÍDA (modelo)
ADS FEATURE BRIEFING
- Persona: [...]
- Dores/Benefícios: [...]
- Objetivo: [...]
- Formato recomendado: [...]
- Mensagens-chave: [...]
- Restrições: [...]
- Observações: [...]
""",
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
- Task atual: {current_task_info}

Regras gerais:
- **Saída sempre em JSON válido**, sem markdown/comentários.
- pt-BR e adequado a Instagram.
- Evite alegações médicas indevidas e promessas irrealistas.

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
      "descricao": "...",
      "aspect_ratio": "9:16" | "1:1" | "4:5" | "16:9",
      "duracao": "15s" | "30s"
    },
    "formato": "Reels" | "Stories" | "Feed"
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

Analise {generated_code} para a tarefa {current_task_info}. Aplique critérios **por categoria**:

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

- COPY_QA:
  * Avaliação honesta; se "ajustar", razões acionáveis

- VISUAL_DRAFT:
  * Descrição visual com gancho, contexto e elementos on-screen
  * Formato/ratio/duração coerentes

- VISUAL_QA:
  * Avaliação honesta; se "ajustar", razões acionáveis

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

Monte **1 item** de anúncio combinando `approved_code_snippets`.

Campos obrigatórios (saída deve ser uma LISTA com 1 OBJETO):
- "landing_page_url": usar {landing_page_url} (se vazio, inferir do briefing coerentemente)
- "formato": vir do melhor fragmento VISUAL_DRAFT aprovado (ou inferir coerente)
- "copy": { "headline", "corpo", "cta_texto" } (COPY_DRAFT refinado)
- "visual": { "descricao", "aspect_ratio", "duracao" } (VISUAL_DRAFT refinado)
- "cta_instagram": do COPY_DRAFT
- "fluxo": coerente com {objetivo_final}, por padrão "Instagram Ad → Landing Page → Botão WhatsApp"
- "referencia_padroes": do RESEARCH

Regras:
- Complete faltantes de forma conservadora.
- **Saída**: apenas JSON válido (sem markdown).
""",
    output_key="final_code_delivery",
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
1) JSON válido e lista com 1 objeto.
2) Chaves obrigatórias presentes:
   landing_page_url, formato, copy{headline,corpo,cta_texto}, visual{descricao,aspect_ratio,duracao}, cta_instagram, fluxo, referencia_padroes
3) Enums:
   - formato ∈ {"Reels","Stories","Feed"}
   - aspect_ratio ∈ {"9:16","1:1","4:5","16:9"}
   - cta_instagram ∈ {"Saiba mais","Enviar mensagem","Ligar","Comprar agora","Cadastre-se"}
4) "duracao" combina regex ^\d{1,3}s$
5) Coerência com objetivo_final: CTA e fluxo fazem sentido (ex.: leads → "Saiba mais" ou "Cadastre-se").
6) Campos não vazios/placeholder.

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
2) Leia `final_validation_result.comment` e **corrija** exatamente os pontos citados (enums, chaves faltantes, duração regex, etc.).
3) Garanta coerência com:
   - landing_page_url: {landing_page_url}
   - objetivo_final: {objetivo_final}
   - perfil_cliente: {perfil_cliente}
4) Retorne **apenas** o JSON final corrigido.
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

Formas aceitas:
- Linhas "chave: valor" (ex.: "landing_page_url: https://...")
- Tags: [landing_page_url]...[/landing_page_url], [objetivo_final]...[/objetivo_final], [perfil_cliente]...[/perfil_cliente]

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
    max_iterations=config.max_plan_review_iterations if hasattr(config, "max_plan_review_iterations") else 3,
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
    max_iterations=config.max_code_review_iterations if hasattr(config, "max_code_review_iterations") else 3,
    sub_agents=[
        code_reviewer,
        EscalationChecker(name="code_escalation_checker", review_key="code_review_result"),
        code_refiner,
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
        final_fix_agent,
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
        EnhancedStatusReporter(name="status_reporter_final"),
    ],
)

complete_pipeline = SequentialAgent(
    name="complete_pipeline",
    description="Pipeline completo (Ads): input → planejamento → execução → montagem → validação.",
    sub_agents=[
        input_processor,
        planning_pipeline,
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

