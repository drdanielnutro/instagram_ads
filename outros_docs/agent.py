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

import datetime
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
from google.adk.tools.agent_tool import AgentTool
from google.genai.types import Content, Part
from pydantic import BaseModel, Field

from .config import config


# --- Structured Output Models ---
class SearchQuery(BaseModel):
    """Model representing a specific search query for web search."""

    search_query: str = Field(
        description="A highly specific and targeted query for web search."
    )


class Feedback(BaseModel):
    """Model for providing evaluation feedback on research quality."""

    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if the research is sufficient, 'fail' if it needs revision."
    )
    comment: str = Field(
        description="Detailed explanation of the evaluation, highlighting strengths and/or weaknesses of the research."
    )
    follow_up_queries: list[SearchQuery] | None = Field(
        default=None,
        description="A list of specific, targeted follow-up search queries needed to fix research gaps. This should be null or empty if the grade is 'pass'.",
    )


class ImplementationTask(BaseModel):
    """Task within an implementation plan."""

    id: str = Field(description="Unique identifier for the task, e.g., 'TASK-001'.")
    category: Literal["MODEL", "PROVIDER", "WIDGET", "SERVICE", "UTIL"]
    title: str = Field(description="A short, descriptive title for the task.")
    description: str = Field(description="Detailed description of what to implement.")
    file_path: str = Field(description="The full path where the file should be created or modified.")
    action: Literal["CREATE", "MODIFY", "EXTEND"]
    dependencies: list[str] = Field(description="A list of task IDs that must be completed before this one.")


class ImplementationPlan(BaseModel):
    """Structured plan produced by the planner agent."""

    feature_name: str = Field(description="A descriptive name for the entire feature.")
    estimated_time: str = Field(description="A high-level time estimate, e.g., '2-3 hours'.")
    implementation_tasks: list[ImplementationTask]


# --- Callbacks ---
def collect_code_snippets_callback(callback_context: CallbackContext) -> None:
    """Collects approved code snippets throughout the execution pipeline."""
    session = callback_context._invocation_context.session
    code_snippets = callback_context.state.get("approved_code_snippets", [])
    
    # Collect any newly approved code snippet
    if "generated_code" in callback_context.state:
        code_snippet = callback_context.state["generated_code"]
        task_info = callback_context.state.get("current_task_info", {})
        
        code_snippets.append({
            "task_id": task_info.get("id", "unknown"),
            "task_description": task_info.get("description", ""),
            "file_path": task_info.get("file_path", ""),
            "code": code_snippet
        })
    
    callback_context.state["approved_code_snippets"] = code_snippets




def unpack_extracted_input_callback(callback_context: CallbackContext) -> None:
    """Unpacks the extracted_input dictionary into the session state."""
    if "extracted_input" in callback_context.state:
        extracted_input_str = callback_context.state["extracted_input"]
        try:
            if isinstance(extracted_input_str, str):
                if "```json" in extracted_input_str:
                    extracted_input_str = (
                        extracted_input_str.split("```json")[1]
                        .split("```")[0]
                        .strip()
                    )
                extracted_input = json.loads(extracted_input_str)
            elif isinstance(extracted_input_str, dict):
                extracted_input = extracted_input_str
            else:
                return

            if isinstance(extracted_input, dict):
                for key, value in extracted_input.items():
                    callback_context.state[key] = value
        except (json.JSONDecodeError, IndexError):
            pass


def make_failure_handler(state_key: str, reason: str):
    """Creates a callback that marks a failure if the review result isn't pass."""

    def _callback(callback_context: CallbackContext) -> None:
        result = callback_context.state.get(state_key)
        if isinstance(result, dict):
            grade = result.get("grade")
        else:
            grade = result
        if grade != "pass":
            callback_context.state[f"{state_key}_failed"] = True
            callback_context.state[f"{state_key}_failure_reason"] = reason

    return _callback


