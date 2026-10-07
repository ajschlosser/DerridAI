# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD

from __future__ import annotations

import sys
import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor

from app import cross_encoder


def test_cross_encoder_uses_cache_folder_and_single_flight_loading(monkeypatch, tmp_path) -> None:
    calls = []
    predict_threads = []
    calls_lock = threading.Lock()

    class FakeCrossEncoder:
        def __init__(self, model_name, **kwargs):
            with calls_lock:
                calls.append((model_name, kwargs))
            time.sleep(0.05)

        def predict(self, pairs):
            with calls_lock:
                predict_threads.append(threading.get_ident())
            return [0.5 for _ in pairs]

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.__version__ = "5.test"
    fake_module.CrossEncoder = FakeCrossEncoder
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setattr(
        cross_encoder,
        "settings",
        types.SimpleNamespace(rag_model_cache=str(tmp_path)),
    )
    cross_encoder._MODEL_CACHE.clear()

    def run_once():
        return cross_encoder.predict_scores(
            [("query", "passage")],
            model_name="cross-encoder/test",
            timeout_seconds=2,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _index: run_once(), range(8)))

    assert all(scores == [0.5] for scores, _telemetry in results)
    assert len(calls) == 1
    # Concurrent callers share the one process-wide native inference thread
    # instead of creating a fresh allocator arena for each rerank.
    assert len(set(predict_threads)) == 1
    _model_name, kwargs = calls[0]
    assert kwargs["cache_folder"] == str(tmp_path)
    assert "cache_dir" not in kwargs



def test_cached_only_context_ranking_never_loads_or_downloads_a_model(monkeypatch):
    from app import cross_encoder
    monkeypatch.setattr(cross_encoder, "_MODEL_CACHE", {})
    def forbidden(*_):
        raise AssertionError("No model load/download allowed")
    monkeypatch.setattr(cross_encoder, "_load_model", forbidden)
    scores, telemetry = cross_encoder.predict_scores([("question", "older turn")],
        model_name="local/test", cached_only=True, timeout_seconds=2)
    assert scores is None and telemetry["fallback_reason"] == "model_not_loaded"
