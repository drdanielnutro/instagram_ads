from __future__ import annotations

import sys
import types

import pytest


def _install_google_stubs() -> None:
    if "google" in sys.modules:
        return

    google_module = types.ModuleType("google")
    sys.modules["google"] = google_module

    adk_module = types.ModuleType("google.adk")
    sys.modules["google.adk"] = adk_module

    class _Dummy:  # pragma: no cover - minimal shim
        def __init__(self, *args, **kwargs) -> None:
            pass

    agents_module = types.ModuleType("google.adk.agents")
    agents_module.BaseAgent = _Dummy
    agents_module.LlmAgent = _Dummy
    agents_module.LoopAgent = _Dummy
    agents_module.SequentialAgent = _Dummy
    sys.modules["google.adk.agents"] = agents_module

    callback_module = types.ModuleType("google.adk.agents.callback_context")
    callback_module.CallbackContext = _Dummy
    sys.modules["google.adk.agents.callback_context"] = callback_module

    invocation_module = types.ModuleType("google.adk.agents.invocation_context")
    invocation_module.InvocationContext = _Dummy
    sys.modules["google.adk.agents.invocation_context"] = invocation_module

    events_module = types.ModuleType("google.adk.events")
    events_module.Event = _Dummy
    events_module.EventActions = _Dummy
    sys.modules["google.adk.events"] = events_module

    tools_module = types.ModuleType("google.adk.tools")
    tools_module.google_search = _Dummy()
    tools_module.FunctionTool = _Dummy
    sys.modules["google.adk.tools"] = tools_module

    genai_module = types.ModuleType("google.genai")
    sys.modules["google.genai"] = genai_module
    genai_types = types.ModuleType("google.genai.types")
    genai_types.Content = _Dummy
    genai_types.Part = _Dummy
    sys.modules["google.genai.types"] = genai_types

    auth_module = types.ModuleType("google.auth")
    auth_module.default = lambda: (None, "test-project")
    sys.modules["google.auth"] = auth_module
    google_module.auth = auth_module

    app_module = types.ModuleType("app")
    sys.modules["app"] = app_module
    utils_package = types.ModuleType("app.utils")
    sys.modules["app.utils"] = utils_package
    metrics_module = types.ModuleType("app.utils.metrics")
    metrics_module.record_vertex_429 = lambda *_args, **_kwargs: None
    sys.modules["app.utils.metrics"] = metrics_module
    utils_package.metrics = metrics_module
    app_module.utils = utils_package


_install_google_stubs()

import importlib.util
from pathlib import Path


def _load_vertex_retry_module():
    module_name = "app.utils.vertex_retry"
    spec = importlib.util.spec_from_file_location(
        module_name,
        Path(__file__).resolve().parents[3] / "app" / "utils" / "vertex_retry.py",
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Failed to load vertex_retry module spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


vertex_retry = _load_vertex_retry_module()


class _RetryableError(Exception):
    status_code = 429

    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__("vertex throttle")
        self.retry_after = retry_after


def test_call_with_vertex_retry_eventual_success(monkeypatch):
    attempts = {"count": 0}

    def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(vertex_retry.time, "sleep", fake_sleep)
    monkeypatch.setattr(vertex_retry.random, "uniform", lambda *_: 0.0)

    def flaky_call() -> str:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise _RetryableError()
        return "ok"

    result = vertex_retry.call_with_vertex_retry(
        flaky_call,
        max_attempts=3,
        initial_backoff=0.01,
        max_backoff=0.02,
        jitter=0.0,
    )

    assert result == "ok"
    assert attempts["count"] == 2


def test_call_with_vertex_retry_exhausted(monkeypatch):
    monkeypatch.setattr(vertex_retry.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(vertex_retry.random, "uniform", lambda *_: 0.0)

    def always_fail() -> None:
        raise _RetryableError(retry_after=0.01)

    with pytest.raises(vertex_retry.VertexRetryExceededError) as excinfo:
        vertex_retry.call_with_vertex_retry(
            always_fail,
            max_attempts=2,
            initial_backoff=0.01,
            max_backoff=0.02,
            jitter=0.0,
        )

    err = excinfo.value
    assert err.attempts == 2
    assert isinstance(err.last_exception, _RetryableError)