def task_execution_failure_handler(callback_context: CallbackContext) -> None:
    """Marks failure if task loop ends before completing all tasks."""
    tasks = callback_context.state.get("implementation_tasks", [])
    index = callback_context.state.get("current_task_index", 0)
    if index < len(tasks):
        callback_context.state["task_execution_failed"] = True
        callback_context.state[
            "task_execution_failure_reason"
        ] = "Limite de tentativas atingido antes de completar todas as tarefas."


# --- Custom Agent for Loop Control ---
class EscalationChecker(BaseAgent):
    """Checks evaluation and escalates to stop the loop if grade is 'pass'."""

    def __init__(self, name: str, review_key: str):
        super().__init__(name=name)
        self._review_key = review_key

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get(self._review_key)
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(
                f"[{self.name}] Review for '{self._review_key}' passed."
                " Escalating to stop loop."
            )
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Review for '{self._review_key}' failed. Loop"
                " will continue."
            )
            yield Event(author=self.name)


class TaskCompletionChecker(BaseAgent):
    """Checks if all tasks have been completed and escalates if done."""
    
    def __init__(self, name: str):
        super().__init__(name=name)
    
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        task_index = ctx.session.state.get("current_task_index", 0)
        tasks = ctx.session.state.get("implementation_tasks", [])
        
        if task_index >= len(tasks):
            logging.info(f"[{self.name}] All tasks completed. Escalating to finish.")
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(f"[{self.name}] More tasks remaining. Continuing...")
            yield Event(author=self.name)


class EnhancedStatusReporter(BaseAgent):
    """Repórter de status com estimativas de tempo e progresso visual."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        # Status detalhado com progresso visual
        status = self._generate_detailed_status(state)
        yield Event(
            author=self.name,
            content=Content(parts=[Part(text=status)])
        )

    def _generate_detailed_status(self, state: dict) -> str:
        tasks = state.get("implementation_tasks", [])
        task_index = state.get("current_task_index", 0)

        # Ainda na fase de planejamento
        if not tasks:
            return "🔄 **FASE: PLANEJAMENTO**\nAnalisando documentos e criando plano de implementação..."

        # Processo concluído
        if "final_code_delivery" in state:
            return "✅ **CONCLUÍDO**\nCódigo gerado e documentação pronta!"

        # Processo em andamento
        if task_index < len(tasks):
            # Progresso visual
            progress = task_index / len(tasks) if len(tasks) > 0 else 0
            progress_bar = "█" * int(progress * 10) + "░" * (10 - int(progress * 10))

            current_task = tasks[task_index]

            # Estimativa de tempo
            remaining_tasks = max(0, len(tasks) - task_index)
            estimated_minutes = remaining_tasks * 3  # ~3min por tarefa

            # Status da última revisão
            review_status = "Pendente"
            if "code_review_result" in state:
                review_result = state["code_review_result"]
                if isinstance(review_result, dict):
                    review_status = review_result.get("grade", "Pendente").upper()

            return f"""🔄 **EXECUTANDO: {task_index + 1}/{len(tasks)} tarefas**

**Progresso:** [{progress_bar}] {progress:.1%}

**Tarefa Atual:** {current_task.get('title', 'Processando...')}
📁 `{current_task.get('file_path', 'N/A')}`

**Tempo Estimado:** ~{estimated_minutes} minutos restantes

**Última Revisão:** {review_status}"""

        # Montando resultado final
        return "🔄 **FINALIZANDO**\nMontando documentação e código final..."


class TaskInitializer(BaseAgent):
    """Initializes the task index and total task count."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        tasks = ctx.session.state.get("implementation_tasks", [])
        ctx.session.state["current_task_index"] = 0
        ctx.session.state["total_tasks"] = len(tasks)
        yield Event(author=self.name)


