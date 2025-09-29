from __future__ import annotations

import sys
import types


def _install_google_stubs() -> None:
    if "google" in sys.modules:
        return

    google_module = types.ModuleType("google")
    sys.modules["google"] = google_module
    adk_module = types.ModuleType("google.adk")
    sys.modules["google.adk"] = adk_module

    class _Dummy:
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


def _load_delivery_status_module():
    module_name = "app.utils.delivery_status"
    spec = importlib.util.spec_from_file_location(
        module_name,
        Path(__file__).resolve().parents[3] / "app" / "utils" / "delivery_status.py",
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Failed to load delivery_status module spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


delivery_status = _load_delivery_status_module()


def test_write_and_clear_failure_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(delivery_status, "_META_DIR", tmp_path)

    session_id = "test-session"
    user_id = "user-123"

    path = delivery_status.write_failure_meta(
        session_id=session_id,
        user_id=user_id,
        reason="vertex_resource_exhausted",
        message="Vertex AI saturated",
        extra={"attempts": 3},
    )

    assert path.exists()

    loaded = delivery_status.load_failure_meta(session_id)
    assert loaded is not None
    assert loaded["status"] == "failed"
    assert loaded["user_id"] == user_id
    assert loaded["reason"] == "vertex_resource_exhausted"
    assert loaded["attempts"] == 3

    delivery_status.clear_failure_meta(session_id)
    assert delivery_status.load_failure_meta(session_id) is None
    assert not path.exists()
