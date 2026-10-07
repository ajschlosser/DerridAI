# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NATIVE_RUNTIME_DEFAULTS = {
    "MALLOC_ARENA_MAX": "4",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "RAYON_NUM_THREADS": "2",
    "TOKENIZERS_PARALLELISM": "false",
}


def test_api_image_bounds_native_runtime_parallelism_and_malloc_arenas() -> None:
    dockerfile = (ROOT / "api" / "Dockerfile").read_text(encoding="utf-8")
    for key, value in NATIVE_RUNTIME_DEFAULTS.items():
        assert f"{key}={value}" in dockerfile


def test_compose_exposes_native_runtime_limits_as_overridable_defaults() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for key, value in NATIVE_RUNTIME_DEFAULTS.items():
        assert f"{key}: ${{{key}:-{value}}}" in compose


def test_env_example_documents_native_runtime_limits() -> None:
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key, value in NATIVE_RUNTIME_DEFAULTS.items():
        assert f"{key}={value}" in env_example


def test_hot_native_paths_reuse_bounded_process_wide_executors() -> None:
    from app import cross_encoder
    from app import metadata_exemplar_retrieval

    assert cross_encoder._INFERENCE_EXECUTOR._max_workers == 1
    assert metadata_exemplar_retrieval._EXEMPLAR_QUERY_EXECUTOR._max_workers == 4


def test_corpus_builder_does_not_keep_duplicate_semantic_graphs_in_process_memory() -> None:
    source = (ROOT / "api" / "app" / "corpus_builder.py").read_text(encoding="utf-8")
    assert "_semantic_graph_cache" not in source