class TaskManager(BaseAgent):
    """Selects the current task and puts it into the state."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        task_index = ctx.session.state.get("current_task_index", 0)
        tasks = ctx.session.state.get("implementation_tasks", [])

        if task_index < len(tasks):
            current_task = tasks[task_index]
            ctx.session.state["current_task_info"] = current_task
            ctx.session.state["current_task_description"] = current_task[
                "description"
            ]
            logging.info(
                "Processing task %d/%d: %s",
                task_index + 1,
                len(tasks),
                current_task["description"],
            )
            yield Event(
                author=self.name,
                content=Content(
                    parts=[
                        Part(
                            text=f"Starting task:"
                            f" {current_task['description']}"
                        )
                    ]
                ),
            )
        else:
            yield Event(author=self.name, actions=EventActions(escalate=True))


class TaskIncrementer(BaseAgent):
    """Increments the task index."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        task_index = ctx.session.state.get("current_task_index", 0)
        ctx.session.state["current_task_index"] = task_index + 1
        yield Event(author=self.name)


# --- PLANNING PIPELINE AGENTS ---

context_synthesizer = LlmAgent(
    model=config.worker_model,
    name="context_synthesizer",
    description="Synthesizes the 3 source documents into a focused briefing for the current feature.",
    instruction="""
    ## IDENTIDADE: Context Synthesizer
    
    Você é um especialista em análise de documentação técnica. Sua função é extrair e sintetizar as informações relevantes dos documentos de referência para a feature específica sendo implementada. Se um documento não for fornecido, ignore-o.

    ## ENTRADA
    **Feature a Implementar:**
    {feature_snippet}

    ## DOCUMENTOS DE REFERÊNCIA
    ### Especificação Técnica da UI
    {especificacao_tecnica_da_ui}

    ### Contexto da API
    {contexto_api}

    ### Fonte da Verdade UX
    {fonte_da_verdade_ux}

    ## SUA TAREFA
    Criar um "Feature Briefing" conciso e focado, extraindo:

    ### 1. Da Especificação Técnica (se disponível):
    - Padrões arquiteturais aplicáveis (Riverpod, json_dynamic_widget, etc.)
    - Estrutura de pastas e convenções
    - Dependências e bibliotecas relevantes

    ### 2. Do Contexto da API (se disponível):
    - Endpoints específicos necessários
    - Estruturas de request/response
    - Fluxo de autenticação se aplicável

    ### 3. Da Fonte da Verdade UX (se disponível):
    - Fluxo exato de interação do usuário
    - Elementos visuais necessários
    - Estados e transições

    ## FORMATO DE SAÍDA
    ```
    FEATURE BRIEFING: [Nome da Feature]
    
    ## Requisitos de UX
    - [Descrição do comportamento esperado]
    - [Interações do usuário]
    
    ## Arquitetura Técnica
    - Padrão: [Riverpod/MVVM/etc]
    - Widgets necessários: [lista]
    
    ## Integração com API
    - Endpoint: [método e path]
    - Request: [estrutura]
    - Response: [estrutura]
    
    ## Considerações Especiais
    - [Qualquer detalhe importante]
    ```
    """,
    output_key="feature_briefing",
)

