"""Test configuration and lightweight stubs for Google ADK dependencies."""

from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterable


def _install_google_adk_stubs() -> None:
    if "google.adk.agents" in sys.modules:
        return

    google_module = sys.modules.get("google")
    if google_module is None:
        google_module = types.ModuleType("google")
        sys.modules["google"] = google_module

    adk_module = types.ModuleType("google.adk")
    sys.modules["google.adk"] = adk_module
    google_module.adk = adk_module  # type: ignore[attr-defined]

    auth_module = types.ModuleType("google.auth")
    auth_module.default = lambda: (None, "test-project")
    sys.modules["google.auth"] = auth_module
    google_module.auth = auth_module  # type: ignore[attr-defined]

    cloud_module = types.ModuleType("google.cloud")
    sys.modules["google.cloud"] = cloud_module
    google_module.cloud = cloud_module  # type: ignore[attr-defined]

    storage_module = types.ModuleType("google.cloud.storage")

    class _StorageClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.project = kwargs.get("project")

        def bucket(self, name: str):  # pragma: no cover - placeholders
            return SimpleNamespace(blob=lambda dest: SimpleNamespace(upload_from_string=lambda data, content_type=None: None))

    storage_module.Client = _StorageClient
    sys.modules["google.cloud.storage"] = storage_module

    events_module = types.ModuleType("google.adk.events")

    @dataclass
    class EventActions:
        escalate: bool = False

    @dataclass
    class Content:
        parts: list[Any] | None = None

    @dataclass
    class Part:
        text: str | None = None

        @classmethod
        def from_text(cls, text: str) -> "Part":
            return cls(text=text)

    class Event:
        def __init__(
            self,
            *,
            author: str,
            content: Content | None = None,
            actions: EventActions | None = None,
        ) -> None:
            self.author = author
            self.content = content or Content(parts=[])
            self.actions = actions

        def is_final_response(self) -> bool:
            return False

    events_module.Event = Event
    events_module.EventActions = EventActions
    sys.modules["google.adk.events"] = events_module
    adk_module.events = events_module  # type: ignore[attr-defined]

    agents_module = types.ModuleType("google.adk.agents")

    class BaseAgent:
        def __init__(self, *, name: str, description: str | None = None, **_: Any) -> None:
            self.name = name
            self.description = description

        async def run_async(self, ctx: Any):  # pragma: no cover - convenience
            async for event in self._run_async_impl(ctx):
                yield event

        async def _run_async_impl(self, ctx: Any):  # pragma: no cover - subclass responsibility
            if False:
                yield ctx

    class LlmAgent(BaseAgent):
        def __init__(
            self,
            *,
            model: str | None = None,
            name: str,
            description: str | None = None,
            instruction: str | None = None,
            tools: Iterable[Any] | None = None,
            output_key: str | None = None,
            after_agent_callback: Any | None = None,
            **kwargs: Any,
        ) -> None:
            super().__init__(name=name, description=description, **kwargs)
            self.model = model
            self.instruction = instruction
            self.tools = list(tools or [])
            self.output_key = output_key
            self.after_agent_callback = after_agent_callback

        async def _run_async_impl(self, ctx: Any):
            if self.output_key is not None:
                ctx.session.state.setdefault(self.output_key, None)
            if callable(self.after_agent_callback):
                callback_ctx = SimpleNamespace(state=ctx.session.state)
                maybe = self.after_agent_callback(callback_ctx)
                if asyncio.iscoroutine(maybe):
                    await maybe
            if False:
                yield None

    class SequentialAgent(BaseAgent):
        def __init__(
            self,
            *,
            name: str,
            sub_agents: Iterable[BaseAgent],
            description: str | None = None,
            after_agent_callback: Any | None = None,
            **kwargs: Any,
        ) -> None:
            super().__init__(name=name, description=description, **kwargs)
            self.sub_agents = list(sub_agents)
            self.after_agent_callback = after_agent_callback

        async def _run_async_impl(self, ctx: Any):
            for agent in self.sub_agents:
                async for event in agent.run_async(ctx):
                    yield event
            if callable(self.after_agent_callback):
                maybe = self.after_agent_callback(ctx)
                if asyncio.iscoroutine(maybe):
                    await maybe

    class LoopAgent(BaseAgent):
        def __init__(
            self,
            *,
            name: str,
            sub_agents: Iterable[BaseAgent],
            max_iterations: int = 1,
            after_agent_callback: Any | None = None,
            **kwargs: Any,
        ) -> None:
            super().__init__(name=name, **kwargs)
            self.sub_agents = list(sub_agents)
            self.max_iterations = max(1, max_iterations)
            self.after_agent_callback = after_agent_callback

        async def _run_async_impl(self, ctx: Any):
            for _ in range(self.max_iterations):
                for agent in self.sub_agents:
                    async for event in agent.run_async(ctx):
                        yield event
                if callable(self.after_agent_callback):
                    maybe = self.after_agent_callback(ctx)
                    if asyncio.iscoroutine(maybe):
                        await maybe

    agents_module.BaseAgent = BaseAgent
    agents_module.LlmAgent = LlmAgent
    agents_module.SequentialAgent = SequentialAgent
    agents_module.LoopAgent = LoopAgent
    sys.modules["google.adk.agents"] = agents_module
    adk_module.agents = agents_module  # type: ignore[attr-defined]

    callback_ctx_module = types.ModuleType("google.adk.agents.callback_context")

    class CallbackContext:
        def __init__(self, *, state: dict[str, Any] | None = None, session: Any | None = None) -> None:
            self.state = state or {}
            self.session = session or SimpleNamespace(state=self.state)

    callback_ctx_module.CallbackContext = CallbackContext
    sys.modules["google.adk.agents.callback_context"] = callback_ctx_module

    invocation_module = types.ModuleType("google.adk.agents.invocation_context")

    class InvocationContext:
        def __init__(self, *, session: Any) -> None:
            self.session = session

    invocation_module.InvocationContext = InvocationContext
    sys.modules["google.adk.agents.invocation_context"] = invocation_module

    tools_module = types.ModuleType("google.adk.tools")

    class FunctionTool:
        def __init__(self, *, name: str | None = None, description: str | None = None, func: Any) -> None:
            self.name = name or getattr(func, "__name__", "tool")
            self.description = description or ""
            self.func = func

        async def __call__(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - unused
            result = self.func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result

    async def google_search(*_: Any, **__: Any) -> dict[str, Any]:  # pragma: no cover - placeholder
        return {"results": []}

    tools_module.google_search = google_search
    tools_module.FunctionTool = FunctionTool
    sys.modules["google.adk.tools"] = tools_module

    runners_module = types.ModuleType("google.adk.runners")

    class Runner:
        def __init__(self, *, agent: BaseAgent, app_name: str, session_service: Any) -> None:
            self.agent = agent
            self.app_name = app_name
            self.session_service = session_service

        async def run_async(self, *args: Any, **kwargs: Any):  # pragma: no cover - manual scripts only
            if False:
                yield args, kwargs

    runners_module.Runner = Runner
    sys.modules["google.adk.runners"] = runners_module

    sessions_module = types.ModuleType("google.adk.sessions")

    class InMemorySessionService:
        async def create_session(self, *, app_name: str, user_id: str, session_id: str) -> None:  # noqa: D401
            self.app_name = app_name
            self.user_id = user_id
            self.session_id = session_id

    sessions_module.InMemorySessionService = InMemorySessionService
    sys.modules["google.adk.sessions"] = sessions_module

    invocation_pkg = types.ModuleType("google.adk.invocation_context")

    class _SessionMaker:
        async def __aenter__(self) -> Any:  # pragma: no cover - used in manual tests only
            return SimpleNamespace(state={})

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

    def session_maker(*_: Any, **__: Any) -> _SessionMaker:  # pragma: no cover - placeholder
        return _SessionMaker()

    invocation_pkg.session_maker = session_maker
    sys.modules["google.adk.invocation_context"] = invocation_pkg

    genai_module = sys.modules.get("google.genai")
    if genai_module is None:
        genai_module = types.ModuleType("google.genai")
        sys.modules["google.genai"] = genai_module

    class _GenAIModels:
        def generate_content(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - stub
            raise RuntimeError("generate_content called on stubbed client")

    class _GenAIClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.models = _GenAIModels()

    genai_module.Client = _GenAIClient  # type: ignore[attr-defined]

    genai_types_module = types.ModuleType("google.genai.types")
    genai_types_module.Content = Content
    genai_types_module.Part = Part
    sys.modules["google.genai.types"] = genai_types_module
    genai_module.types = genai_types_module  # type: ignore[attr-defined]

    otel_module = types.ModuleType("opentelemetry")
    metrics_module = types.ModuleType("opentelemetry.metrics")

    class _MeterProvider:
        def get_meter(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - stub
            return SimpleNamespace(create_counter=lambda *a, **k: None)

    def get_meter_provider() -> _MeterProvider:  # pragma: no cover - stub
        return _MeterProvider()

    metrics_module.get_meter_provider = get_meter_provider
    metrics_module.get_meter = lambda *_args, **_kwargs: _MeterProvider().get_meter()
    sys.modules["opentelemetry.metrics"] = metrics_module
    sys.modules["opentelemetry"] = otel_module


_install_google_adk_stubs()

