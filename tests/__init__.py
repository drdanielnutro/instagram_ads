"""Test package initialisation providing stubs for external SDKs."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

# Ensure repository root is on sys.path for `import app`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ensure_module(name: str) -> ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = ModuleType(name)
        sys.modules[name] = module
    return module


def _patch_logging() -> None:
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


def _patch_storage() -> None:
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

            def delete(self, *args, **kwargs) -> None:  # pragma: no cover - cleanup noop
                return None

            def download_as_bytes(self) -> bytes:  # pragma: no cover - not used in tests
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


_patch_logging()
_patch_storage()