feature_planner = LlmAgent(
    model=config.worker_model,
    name="feature_planner",
    description="Creates a detailed, actionable implementation plan with concrete coding tasks.",
    instruction="""
    ## IDENTIDADE: Flutter Tech Lead
    
    Você é um Tech Lead experiente em Flutter. Baseando-se no Feature Briefing fornecido, crie um plano de implementação detalhado e sequencial.

    ## ENTRADA
    **Feature Briefing:**
    {feature_briefing}

    ## SUA TAREFA
    Criar uma lista estruturada de TODAS as tarefas de código necessárias para implementar esta feature. 
    
    ## REGRAS PARA O PLANO
    1. Ordene as tarefas por dependência (models → providers → widgets → integration)
    2. Cada tarefa deve ser atômica e implementável em 15-30 minutos
    3. Especifique exatamente qual arquivo criar ou modificar
    4. Inclua descrição clara do que implementar

    ## FORMATO DE SAÍDA (JSON)
    ```json
    {
      "feature_name": "Nome descritivo da feature",
      "estimated_time": "2-3 horas",
      "implementation_tasks": [
        {
          "id": "TASK-001",
          "category": "MODEL",
          "title": "Criar modelo de estado",
          "description": "Implementar FeatureState com Freezed incluindo campos: isLoading, errorMessage, data",
          "file_path": "lib/features/feature_name/models/feature_state.dart",
          "action": "CREATE",
          "dependencies": []
        },
        {
          "id": "TASK-002",
          "category": "PROVIDER",
          "title": "Implementar StateNotifier",
          "description": "Criar FeatureNotifier extending StateNotifier<FeatureState> com métodos para gerenciar estado",
          "file_path": "lib/features/feature_name/providers/feature_provider.dart",
          "action": "CREATE",
          "dependencies": ["TASK-001"]
        }
      ]
    }
    ```

    **CATEGORIAS VÁLIDAS**: MODEL, PROVIDER, WIDGET, SERVICE, UTIL
    **AÇÕES VÁLIDAS**: CREATE, MODIFY, EXTEND
    """,
    output_schema=ImplementationPlan,
    output_key="implementation_plan",
)

plan_reviewer = LlmAgent(
    model=config.critic_model,
    name="plan_reviewer",
    description="Reviews the implementation plan for completeness and quality.",
    instruction="""
    ## IDENTIDADE: Principal Flutter Architect
    
    Você é um arquiteto principal revisando planos de implementação. Avalie o plano fornecido com rigor.

    ## ENTRADA
    **Implementation Plan:**
    {implementation_plan}

    **Feature Briefing:**
    {feature_briefing}

    ## CRITÉRIOS DE AVALIAÇÃO
    1. **Completude**: O plano cobre todos os aspectos do briefing?
    2. **Sequência Lógica**: As dependências estão corretas?
    3. **Granularidade**: As tarefas são pequenas o suficiente?
    4. **Clareza**: Cada tarefa está bem descrita?
    5. **Arquitetura**: Segue os padrões estabelecidos?

    ## REGRAS DE DECISÃO
    - **PASS**: Se o plano está completo e bem estruturado
    - **FAIL**: Se faltam tarefas essenciais ou há problemas de sequência

    ## FORMATO DE RESPOSTA
    Retorne um JSON no formato:
    ```json
    {
      "grade": "pass",
      "comment": "Plano completo e bem estruturado, cobrindo todos os aspectos da feature."
    }
    ```
    
    Ou se houver problemas:
    ```json
    {
      "grade": "fail",
      "comment": "Faltam tarefas para [aspecto específico]. Adicionar: [sugestões específicas]"
    }
    ```
    """,
    output_schema=Feedback,
    output_key="plan_review_result",
)

# --- EXECUTION PIPELINE AGENTS ---


code_generator = LlmAgent(
    model=config.worker_model,
    name="code_generator",
    description="Generates production-ready Flutter/Dart code for a single task.",
    instruction="""
    ## IDENTIDADE: Senior Flutter Developer
    
    Você é um desenvolvedor Flutter sênior gerando código production-ready para UMA tarefa específica.

    ## CONTEXTO
    **Feature Briefing:**
    {feature_briefing}

    **Tarefa Atual:**
    {current_task_info}

    ## PADRÕES OBRIGATÓRIOS

    ### Para Models (use Freezed):
    ```dart
    import 'package:freezed_annotation/freezed_annotation.dart';
    
    part 'model_name.freezed.dart';
    part 'model_name.g.dart';
    
    @freezed
    class ModelName with _$ModelName {
      const factory ModelName({
        required String field1,
        @Default(false) bool field2,
      }) = _ModelName;
      
      factory ModelName.fromJson(Map<String, dynamic> json) =>
          _$ModelNameFromJson(json);
    }
    ```

    ### Para Providers (Riverpod 2.0):
    ```dart
    import 'package:flutter_riverpod/flutter_riverpod.dart';
    
    final providerName = StateNotifierProvider<NotifierClass, StateClass>((ref) {
      return NotifierClass(ref);
    });
    ```

    ### Para Widgets:
    - Use ConsumerWidget ou ConsumerStatefulWidget
    - Implemente loading, error e success states
    - Use const constructors sempre que possível

    ## REGRAS
    1. Gere APENAS o código para a tarefa especificada
    2. Código deve estar completo e funcional
    3. Inclua todos os imports necessários
    4. Siga as convenções do projeto
    5. Adicione comentários onde necessário

    ## SAÍDA
    Retorne APENAS o código Dart, pronto para ser salvo no arquivo especificado.
    """,
    output_key="generated_code",
)

