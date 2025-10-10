"""Shared test fixtures and offline stubs."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace

import pytest


class _DummyCounter:
    def add(self, *_args, **_kwargs) -> None:  # pragma: no cover - trivial stub
        return None


def _ensure_module(name: str) -> ModuleType:
    module = sys.modules.get(name)
    if module is not None:
        return module
    module = ModuleType(name)
    sys.modules[name] = module
    if "." in name:
        parent_name, attr = name.rsplit(".", 1)
        parent = _ensure_module(parent_name)
        setattr(parent, attr, module)
    return module


def _install_google_cloud_stubs() -> None:
    auth_module = _ensure_module("google.auth")
    if not hasattr(auth_module, "default"):

        def default(**_kwargs):  # pragma: no cover - trivial stub
            return None, "test-project"

        auth_module.default = default

    logging_module = sys.modules.get("google.cloud.logging")
    if logging_module is None:
        google_module = sys.modules.setdefault("google", ModuleType("google"))
        cloud_module = sys.modules.setdefault("google.cloud", ModuleType("google.cloud"))
        logging_module = ModuleType("google.cloud.logging")
        sys.modules["google.cloud.logging"] = logging_module
        setattr(google_module, "cloud", cloud_module)
        setattr(cloud_module, "logging", logging_module)

    if not hasattr(logging_module, "Client"):
        logging_module.Client = lambda *args, **kwargs: SimpleNamespace(logger=lambda *_a, **_k: None)

    storage_module = sys.modules.get("google.cloud.storage")
    if storage_module is None:
        google_module = sys.modules.setdefault("google", ModuleType("google"))
        cloud_module = sys.modules.setdefault("google.cloud", ModuleType("google.cloud"))
        storage_module = ModuleType("google.cloud.storage")
        sys.modules["google.cloud.storage"] = storage_module
        setattr(google_module, "cloud", cloud_module)
        setattr(cloud_module, "storage", storage_module)

    if not hasattr(storage_module, "Client"):

        class _DummyBlob:
            def __init__(self, name: str) -> None:
                self.name = name

            def upload_from_string(self, *args, **kwargs) -> None:
                return None

            def generate_signed_url(self, *args, **kwargs) -> str:
                return "https://example.com/signed"

            def delete(self, *args, **kwargs) -> None:  # pragma: no cover - rarely used stub
                return None

            def download_as_bytes(self) -> bytes:  # pragma: no cover - rarely used stub
                return b""

        class _DummyBucket:
            def __init__(self, name: str, location: str = "us-central1") -> None:
                self.name = name
                self.location = location

            def blob(self, name: str) -> _DummyBlob:
                return _DummyBlob(name)

        class _DummyStorageClient:
            def __init__(self, *args, **kwargs) -> None:
                self.project = kwargs.get("project", "test-project")

            def bucket(self, name: str) -> _DummyBucket:
                return _DummyBucket(name)

            def get_bucket(self, name: str) -> _DummyBucket:
                return _DummyBucket(name)

            def create_bucket(
                self,
                name: str,
                location: str | None = None,
                project: str | None = None,
            ) -> _DummyBucket:
                return _DummyBucket(name, location or "us-central1")

        storage_module.Client = _DummyStorageClient
        storage_module.Bucket = _DummyBucket
        storage_module.Blob = _DummyBlob


def _install_google_adk_stubs() -> None:
    _ensure_module("google")
    adk_module = _ensure_module("google.adk")
    agents_module = _ensure_module("google.adk.agents")
    callback_module = _ensure_module("google.adk.agents.callback_context")
    invocation_module = _ensure_module("google.adk.agents.invocation_context")
    events_module = _ensure_module("google.adk.events")
    tools_module = _ensure_module("google.adk.tools")
    runners_module = _ensure_module("google.adk.runners")
    sessions_module = _ensure_module("google.adk.sessions")
    context_module = _ensure_module("google.adk.context")
    inv_root_module = _ensure_module("google.adk.invocation_context")

    if not hasattr(events_module, "EventActions"):

        @dataclass
        class EventActions:
            escalate: bool = False
            state_delta: dict | None = None
            output_key: str | None = None

            def mark_final(self) -> None:  # pragma: no cover - helper
                self.output_key = self.output_key or "final"

        class Event:
            def __init__(self, *, author: str, content=None, actions: EventActions | None = None):
                self.author = author
                self.content = content
                self.actions = actions or EventActions()

            def is_final_response(self) -> bool:  # pragma: no cover - simple flag
                return bool(getattr(self.actions, "output_key", None))

        events_module.Event = Event
        events_module.EventActions = EventActions

    if not hasattr(invocation_module, "InvocationContext"):

        class InvocationContext:
            def __init__(self, *, session: SimpleNamespace | None = None):
                if session is None:
                    session = SimpleNamespace(id="session", user_id="user", state={})
                session.state = getattr(session, "state", None) or {}
                self.session = session

        invocation_module.InvocationContext = InvocationContext
        inv_root_module.InvocationContext = InvocationContext

    if not hasattr(inv_root_module, "session_maker"):

        class _SessionManager:
            def __init__(self, *, state: dict | None = None):
                self._state = state or {}
                self._session = SimpleNamespace(
                    id="stub-session",
                    user_id="stub-user",
                    state=self._state,
                )

            async def __aenter__(self):
                return invocation_module.InvocationContext(session=self._session)

            async def __aexit__(self, exc_type, exc, tb):
                return False

        def session_maker(**_kwargs):
            return _SessionManager()

        inv_root_module.session_maker = session_maker

    if not hasattr(callback_module, "CallbackContext"):

        class CallbackContext:
            def __init__(self, invocation_context, agent=None):
                self._invocation_context = invocation_context
                self.agent = agent
                self.session = invocation_context.session
                self.state = self.session.state
                self.actions = events_module.EventActions()

        callback_module.CallbackContext = CallbackContext

    if not hasattr(context_module, "ToolContext"):

        class ToolContext:
            def __init__(self, *, state: dict | None = None):
                self.state = state or {}
                self.actions = events_module.EventActions()

        context_module.ToolContext = ToolContext

    if not hasattr(tools_module, "FunctionTool"):

        class FunctionTool:
            def __init__(self, *, func, name: str | None = None):
                self.func = func
                self.name = name or getattr(func, "__name__", "function_tool")

            def __call__(self, *args, **kwargs):
                return self.func(*args, **kwargs)

        async def google_search(*_args, **_kwargs):  # pragma: no cover - deterministic stub
            return {"status": "ok", "results": []}

        tools_module.FunctionTool = FunctionTool
        tools_module.google_search = google_search

    if not hasattr(agents_module, "BaseAgent"):

        class BaseAgent:
            def __init__(
                self,
                *,
                name: str,
                description: str | None = None,
                output_key: str | None = None,
                before_agent_callback=None,
                after_agent_callback=None,
                tools=None,
                **_kwargs,
            ) -> None:
                self.name = name
                self.description = description
                self.output_key = output_key
                self.before_agent_callback = before_agent_callback
                self.after_agent_callback = after_agent_callback
                self.tools = list(tools or [])

            async def _run_async_impl(self, ctx):  # pragma: no cover - default branch
                yield events_module.Event(author=self.name)

            async def run_async(self, ctx):
                if self.before_agent_callback:
                    self.before_agent_callback(callback_module.CallbackContext(ctx, agent=self))
                async for event in self._run_async_impl(ctx):
                    yield event
                if self.after_agent_callback:
                    self.after_agent_callback(callback_module.CallbackContext(ctx, agent=self))

            async def __call__(self, ctx):  # pragma: no cover - compatibility
                async for event in self.run_async(ctx):
                    yield event

            def run(self, *, ctx, **_kwargs):
                async def _collect():
                    events = []
                    async for event in self.run_async(ctx):
                        events.append(event)
                    return events

                return asyncio.run(_collect())

        def _filter_kwargs(kwargs: dict) -> dict:
            allowed = {"description", "output_key", "before_agent_callback", "after_agent_callback", "tools"}
            return {k: v for k, v in kwargs.items() if k in allowed}

        class SequentialAgent(BaseAgent):
            def __init__(self, *, name: str, sub_agents, **kwargs):
                super().__init__(name=name, **_filter_kwargs(kwargs))
                self.sub_agents = list(sub_agents)

            async def _run_async_impl(self, ctx):
                for agent in self.sub_agents:
                    async for event in agent.run_async(ctx):
                        yield event

        class LoopAgent(BaseAgent):
            def __init__(self, *, name: str, sub_agents, max_iterations: int = 1, **kwargs):
                super().__init__(name=name, **_filter_kwargs(kwargs))
                self.sub_agents = list(sub_agents)
                self.max_iterations = max(1, int(max_iterations))

            async def _run_async_impl(self, ctx):
                for _ in range(self.max_iterations):
                    for agent in self.sub_agents:
                        async for event in agent.run_async(ctx):
                            yield event
                    if self.after_agent_callback:
                        self.after_agent_callback(callback_module.CallbackContext(ctx, agent=self))

        class LlmAgent(BaseAgent):
            def __init__(self, *, name: str, model: str | None = None, **kwargs):
                super().__init__(name=name, **_filter_kwargs(kwargs))
                self.model = model or "stub-model"
                self.instruction = kwargs.get("instruction")
                self.output_schema = kwargs.get("output_schema")

        agents_module.BaseAgent = BaseAgent
        agents_module.SequentialAgent = SequentialAgent
        agents_module.LoopAgent = LoopAgent
        agents_module.LlmAgent = LlmAgent
        adk_module.BaseAgent = BaseAgent

    if not hasattr(runners_module, "Runner"):

        class Runner:
            def __init__(self, *, agent, app_name: str, session_service):
                self.agent = agent
                self.app_name = app_name
                self.session_service = session_service

            async def run_async(self, *, user_id: str, session_id: str, new_message=None):
                session = await self.session_service.get_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=session_id,
                )
                ctx = invocation_module.InvocationContext(session=session)
                async for event in self.agent.run_async(ctx):
                    yield event

        runners_module.Runner = Runner

    if not hasattr(sessions_module, "InMemorySessionService"):

        class InMemorySessionService:
            def __init__(self) -> None:
                self._sessions: dict[tuple[str, str, str], SimpleNamespace] = {}

            async def create_session(self, *, app_name: str, user_id: str, session_id: str):
                key = (app_name, user_id, session_id)
                session = SimpleNamespace(
                    id=session_id,
                    user_id=user_id,
                    app_name=app_name,
                    state={},
                )
                self._sessions[key] = session
                return session

            async def get_session(self, *, app_name: str, user_id: str, session_id: str):
                key = (app_name, user_id, session_id)
                if key not in self._sessions:
                    await self.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
                return self._sessions[key]

        sessions_module.InMemorySessionService = InMemorySessionService


def _install_google_genai_stubs() -> None:
    genai_module = _ensure_module("google.genai")
    types_module = _ensure_module("google.genai.types")

    if not hasattr(types_module, "Part"):

        @dataclass
        class Part:
            text: str | None = None
            inline_data: SimpleNamespace | None = None

            @classmethod
            def from_text(cls, text: str):
                return cls(text=text)

            @classmethod
            def from_bytes(cls, *, data: bytes, mime_type: str):
                return cls(inline_data=SimpleNamespace(data=data, mime_type=mime_type))

        @dataclass
        class Content:
            parts: list[Part]
            role: str | None = None

        @dataclass
        class GenerateContentConfig:
            response_modalities: list[str] | None = None
            temperature: float | None = None
            top_p: float | None = None
            max_output_tokens: int | None = None
            system_instruction: list[Part] | None = None

        types_module.Part = Part
        types_module.Content = Content
        types_module.GenerateContentConfig = GenerateContentConfig
        genai_module.types = types_module

    if not hasattr(genai_module, "Client"):

        class _ImageService:
            async def generate(self, *args, **kwargs):  # pragma: no cover - deterministic stub
                return SimpleNamespace(candidates=[])

        class Client:
            def __init__(self, *args, **kwargs):
                self._args = args
                self._kwargs = kwargs
                self.images = _ImageService()

        genai_module.Client = Client


def _install_opentelemetry_stubs() -> None:
    metrics_module = _ensure_module("opentelemetry.metrics")

    if not hasattr(metrics_module, "get_meter"):

        class _DummyMeter:
            def create_counter(self, *args, **kwargs):  # pragma: no cover - deterministic stub
                return _DummyCounter()

        def get_meter(*_args, **_kwargs):
            return _DummyMeter()

        metrics_module.get_meter = get_meter


_install_google_cloud_stubs()
_install_google_adk_stubs()
_install_google_genai_stubs()
_install_opentelemetry_stubs()


@pytest.fixture(autouse=True)
def stub_storybrand_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.utils import metrics

    monkeypatch.setattr(metrics, "_fallback_counter", _DummyCounter())


@pytest.fixture(autouse=True)
def stub_google_modules() -> None:
    # Fixtures execute before tests, ensuring stubs remain available when monkeypatched.
    _install_google_cloud_stubs()
    _install_google_adk_stubs()
    _install_google_genai_stubs()
    _install_opentelemetry_stubs()
