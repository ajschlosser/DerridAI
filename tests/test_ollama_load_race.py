"""A model load abandoned by a warmup must not take the build's first call down with it."""

from __future__ import annotations

from pathlib import Path
import sys
import types

import httpx
import pytest

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb
from app import llm


def manager(tmp_path: Path):
    m = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"))
    m._TRANSPORT_PAUSES = (0.0, 0.0, 0.0)
    return m


def test_a_dropped_connection_is_retried_until_the_server_is_ready(tmp_path):
    m = manager(tmp_path)
    calls = []

    def flaky(**kw):
        calls.append(kw)
        if len(calls) < 3:
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
        return "{}"

    assert m._with_transport_retry("", flaky, prompt="x") == "{}"
    assert len(calls) == 3


def test_errors_that_are_not_the_connection_are_not_retried(tmp_path):
    m = manager(tmp_path)
    calls = []

    def bad(**kw):
        calls.append(1)
        raise ValueError("schema mismatch")

    with pytest.raises(ValueError):
        m._with_transport_retry("", bad)
    assert len(calls) == 1
    timeouts = []

    def slow(**kw):
        timeouts.append(1)
        raise httpx.ReadTimeout("read timed out")

    with pytest.raises(httpx.ReadTimeout):
        m._with_transport_retry("", slow)
    assert len(timeouts) == 1


def test_it_gives_up_after_the_last_pause(tmp_path):
    m = manager(tmp_path)
    calls = []

    def down(**kw):
        calls.append(1)
        raise OSError("[Errno 97] Address family not supported by protocol")

    with pytest.raises(OSError):
        m._with_transport_retry("", down)
    assert len(calls) == 4  # the first try and one after each of three pauses


def test_warmup_loads_with_the_real_context_and_waits_for_a_slow_load(monkeypatch):
    seen = {}

    class FakeClient:
        def __init__(self, timeout=None, **kw):
            seen["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None, **kw):
            seen["body"] = json
            return types.SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(llm.httpx, "Client", FakeClient)
    result = llm.warmup_model(provider="ollama", model="big:14b", base_url="http://x:11434", num_ctx=16384)
    assert result["ok"] is True
    assert seen["body"]["options"]["num_ctx"] == 16384
    assert seen["timeout"].read > 60  # it used to give up at 60 s and abort the load


def test_regenerating_the_analysis_fills_only_what_is_empty(tmp_path, monkeypatch):
    m = manager(tmp_path)
    build = m.repo.create_build({"asset_id": "a", "source_sha256": "x", "source_filename": "x.pdf", "source_page_count": 1, "source_block_count": 1,
                                 "schema_version": cb.SCHEMA_VERSION, "profile_id": cb.PROFILE_VERSION, "profile_version": 11, "app_version": "0", "provider": "ollama", "model": "m", "request": {},
                                 "manifest": {"title": "Typed by hand", "document_author": None, "publisher": ""}})
    build.update(status="awaiting_review", stage="review", manifest_revision=1)
    m.repo.save_build(build)
    monkeypatch.setattr(m.repo, "get_asset", lambda asset_id: {"asset_id": asset_id})
    monkeypatch.setattr(m.repo, "load_blocks", lambda asset_id: [])
    monkeypatch.setattr(m, "_interactive_llm_request", lambda build_id, override=None: {"auto_enrich_work_metadata": False})
    monkeypatch.setattr(m, "_document_manifest", lambda *a, **k: {"title": "Model title", "document_author": "Jacques Derrida", "publisher": "Routledge"})
    saved = {}
    monkeypatch.setattr(m, "patch_manifest", lambda bid, changes, expected_revision=None: saved.update(changes) or m.repo.get_build(bid))
    out = m.regenerate_manifest(build["build_id"], {})
    assert saved == {"document_author": "Jacques Derrida", "publisher": "Routledge"}  # the typed title is left alone
    assert out["filled"] == ["document_author", "publisher"]