code_reviewer = LlmAgent(
    model=config.critic_model,
    name="code_reviewer",
    description="Reviews generated code for quality, correctness and adherence to requirements.",
    instruction="""
    ## IDENTIDADE: Principal Software Engineer
    
    Você é um engenheiro principal realizando code review rigoroso.

    ## CONTEXTO
    **Feature Briefing:**
    {feature_briefing}

    **Task Description:**
    {current_task_info}

    **Generated Code:**
    {generated_code}

    ## CRITÉRIOS DE REVISÃO

    ### 1. Correção Funcional (40%)
    - [ ] Implementa exatamente o que foi pedido?
    - [ ] Lógica está correta?
    - [ ] Tratamento de erros adequado?

    ### 2. Qualidade do Código (30%)
    - [ ] Segue convenções Dart/Flutter?
    - [ ] Código limpo e legível?
    - [ ] Sem duplicação?

    ### 3. Arquitetura (20%)
    - [ ] Respeita padrões do projeto?
    - [ ] Usa Riverpod corretamente?
    - [ ] Separação de responsabilidades?

    ### 4. Performance (10%)
    - [ ] Usa const onde possível?
    - [ ] Evita rebuilds desnecessários?
    - [ ] Gerencia recursos corretamente?

    ## FORMATO DE RESPOSTA
    
    Para código APROVADO:
    ```json
    {
      "grade": "pass",
      "comment": "Código implementa corretamente [descrição]. Segue todos os padrões e está pronto para produção."
    }
    ```

    Para código com PROBLEMAS:
    ```json
    {
      "grade": "fail",
      "comment": "Problemas identificados: [lista específica]. Correções necessárias: [lista de mudanças]",
      "follow_up_queries": [
        {"search_query": "Flutter [specific pattern] best practices"},
        {"search_query": "Riverpod [specific issue] solution"}
      ]
    }
    ```
    """,
    output_schema=Feedback,
    output_key="code_review_result",
)

code_refiner = LlmAgent(
    model=config.worker_model,
    name="code_refiner",
    description="Refines code based on review feedback.",
    instruction="""
    ## IDENTIDADE: Code Refinement Specialist
    
    Você é especialista em corrigir e melhorar código baseado em feedback de revisão.

    ## CONTEXTO
    **Review Feedback:**
    {code_review_result}

    **Original Code:**
    {generated_code}

    **Task Context:**
    {current_task_info}

    ## SUA TAREFA
    1. Analise o feedback da revisão
    2. Execute TODAS as queries de follow-up se houver
    3. Implemente TODAS as correções solicitadas
    4. Mantenha o que estava bom
    5. Melhore o que foi criticado

    ## PROCESSO
    Se há queries de follow-up:
    1. Execute cada uma com google_search
    2. Incorpore as best practices encontradas
    3. Aplique ao código

    ## SAÍDA
    Retorne o código CORRIGIDO e MELHORADO, pronto para nova revisão.
    """,
    tools=[google_search],
    output_key="generated_code",
)

