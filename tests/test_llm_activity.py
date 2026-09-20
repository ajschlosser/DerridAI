"""The live "what is the build waiting for" reading."""

from __future__ import annotations

import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

from app import corpus_builder as cb


def manager(tmp_path: Path):
    return cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"))


def test_no_call_in_flight_means_no_activity(tmp_path):
    assert manager(tmp_path).llm_activity("b") is None


def test_an_ollama_model_that_is_not_in_memory_is_reported_as_loading(tmp_path, monkeypatch):
    m = manager(tmp_path)
    monkeypatch.setattr(m, "_ollama_loaded_models", lambda url: set())
    token = m._note_llm_call_start("b", "manifest", "ollama", "big:14b", "http://x:11434")
    seen = m.llm_activity("b")
    assert seen["state"] == "loading_model" and seen["task"] == "manifest" and seen["model"] == "big:14b" and seen["seconds"] >= 0
    monkeypatch.setattr(m, "_ollama_loaded_models", lambda url: {"big:14b"})
    assert m.llm_activity("b")["state"] == "working"
    monkeypatch.setattr(m, "_ollama_loaded_models", lambda url: None)  # Ollama could not be asked
    assert m.llm_activity("b")["state"] == "unknown"
    m._note_llm_call_end("b", token)
    assert m.llm_activity("b") is None


def test_other_providers_are_simply_working_and_the_oldest_call_leads(tmp_path):
    m = manager(tmp_path)
    first = m._note_llm_call_start("b", "segmentation", "openai", "auto", "http://x/v1")
    second = m._note_llm_call_start("b", "metadata", "openai", "auto", "http://x/v1")
    seen = m.llm_activity("b")
    assert seen["state"] == "working" and seen["task"] == "segmentation" and seen["calls_in_flight"] == 2
    m._note_llm_call_end("b", first)
    assert m.llm_activity("b")["task"] == "metadata"
    m._note_llm_call_end("b", second)


def test_asking_ollama_fails_quietly(tmp_path):
    assert manager(tmp_path)._ollama_loaded_models("http://127.0.0.1:9") is None
