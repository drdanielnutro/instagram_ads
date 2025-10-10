"""Shared test fixtures and stubs."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import Any, Iterable

import pytest


class _DummyCounter:
    def add(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - trivial stub
        return None


def _ensure_module(name: str) -> ModuleType:
    """Create a ModuleType (and its parents) if it does not already exist."""

    module = sys.modules.get(name)
    if module is not None:
        return module

    module = ModuleType(name)
    sys.modules[name] = module

    if "." in name:
        parent_name, attr = name.rsplit(".", 1)
        parent = _ensure_module(parent_name)
        if not hasattr(parent, attr):
            setattr(parent, attr, module)

    return module


def _ensure_iterable(value: Any) -> Iterable[Any]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set)):
        return value
    return (value,)


async def _yield_from_result(result: Any) -> Iterable[Any]:
    if result is None:
        return
    if hasattr(result, "__aiter__"):
        async for item in result:
            yield item
        return
    if hasattr(result, "__await__"):
        awaited = await result
        for item in _ensure_iterable(awaited):
            yield item
        return
    for item in _ensure_iterable(result):
        yield item


def _install_google_cloud_stubs() -> None:
    logging_module = _ensure_module("google.cloud.logging")
    if not hasattr(logging_module, "Client"):
        logging_module.Client = lambda *args, **kwargs: SimpleNamespace(  # type: ignore[attr-defined]
            logger=lambda *_a, **_k: None
        )

    storage_module = _ensure_module("google.cloud.storage")
    if not hasattr(storage_module, "Client"):

        class _DummyBlob:
            def __init__(self, name: str) -> None:
                self.name = name

            def upload_from_string(self, *args: Any, **kwargs: Any) -> None:
                return None

            def generate_signed_url(self, *args: Any, **kwargs: Any) -> str:
                return "https://example.com/signed"

            def delete(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - cleanup shim
                return None

            def download_as_bytes(self) -> bytes:  # pragma: no cover - shim
                return b""

        class _DummyBucket:
            def __init__(self, name: str, location: str = "us-central1") -> None:
                self.name = name
                self.location = location

            def blob(self, name: str) -> _DummyBlob:
                return _DummyBlob(name)

        class _DummyStorageClient:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
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

        storage_module.Client = _DummyStorageClient  # type: ignore[attr-defined]
        storage_module.Bucket = _DummyBucket  # type: ignore[attr-defined]
        storage_module.Blob = _DummyBlob  # type: ignore[attr-defined]


def _install_google_adk_stubs() -> None:
    try:
        __import__("google.adk")  # If the real package exists, nothing to do.
        return
    except ImportError:
        pass

    adk_module = _ensure_module("google.adk")

    agents_module = _ensure_module("google.adk.agents")
    if not hasattr(agents_module, "BaseAgent"):

        class BaseAgent:
            """Simplified stand-in for google.adk BaseAgent."""

            def __init__(
                self,
                *args: Any,
                name: str | None = None,
                description: str | None = None,
                **kwargs: Any,
            ) -> None:
                del args
                self.name = name or self.__class__.__name__
                self.description = description
                self.config = kwargs
                for key, value in kwargs.items():
                    setattr(self, key, value)

            async def run_async(self, ctx: Any) -> Iterable[Any]:
                impl = getattr(self, "_run_async_impl", None)
                if impl is None:
                    return
                async for item in _yield_from_result(impl(ctx)):
                    yield item

        class LlmAgent(BaseAgent):
            def __init__(
                self,
                *args: Any,
                model: Any = None,
                instruction: str | None = None,
                output_key: str | None = None,
                after_agent_callback: Any = None,
                name: str | None = None,
                description: str | None = None,
                **kwargs: Any,
            ) -> None:
                super().__init__(
                    *args,
                    name=name,
                    description=description,
                    model=model,
                    instruction=instruction,
                    output_key=output_key,
                    after_agent_callback=after_agent_callback,
                    **kwargs,
                )

        class LoopAgent(BaseAgent):
            def __init__(
                self,
                agent: Any | None = None,
                max_iterations: int | None = None,
                name: str | None = None,
                description: str | None = None,
                **kwargs: Any,
            ) -> None:
                super().__init__(
                    name=name,
                    description=description,
                    agent=agent,
                    max_iterations=max_iterations,
                    **kwargs,
                )
                self.agent = agent
                self.max_iterations = max_iterations

        class SequentialAgent(BaseAgent):
            def __init__(
                self,
                sub_agents: Iterable[Any] | None = None,
                name: str | None = None,
                description: str | None = None,
                **kwargs: Any,
            ) -> None:
                super().__init__(
                    name=name,
                    description=description,
                    sub_agents=list(sub_agents or []),
                    **kwargs,
                )
                self.sub_agents = list(sub_agents or [])

            async def run_async(self, ctx: Any) -> Iterable[Any]:
                for agent in self.sub_agents:
                    run = getattr(agent, "run_async", None)
                    if run is None:
                        continue
                    async for event in run(ctx):
                        yield event

        agents_module.BaseAgent = BaseAgent  # type: ignore[attr-defined]
        agents_module.LlmAgent = LlmAgent  # type: ignore[attr-defined]
        agents_module.LoopAgent = LoopAgent  # type: ignore[attr-defined]
        agents_module.SequentialAgent = SequentialAgent  # type: ignore[attr-defined]

    events_module = _ensure_module("google.adk.events")
    if not hasattr(events_module, "Event"):

        @dataclass
        class Event:
            author: str | None = None
            content: Any | None = None
            actions: Any | None = None
            metadata: dict[str, Any] | None = None

            def is_final_response(self) -> bool:
                actions = self.actions
                if actions and getattr(actions, "escalate", False):
                    return False
                return self.content is not None

        @dataclass
        class EventActions:
            escalate: bool = False
            state_delta: dict[str, Any] | None = None
            artifact_delta: dict[str, Any] | None = None
            transfer_to_agent: Any | None = None
            metadata: dict[str, Any] | None = None
            is_final: bool | None = None

        events_module.Event = Event  # type: ignore[attr-defined]
        events_module.EventActions = EventActions  # type: ignore[attr-defined]
        events_event_module = _ensure_module("google.adk.events.event")
        if not hasattr(events_event_module, "Event"):
            events_event_module.Event = Event  # type: ignore[attr-defined]
        if not hasattr(events_event_module, "EventActions"):
            events_event_module.EventActions = EventActions  # type: ignore[attr-defined]

    callback_module = _ensure_module("google.adk.agents.callback_context")
    if not hasattr(callback_module, "CallbackContext"):

        class CallbackContext:
            def __init__(self, *, state: dict[str, Any] | None = None, session: Any | None = None) -> None:
                self.state = state or {}
                self.session = session
                actions_cls = getattr(events_module, "EventActions")
                self.actions = actions_cls()

        callback_module.CallbackContext = CallbackContext  # type: ignore[attr-defined]

    invocation_module = _ensure_module("google.adk.agents.invocation_context")
    if not hasattr(invocation_module, "InvocationContext"):

        class InvocationContext:
            def __init__(self, *, session: Any | None = None, **kwargs: Any) -> None:
                self.session = session or SimpleNamespace(state={})
                for key, value in kwargs.items():
                    setattr(self, key, value)

        invocation_module.InvocationContext = InvocationContext  # type: ignore[attr-defined]

    tools_module = _ensure_module("google.adk.tools")
    if not hasattr(tools_module, "google_search"):

        def google_search(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return {"results": []}

        class FunctionTool:
            def __init__(self, func: Any, name: str | None = None) -> None:
                self.func = func
                self.name = name or getattr(func, "__name__", "function_tool")

            async def arun(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - shim
                result = self.func(*args, **kwargs)
                if hasattr(result, "__await__"):
                    return await result
                return result

            def __call__(self, *args: Any, **kwargs: Any) -> Any:
                return self.func(*args, **kwargs)

        tools_module.google_search = google_search  # type: ignore[attr-defined]
        tools_module.FunctionTool = FunctionTool  # type: ignore[attr-defined]

    tool_context_module = _ensure_module("google.adk.tools.tool_context")
    if not hasattr(tool_context_module, "ToolContext"):

        class ToolContext:
            def __init__(self) -> None:
                self.state: dict[str, Any] = {}
                actions_cls = getattr(events_module, "EventActions")
                self.actions = actions_cls()

        tool_context_module.ToolContext = ToolContext  # type: ignore[attr-defined]

    sessions_module = _ensure_module("google.adk.sessions")
    if not hasattr(sessions_module, "InMemorySessionService"):

        class Session(SimpleNamespace):
            state: dict[str, Any]

        class InMemorySessionService:
            def __init__(self) -> None:
                self._sessions: dict[tuple[str, str], Session] = {}

            async def create_session(
                self,
                *,
                app_name: str,
                user_id: str,
                session_id: str,
            ) -> Session:
                session = Session(app_name=app_name, user_id=user_id, session_id=session_id, state={})
                self._sessions[(user_id, session_id)] = session
                return session

            async def get_session(self, *, user_id: str, session_id: str) -> Session:
                return self._sessions.setdefault(
                    (user_id, session_id),
                    Session(user_id=user_id, session_id=session_id, state={}),
                )

        sessions_module.Session = Session  # type: ignore[attr-defined]
        sessions_module.InMemorySessionService = InMemorySessionService  # type: ignore[attr-defined]

    runners_module = _ensure_module("google.adk.runners")
    if not hasattr(runners_module, "Runner"):

        class Runner:
            def __init__(self, *, agent: Any, app_name: str, session_service: Any) -> None:
                self.agent = agent
                self.app_name = app_name
                self.session_service = session_service

            async def run_async(self, *, user_id: str, session_id: str, **kwargs: Any) -> Iterable[Any]:
                session = await self.session_service.get_session(user_id=user_id, session_id=session_id)
                context_cls = getattr(invocation_module, "InvocationContext")
                ctx = context_cls(session=session, **kwargs)
                async for event in self.agent.run_async(ctx):
                    yield event

        runners_module.Runner = Runner  # type: ignore[attr-defined]

    cli_module = _ensure_module("google.adk.cli")
    fast_api_module = _ensure_module("google.adk.cli.fast_api")
    if not hasattr(fast_api_module, "get_fast_api_app"):

        def get_fast_api_app(**_kwargs: Any) -> Any:  # pragma: no cover - shim
            class _FakeApp:
                def __init__(self) -> None:
                    self.title = ""
                    self.description = ""

                def include_router(self, *_args: Any, **_kwargs: Any) -> None:
                    return None

            return _FakeApp()

        fast_api_module.get_fast_api_app = get_fast_api_app  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def stub_storybrand_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.utils import metrics

    monkeypatch.setattr(metrics, "_fallback_counter", _DummyCounter())


@pytest.fixture(autouse=True)
def stub_google_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_google_cloud_stubs()
    _install_google_adk_stubs()
    yield