code_approver = LlmAgent(
    model=config.worker_model,
    name="code_approver",
    description="Saves approved code to the state for final assembly.",
    instruction="""
    ## IDENTIDADE: Code Approval Manager
    
    O código para a tarefa atual foi aprovado na revisão. 

    ## SUA TAREFA
    1. Registre o código aprovado no estado
    2. Marque a tarefa como completa
    3. Prepare para a próxima tarefa

    ## DADOS
    **Task Info:** {current_task_info}
    **Approved Code:** {generated_code}

    ## SAÍDA
    Confirme que o código foi registrado e a tarefa marcada como completa.
    """,
    output_key="approval_confirmation",
    after_agent_callback=collect_code_snippets_callback,
)

final_assembler = LlmAgent(
    model=config.critic_model,
    name="final_assembler",
    description="Assembles all approved code snippets into the final deliverable with comprehensive documentation.",
    instruction="""
    ## IDENTIDADE: Final Code Assembler & Documentation Generator
    
    Você é responsável por criar uma entrega profissional completa, incluindo todo o código implementado E documentação contextual que agrega valor ao desenvolvedor.

    ## DADOS DISPONÍVEIS
    **Feature Name:** {{ implementation_plan.feature_name or "Unknown Feature" }}
    **Feature Briefing:** {feature_briefing}
    **Implementation Plan:** {implementation_plan}
    **Approved Code Snippets:** {approved_code_snippets}

    ## SUA MISSÃO
    Criar uma entrega completa que inclua:
    1. Todo o código implementado organizado por categoria
    2. Um README.md específico da feature explicando arquitetura e integração
    3. Instruções claras de como conectar a feature ao app principal

    ## FORMATO DE SAÍDA OBRIGATÓRIO

    Sua resposta DEVE conter DUAS seções principais:

    ### SEÇÃO 1: README da Feature
    ```markdown
    <!-- README.md -->
    # Feature: [Nome Descritivo]

    ## 📋 Visão Geral
    [Descrição concisa do que a feature faz e seu valor para o usuário]

    ## 🏗️ Arquitetura
    
    ### Componentes Principais
    - **Models**: [Descreva os modelos de dados e seu propósito]
    - **Providers**: [Explique o gerenciamento de estado]
    - **Widgets**: [Liste os widgets principais e suas responsabilidades]
    - **Services**: [Descreva integrações com API]

    ### Fluxo de Dados
    ```
    User Input → Widget → Provider → Service → API
                   ↑          ↓
                   └──────────┘
    ```

    ## 📁 Estrutura de Arquivos
    ```
    lib/features/[feature_name]/
    ├── models/
    │   └── feature_state.dart
    ├── providers/
    │   └── feature_provider.dart
    ├── widgets/
    │   └── feature_widget.dart
    └── services/
        └── feature_service.dart
    ```

    ## 🔧 Como Integrar

    ### 1. Adicionar ao Roteamento
    ```dart
    // Em lib/router/app_router.dart
    GoRoute(
      path: '/feature-name',
      builder: (context, state) => const FeatureWidget(),
    ),
    ```

    ### 2. Registrar Providers (se necessário)
    ```dart
    // Em lib/main.dart ou provider_scope
    ProviderScope(
      overrides: [
        // Adicione overrides se necessário
      ],
    )
    ```

    ### 3. Conectar à Navegação
    ```dart
    // Onde você quer acessar a feature
    context.go('/feature-name');
    ```

    ## 🧪 Testando a Feature
    
    ### Testes Unitários Sugeridos
    - [ ] Testar transformações do modelo
    - [ ] Testar lógica do StateNotifier
    - [ ] Testar chamadas de API mockadas

    ### Testes de Widget Sugeridos
    - [ ] Testar estados de loading
    - [ ] Testar tratamento de erros
    - [ ] Testar fluxo completo do usuário

    ## 🚀 Checklist de Deploy
    - [ ] Executar `flutter pub get`
    - [ ] Executar `flutter pub run build_runner build --delete-conflicting-outputs`
    - [ ] Verificar análise estática: `flutter analyze`
    - [ ] Executar testes: `flutter test`
    - [ ] Testar em dispositivo físico
    - [ ] Verificar performance com Flutter DevTools

    ## 📝 Notas Técnicas
    [Qualquer consideração especial, limitação conhecida ou decisão arquitetural importante]
    ```

    ### SEÇÃO 2: Código Implementado
    ```markdown
    # 💻 Código Implementado

    ## Resumo da Implementação
    - **Total de arquivos**: [número]
    - **Linhas de código**: ~[estimativa]
    - **Tempo estimado**: [horas]
    - **Complexidade**: [Baixa/Média/Alta]

    ## Arquivos Criados

    [Organize por categoria: Models → Providers → Widgets → Services]

    ### 📦 Models

    #### `lib/features/[feature]/models/[model].dart`
    ```dart
    [código completo]
    ```

    ### 🔄 Providers

    #### `lib/features/[feature]/providers/[provider].dart`
    ```dart
    [código completo]
    ```

    ### 🎨 Widgets

    #### `lib/features/[feature]/widgets/[widget].dart`
    ```dart
    [código completo]
    ```

    ### 🔌 Services

    #### `lib/features/[feature]/services/[service].dart`
    ```dart
    [código completo]
    ```
    ```

    ## REGRAS IMPORTANTES
    1. O README deve ser específico e contextual para ESTA feature
    2. Use diagramas simples em ASCII quando ajudar a explicar o fluxo
    3. Exemplos de código no README devem ser reais, não genéricos
    4. Mantenha um tom profissional mas acessível
    5. Foque em agregar valor prático ao desenvolvedor que vai integrar
    """,
    output_key="final_code_delivery",
)

