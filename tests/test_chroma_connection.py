# Copyright 2026 Aaron John Schlosser, PhD.
"""Chroma backend identity: embedded filesystem vs HTTP server.

Why: Vector Stores must be able to use PersistentClient, the compose Chroma
service, or a host-run Chroma process without two writers on one directory.
HTTP NUKE must delete collections on the server and must not wipe ./data/chroma.
How: exercises chroma_connection parsing without chromadb, then drives
ChromaStore against fake PersistentClient / HttpClient objects.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.chroma_connection import (
    connection_identity,
    http_client_kwargs,
    normalize_mode,
    parse_http_endpoint,
    public_http_config,
)
from app.models import ChromaConnectionUpdate
from pydantic import ValidationError


def test_normalize_mode_aliases():
    """Empty and filesystem aliases are embedded; server aliases are http."""
    assert normalize_mode("") == "embedded"
    assert normalize_mode("local") == "embedded"
    assert normalize_mode("HTTP") == "http"
    assert normalize_mode("server") == "http"
    with pytest.raises(ValueError):
        normalize_mode("s3")


def test_parse_http_endpoint_rejects_secrets_and_relative_urls():
    """Credentials belong in the token field; the URL must be an absolute origin."""
    parsed = parse_http_endpoint("https://chroma.example:8000/api/v2")
    assert parsed["display"] == "https://chroma.example:8000"
    assert parsed["ssl"] is True
    with pytest.raises(ValueError, match="absolute"):
        parse_http_endpoint("chroma:8000")
    with pytest.raises(ValueError, match="token"):
        parse_http_endpoint("http://user:secret@chroma:8000")
    kwargs = http_client_kwargs("http://host.docker.internal:8001")
    assert kwargs == {"host": "host.docker.internal", "port": 8001, "ssl": False}
    assert http_client_kwargs("https://chroma.example")["port"] == 443
    assert http_client_kwargs("http://chroma")["port"] == 8000


def test_connection_identity_never_includes_a_token():
    """Health chips and backups may show the origin, never a secret."""
    assert "secret" not in connection_identity(
        mode="http",
        url="http://chroma:8000",
        tenant="lab",
        database="derrida",
    )
    public = public_http_config({"url": "http://chroma:8000", "token": "secret-token"})
    assert public["token_configured"] is True
    assert "secret" not in str(public)


def test_connection_update_schema_accepts_embedded_and_http():
    """The API body names the mode; a path is optional until apply time."""
    embedded = ChromaConnectionUpdate(mode="embedded", path="/data/chroma")
    assert embedded.mode == "embedded"
    remote = ChromaConnectionUpdate(mode="http", url="http://chroma:8000")
    assert remote.url == "http://chroma:8000"
    with pytest.raises(ValidationError):
        ChromaConnectionUpdate(mode="s3")


class FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeClient:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.names = ["works"]
        self.deleted: list[str] = []
        self.heartbeats = 0

    def list_collections(self):
        return [FakeCollection(name) for name in list(self.names)]

    def delete_collection(self, name: str) -> None:
        self.deleted.append(name)
        self.names.remove(name)

    def heartbeat(self) -> int:
        self.heartbeats += 1
        return 1


def _store(tmp_path: Path, monkeypatch, *, mode: str = "embedded"):
    sys.modules.setdefault("chromadb", SimpleNamespace())
    from app import chroma_store as cs

    persistent_calls: list[dict] = []
    http_calls: list[dict] = []

    def persistent(**kwargs):
        persistent_calls.append(kwargs)
        return FakeClient(**kwargs)

    def http(**kwargs):
        http_calls.append(kwargs)
        return FakeClient(**kwargs)

    monkeypatch.setattr(cs, "chromadb", SimpleNamespace(
        PersistentClient=persistent,
        HttpClient=http,
        __version__="1.1.0",
    ))
    store = cs.ChromaStore.__new__(cs.ChromaStore)
    store._client = None
    store._data_root = tmp_path
    store._path = str(tmp_path / "chroma")
    store._mode = mode
    store._http = {
        "url": "http://chroma:8000",
        "token": "",
        "tenant": "default_tenant",
        "database": "default_database",
    }
    store.embeddings = None
    return store, persistent_calls, http_calls, cs


def test_embedded_health_reports_mode_and_identity(tmp_path: Path, monkeypatch):
    """Embedded health keeps path/host_path_hint and adds a mode identity."""
    store, _, _, _ = _store(tmp_path, monkeypatch, mode="embedded")
    (tmp_path / "chroma").mkdir()
    health = store.health()
    assert health["available"] is True
    assert health["mode"] == "embedded"
    assert health["path"] == str(tmp_path / "chroma")
    assert health["url"] is None
    assert "Local Chroma" in health["identity"]
    assert health["token_configured"] is False


def test_http_health_omits_filesystem_path(tmp_path: Path, monkeypatch):
    """HTTP health names the server origin and does not imply a live data path."""
    store, _, http_calls, _ = _store(tmp_path, monkeypatch, mode="http")
    store._http["token"] = "secret-token"
    health = store.health()
    assert health["available"] is True
    assert health["mode"] == "http"
    assert health["path"] is None
    assert health["url"] == "http://chroma:8000"
    assert health["token_configured"] is True
    assert "secret" not in str(health)
    assert http_calls and http_calls[0]["headers"]["Authorization"] == "Bearer secret-token"


def test_set_path_rejected_while_http(tmp_path: Path, monkeypatch):
    """Filesystem path changes are an embedded-only deployment action."""
    store, _, _, _ = _store(tmp_path, monkeypatch, mode="http")
    with pytest.raises(ValueError, match="embedded"):
        store.set_path(str(tmp_path / "other"))


def test_set_connection_switches_to_http_without_touching_disk(tmp_path: Path, monkeypatch):
    """Adopting a server does not migrate or delete the previous directory."""
    leftover = tmp_path / "chroma" / "chroma.sqlite3"
    leftover.parent.mkdir()
    leftover.write_text("keep", encoding="utf-8")
    store, _, http_calls, _ = _store(tmp_path, monkeypatch, mode="embedded")
    health = store.set_connection(mode="http", url="http://host.docker.internal:8001")
    assert health["mode"] == "http"
    assert health["url"] == "http://host.docker.internal:8001"
    assert leftover.exists()
    assert http_calls[0]["host"] == "host.docker.internal"
    assert http_calls[0]["port"] == 8001
    assert http_calls[0]["ssl"] is False


def test_probe_does_not_replace_the_live_client(tmp_path: Path, monkeypatch):
    """Test connection is a dry run so a bad URL cannot drop the current store."""
    store, _, _, _ = _store(tmp_path, monkeypatch, mode="embedded")
    original = FakeClient()
    store._client = original
    probed = store.probe_connection(mode="http", url="http://chroma:8000")
    assert probed["mode"] == "http"
    assert probed["available"] is True
    assert store.mode == "embedded"
    assert store._client is original


def test_http_nuke_deletes_collections_not_local_files(tmp_path: Path, monkeypatch):
    """NUKE against a server must not rmtree the embedded chroma directory."""
    root = tmp_path / "chroma"
    root.mkdir()
    catalog = root / "chroma.sqlite3"
    catalog.write_text("catalog", encoding="utf-8")
    store, _, _, _ = _store(tmp_path, monkeypatch, mode="http")
    client = FakeClient()
    client.names = ["works", "derridai_response_cache"]
    store._client = client
    store._path = str(root)

    result = store.nuke()

    assert result["deleted_collections"] == 2
    assert result["removed_paths"] == 0
    assert result["mode"] == "http"
    assert result["url"] == "http://chroma:8000"
    assert client.deleted == ["works", "derridai_response_cache"]
    assert catalog.exists()
    assert store._client is None


def test_http_nuke_fails_visibly_when_the_server_is_unreachable(tmp_path: Path, monkeypatch):
    """A failed HTTP reset must not report success or wipe leftover local files."""
    root = tmp_path / "chroma"
    root.mkdir()
    (root / "chroma.sqlite3").write_text("catalog", encoding="utf-8")
    store, _, _, _ = _store(tmp_path, monkeypatch, mode="http")

    class DeadClient:
        def list_collections(self):
            raise RuntimeError("connection refused")

    store._client = DeadClient()
    store._path = str(root)
    with pytest.raises(RuntimeError, match="connection refused"):
        store.nuke()
    assert (root / "chroma.sqlite3").exists()
