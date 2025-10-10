"""Shared test fixtures and stubs."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace

import pytest


class _DummyCounter:
    def add(self, *_args, **_kwargs) -> None:  # pragma: no cover - trivial stub
        return None


@pytest.fixture(autouse=True)
def stub_storybrand_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.utils import metrics

    monkeypatch.setattr(metrics, "_fallback_counter", _DummyCounter())


@pytest.fixture(autouse=True)
def stub_google_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    def _ensure_module(name: str) -> ModuleType:
        module = sys.modules.get(name)
        if module is None:
            module = ModuleType(name)
            sys.modules[name] = module
            if "." in name:
                parent_name, attr = name.rsplit(".", 1)
                parent = _ensure_module(parent_name)
                setattr(parent, attr, module)
        return module

    logging_module = sys.modules.get("google.cloud.logging")
    if logging_module is None:
        google_module = _ensure_module("google")
        cloud_module = _ensure_module("google.cloud")
        logging_module = ModuleType("google.cloud.logging")
        sys.modules["google.cloud.logging"] = logging_module
        setattr(google_module, "cloud", cloud_module)
        setattr(cloud_module, "logging", logging_module)

    if not hasattr(logging_module, "Client"):
        logging_module.Client = lambda *args, **kwargs: SimpleNamespace(logger=lambda *_a, **_k: None)

    storage_module = sys.modules.get("google.cloud.storage")
    if storage_module is None:
        google_module = _ensure_module("google")
        cloud_module = _ensure_module("google.cloud")
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

            def delete(self, *args, **kwargs) -> None:  # pragma: no cover
                return None

            def download_as_bytes(self) -> bytes:  # pragma: no cover
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

            def create_bucket(self, name: str, location: str | None = None, project: str | None = None) -> _DummyBucket:
                return _DummyBucket(name, location or "us-central1")

        storage_module.Client = _DummyStorageClient
        storage_module.Bucket = _DummyBucket
        storage_module.Blob = _DummyBlob

    # Minimal google.adk shims used across the codebase during tests
    adk_module = _ensure_module("google.adk")

    agents_module = _ensure_module("google.adk.agents")
    if not hasattr(agents_module, "BaseAgent"):

        class BaseAgent:
            """Simplified stand-in for google.adk BaseAgent."""

            def __init__(self, name: str | None = None) -> None:
                self.name = name or self.__class__.__name__

            async def run_async(self, ctx):  # pragma: no cover - simple shim
                impl = getattr(self, "_run_async_impl", None)
                if impl is None:
                    return
                result = impl(ctx)
                if hasattr(result, "__aiter__"):
                    async for event in result:
                        yield event
                elif hasattr(result, "__await__"):
                    awaited = await result
                    if awaited is not None:
                        yield awaited
                elif result is not None:
                    for event in result:
                        yield event

        class LlmAgent(BaseAgent):
            pass

        class LoopAgent(BaseAgent):
            pass

        class SequentialAgent(BaseAgent):
            pass

        agents_module.BaseAgent = BaseAgent
        agents_module.LlmAgent = LlmAgent
        agents_module.LoopAgent = LoopAgent
        agents_module.SequentialAgent = SequentialAgent

    events_module = _ensure_module("google.adk.events")
    if not hasattr(events_module, "Event"):

        @dataclass
        class Event:
            author: str | None = None
            content: object | None = None
            actions: object | None = None
            metadata: dict[str, object] | None = None

            def is_final_response(self) -> bool:
                actions = getattr(self, "actions", None)
                if actions is not None:
                    is_final = getattr(actions, "is_final", None)
                    if is_final is not None:
                        return bool(is_final)
                    if getattr(actions, "escalate", False):
                        return False
                return self.content is not None

        @dataclass
        class EventActions:
            escalate: bool = False
            state_delta: dict[str, object] | None = None
            artifact_delta: dict[str, object] | None = None
            transfer_to_agent: object | None = None
            metadata: dict[str, object] | None = None
            is_final: bool | None = None

        events_module.Event = Event
        events_module.EventActions = EventActions
        _ensure_module("google.adk.events.event").Event = Event
        sys.modules["google.adk.events.event"].EventActions = EventActions

    callback_module = _ensure_module("google.adk.agents.callback_context")
    if not hasattr(callback_module, "CallbackContext"):

        class CallbackContext:
            def __init__(self, *, state: dict | None = None, session: object | None = None) -> None:
                self.state = state or {}
                self.session = session
                actions_cls = getattr(events_module, "EventActions")
                self.actions = actions_cls()

        callback_module.CallbackContext = CallbackContext

    invocation_module = _ensure_module("google.adk.agents.invocation_context")
    if not hasattr(invocation_module, "InvocationContext"):

        class InvocationContext:
            def __init__(self, *, session: object | None = None, **kwargs) -> None:
                self.session = session or SimpleNamespace(state={})
                for key, value in kwargs.items():
                    setattr(self, key, value)

        invocation_module.InvocationContext = InvocationContext

    tools_module = _ensure_module("google.adk.tools")
    if not hasattr(tools_module, "google_search"):

        def google_search(*_args, **_kwargs) -> dict:
            return {"results": []}

        class FunctionTool:
            def __init__(self, func, name: str | None = None) -> None:
                self.func = func
                self.name = name or getattr(func, "__name__", "function_tool")

            async def arun(self, *args, **kwargs):  # pragma: no cover - shim
                result = self.func(*args, **kwargs)
                if hasattr(result, "__await__"):
                    return await result
                return result

            def __call__(self, *args, **kwargs):
                return self.func(*args, **kwargs)

        tools_module.google_search = google_search
        tools_module.FunctionTool = FunctionTool

    context_module = _ensure_module("google.adk.context")
    if not hasattr(context_module, "ToolContext"):

        class ToolContext:
            def __init__(self) -> None:
                self.state: dict = {}
                actions_cls = getattr(events_module, "EventActions")
                self.actions = actions_cls()

        context_module.ToolContext = ToolContext

    sessions_module = _ensure_module("google.adk.sessions")
    if not hasattr(sessions_module, "InMemorySessionService"):

        class Session(SimpleNamespace):
            state: dict

        class InMemorySessionService:
            def __init__(self) -> None:
                self._sessions: dict[tuple[str, str], Session] = {}

            async def create_session(self, *, app_name: str, user_id: str, session_id: str) -> Session:
                session = Session(app_name=app_name, user_id=user_id, session_id=session_id, state={})
                self._sessions[(user_id, session_id)] = session
                return session

            async def get_session(self, *, user_id: str, session_id: str) -> Session:
                return self._sessions.setdefault(
                    (user_id, session_id),
                    Session(user_id=user_id, session_id=session_id, state={}),
                )

        sessions_module.Session = Session
        sessions_module.InMemorySessionService = InMemorySessionService

    runners_module = _ensure_module("google.adk.runners")
    if not hasattr(runners_module, "Runner"):

        class Runner:
            def __init__(self, *, agent, app_name: str, session_service) -> None:
                self.agent = agent
                self.app_name = app_name
                self.session_service = session_service

            async def run_async(self, *, user_id: str, session_id: str, **kwargs):
                session = await self.session_service.get_session(user_id=user_id, session_id=session_id)
                context_cls = getattr(invocation_module, "InvocationContext")
                ctx = context_cls(session=session, **kwargs)
                async for event in self.agent.run_async(ctx):
                    yield event

        runners_module.Runner = Runner

    cli_module = _ensure_module("google.adk.cli")
    fast_api_module = _ensure_module("google.adk.cli.fast_api")
    if not hasattr(fast_api_module, "get_fast_api_app"):

        def get_fast_api_app(**_kwargs):  # pragma: no cover - shim
            class _FakeApp:
                def __init__(self) -> None:
                    self.title = ""
                    self.description = ""

                def include_router(self, *_args, **_kwargs) -> None:
                    return None

            return _FakeApp()

        fast_api_module.get_fast_api_app = get_fast_api_app

    yield