# --- INPUT PROCESSING AGENT ---

input_processor = LlmAgent(
    model=config.worker_model,
    name="input_processor",
    description="Processes and extracts feature requests and documentation from user input",
    instruction="""
    ## IDENTIDADE: Input Processor
    
    Você é responsável por processar a entrada do usuário e extrair informações estruturadas
    para o sistema de geração de código Flutter.
    
    ## SUA TAREFA
    
    Analise a mensagem do usuário e extraia:
    
    1. **Feature Request** (OBRIGATÓRIO):
       - Procure por conteúdo entre tags [feature_snippet]...[/feature_snippet]
       - Se não houver tags, trate a mensagem inteira como feature request
       - Armazene em: feature_snippet
    
    2. **Documentação de Referência** (OPCIONAL):
       - [especificacao_tecnica_da_ui]...[/especificacao_tecnica_da_ui]: Especificações técnicas da UI
       - [contexto_api]...[/contexto_api]: Documentação da API
       - [fonte_da_verdade_ux]...[/fonte_da_verdade_ux]: Requisitos de UX
    
    ## REGRAS DE EXTRAÇÃO
    
    1. Se encontrar tags, extraia EXATAMENTE o conteúdo entre elas
    2. Preserve formatação, quebras de linha e código
    3. Se não encontrar [feature_snippet], mas encontrar outras tags, extraia-as mesmo assim
    4. Se não encontrar nenhuma tag, considere toda a mensagem como feature_snippet
    
    ## FORMATO DE SAÍDA
    
    Retorne um JSON com os campos extraídos:
    ```json
    {
      "feature_snippet": "descrição da feature extraída",
      "especificacao_tecnica_da_ui": "conteúdo extraído ou null",
      "contexto_api": "conteúdo extraído ou null",
      "fonte_da_verdade_ux": "conteúdo extraído ou null",
      "extraction_status": "success" ou "no_feature_found"
    }
    ```
    
    ## IMPORTANTE
    - Sempre defina feature_snippet se houver qualquer pedido de implementação
    - Defina extraction_status como "success" se encontrou uma feature
    - Defina extraction_status como "no_feature_found" apenas se não há nada para implementar
    """,
    output_key="extracted_input",
    after_agent_callback=unpack_extracted_input_callback,
)

# --- PIPELINE DEFINITIONS ---

