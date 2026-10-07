# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

"""Native Corpus Builder capability diagnostics."""

from __future__ import annotations

from app import corpus_capabilities
from app.corpus_run_config import HEADLESS_CORPUS_PIPELINE_FEATURES


def test_source_preflight_probes_only_relevant_optional_helpers(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(corpus_capabilities, "_module_available", lambda _name: True)

    def fake_tool(name: str, _args: tuple[str, ...]):
        calls.append(name)
        return {"available": True, "path": f"/{name}", "version": "test"}

    monkeypatch.setattr(corpus_capabilities, "_tool", fake_tool)

    pdf = corpus_capabilities.source_preflight("book.pdf", ocr_mode="auto")
    assert pdf["available"] is True
    assert calls == []

    audio = corpus_capabilities.source_preflight("lecture.wav")
    assert audio["available"] is True
    assert calls == ["ffprobe"]


def test_source_preflight_reports_missing_required_runtime_module(monkeypatch):
    monkeypatch.setattr(
        corpus_capabilities,
        "_module_available",
        lambda name: name != "httpx",
    )

    result = corpus_capabilities.source_preflight("book.txt")

    assert result["available"] is False
    assert result["missing"] == ["python:httpx"]


def test_runtime_capabilities_include_contract_bindings_and_filesystem(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        corpus_capabilities,
        "_tool",
        lambda _name, _args: {
            "available": False,
            "path": None,
            "version": None,
        },
    )
    monkeypatch.setattr(corpus_capabilities, "_module_available", lambda _name: False)

    result = corpus_capabilities.runtime_capabilities(
        workspace=tmp_path / "workspace",
        output_directory=tmp_path / "output",
    )

    assert result["status"] == "ok"
    assert result["filesystem"]["workspace"]["writable"] is True
    assert result["filesystem"]["output"]["writable"] is True
    assert result["missing_features"] == []
    assert set(result["headless_corpus_pipelines"]) == set(
        HEADLESS_CORPUS_PIPELINE_FEATURES
    )
    assert result["pipeline_contract"]["pipeline_contract_version"] >= 1
    assert result["provider_reachability"]["checked"] is False