planning_pipeline = SequentialAgent(
    name="planning_pipeline",
    description="Creates comprehensive implementation plan for a feature.",
    sub_agents=[
        context_synthesizer,
        LoopAgent(
            name="plan_review_loop",
            max_iterations=3,
            sub_agents=[
                feature_planner,  # Cria ou refaz o plano
                plan_reviewer,    # Revisa o plano
                EscalationChecker(
                    name="plan_escalation_checker",
                    review_key="plan_review_result",
                ),
            ],
            after_agent_callback=make_failure_handler(
                "plan_review_result",
                "Não foi possível atender aos critérios de revisão após 3 tentativas.",
            ),
        ),
    ],
)

# Task execution loop - processa uma tarefa por vez
task_execution_loop = LoopAgent(
    name="task_execution_loop",
    max_iterations=20,  # Máximo de 20 tarefas por feature
    sub_agents=[
        TaskManager(name="task_manager"),
        code_generator,  # Gera código
        LoopAgent(
            name="code_review_loop",
            max_iterations=3,
            sub_agents=[
                code_reviewer,
                EscalationChecker(
                    name="code_escalation_checker",
                    review_key="code_review_result",
                ),
                code_refiner,
            ],
            after_agent_callback=make_failure_handler(
                "code_review_result",
                "Não foi possível atender aos critérios de revisão de código após 3 tentativas.",
            ),
        ),
        code_approver,  # Salva código aprovado
        TaskIncrementer(name="task_incrementer"),
        TaskCompletionChecker(
            name="task_completion_checker"
        ),  # Verifica se há mais tarefas
    ],
    after_agent_callback=task_execution_failure_handler,
)

execution_pipeline = SequentialAgent(
    name="execution_pipeline",
    description="Executes approved implementation plan, generating code for each task.",
    sub_agents=[
        TaskInitializer(name="task_initializer"),
        EnhancedStatusReporter(name="status_reporter_start"),  # Status inicial
        task_execution_loop,
        EnhancedStatusReporter(
            name="status_reporter_assembly"
        ),  # Status pré-assembly
        final_assembler,
        EnhancedStatusReporter(name="status_reporter_final"),  # Status final
    ],
)

# --- COMPLETE PIPELINE WITH INPUT PROCESSING ---

complete_pipeline = SequentialAgent(
    name="complete_pipeline",
    description="Complete pipeline from input processing to code generation",
    sub_agents=[
        input_processor,        # Primeiro processa o input
        planning_pipeline,      # Depois planeja
        execution_pipeline      # Por fim executa
    ]
)

# --- MAIN ORCHESTRATOR ---

class FeatureOrchestrator(BaseAgent):
    def __init__(self, complete_pipeline: BaseAgent):
        super().__init__(
            name="FeatureOrchestrator",
            description="Orchestrates the complete Flutter feature implementation flow.",
        )
        self._complete_pipeline = complete_pipeline

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state

        if state.get("orchestrator_has_run"):
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text="Processamento concluído.")])
            )
            return

        state["orchestrator_has_run"] = True

        yield Event(
            author=self.name,
            content=Content(parts=[Part(text="Iniciando processamento da solicitação...")])
        )

        async for event in self._complete_pipeline.run_async(ctx):
            yield event

        if state.get("plan_review_result_failed"):
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=state.get("plan_review_result_failure_reason", "Falha no plano."))])
            )
        elif state.get("code_review_result_failed"):
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=state.get("code_review_result_failure_reason", "Falha na revisão de código."))])
            )
        elif state.get("task_execution_failed"):
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text=state.get("task_execution_failure_reason", "Falha na execução das tarefas."))])
            )
        elif "final_code_delivery" in state:
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text="✅ Feature implementada com sucesso!")])
            )
        elif "feature_snippet" not in state:
            yield Event(
                author=self.name,
                content=Content(parts=[Part(text="Por favor, forneça uma descrição clara da feature a ser implementada.")])
            )

        state["orchestrator_has_run"] = False

# A nova raiz do agente
root_agent = FeatureOrchestrator(
    complete_pipeline=complete_pipeline
)