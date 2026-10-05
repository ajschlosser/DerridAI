# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Corpus Builder runtime resilience: bad LLM output, segmentation guards, resume.

Why: local LLMs return malformed, truncated, or non-JSON answers. A book-length build must
degrade safely: never invent a record, never collapse a book into one giant record, never
lose text, and always leave a state a human can review or resume.
How: replaces `chat_complete` so the "LLM" returns broken or empty replies on demand, then runs
the manager's segmentation/enrichment/run steps on synthetic blocks in a temp repository.
Note: at import this file installs a stub `app.rag` module (via setdefault) so these tests do not
need vector-store dependencies; `_blocks` and `_build` are shared helpers below.
"""

from __future__ import annotations

import json
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.persistence_errors import PersistenceBusyError

# Isolate Corpus Builder tests from optional vector-store dependencies.  The
# production module imports these helpers from app.rag, while this test only
# exercises structured-output and source-record behavior.
rag_stub = types.ModuleType("app.rag")
rag_stub._extract_json = lambda value: json.loads(value)
rag_stub._citation_strings = lambda record: (
    f"({record.get('document_author') or 'Unknown'}, {record.get('year') or 'n.d.'}: {record.get('page_start') or '?'})",
    f"{record.get('document_author') or 'Unknown'}. {record.get('work') or 'Untitled'}."
)
rag_stub.chat_complete = lambda **kwargs: "{}"
rag_stub.run_rag_pipeline = lambda *args, **kwargs: {}
sys.modules.setdefault("app.rag", rag_stub)
from app import corpus_builder as cb
from app import corpus_segmentation_execution as cse
from app import operation_events


def _blocks(count: int = 30):
    """Build `count` synthetic paragraph blocks (ten per page) with printed page labels."""
    return [
        {
            "block_id": f"p001-b{i:03d}",
            "page": 1 + (i // 10),
            "printed_page_label": str(1 + (i // 10)),
            "type": "paragraph",
            "text": f"Source paragraph {i}. Derrida develops one continuous argument here.",
            "bbox": [10.0, 10.0 + i, 500.0, 20.0 + i],
            "extraction_method": "native",
            "confidence": 1.0,
        }
        for i in range(count)
    ]


def _build(repo: cb.PdfCorpusRepository, *, blocks: int = 30):
    """Create a temp build referring to pdf-test with the given block count."""
    return repo.create_build({
        "asset_id": "pdf-test",
        "source_sha256": "abc",
        "source_filename": "test.pdf",
        "source_page_count": 3,
        "source_block_count": blocks,
        "schema_version": cb.SCHEMA_VERSION,
        "profile_id": cb.PROFILE_VERSION,
        "profile_version": 2,
        "provider": "ollama",
        "model": "test",
        "request": {},
        "warnings": [],
    })


def test_parse_json_robust_handles_common_model_wrappers_and_trailing_commas():
    """Extract the JSON object from a fenced reply with trailing commas and extra text."""
    raw = '''Here is the requested object:\n```json\n{"boundaries": [{"after_block_id": "p001-b001", "decision": "keep", "confidence": 0.9, "reason": "continuous", "change": {},},],}\n```\nextra'''
    parsed = cb._parse_json_robust(raw)
    assert parsed["boundaries"][0]["after_block_id"] == "p001-b001"


def test_chat_json_repairs_malformed_json_before_spending_a_retry(monkeypatch, tmp_path: Path):
    """A syntax-only JSON defect is repaired locally and validated in one model call."""
    calls = []

    def fake_chat_complete(**kwargs):
        calls.append(kwargs)
        return '{"boundaries": [],}'

    monkeypatch.setattr(cb, "chat_complete", fake_chat_complete)
    manager = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"), max_workers=1)
    result = manager._chat_json(
        {"provider": "ollama", "model": "test"},
        "segment",
        response_model=cb.SegmentationResponseModel,
        attempts=3,
    )
    assert result == {"boundaries": []}
    assert len(calls) == 1


def test_chat_json_retries_cutoff_with_distinct_prompt_and_larger_budget(monkeypatch, tmp_path: Path):
    """A token-limited response is not repaired; retry restarts with more output budget."""
    calls = []

    def fake_chat_complete(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise cb.StructuredJsonTruncatedError(
                "cut off",
                diagnostic='{"boundaries": [',
                finish_reason="length",
            )
        return '{"boundaries": []}'

    monkeypatch.setattr(cb, "chat_complete", fake_chat_complete)
    manager = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"), max_workers=1)
    result = manager._chat_json(
        {"provider": "ollama", "model": "test"},
        "segment",
        response_model=cb.SegmentationResponseModel,
        attempts=2,
        max_tokens=1200,
    )
    assert result == {"boundaries": []}
    assert len(calls) == 2
    assert "OUTPUT LIMIT CORRECTION" in calls[1]["prompt"]
    assert "do not continue the partial object" in calls[1]["prompt"]
    assert calls[1]["max_tokens"] >= 1800


def test_chat_json_retries_malformed_output_then_validates(monkeypatch, tmp_path: Path):
    """Unrepairable JSON is retried with a syntax-specific note and a larger token budget."""
    calls = []

    def fake_chat_complete(**kwargs):
        calls.append(kwargs)
        if len(calls) < 3:
            return "not json at all"
        return '{"boundaries": []}'

    monkeypatch.setattr(cb, "chat_complete", fake_chat_complete)
    manager = cb.PdfCorpusBuildManager(cb.PdfCorpusRepository(tmp_path / "repo"), max_workers=1)
    result = manager._chat_json(
        {"provider": "ollama", "model": "test"},
        "segment",
        response_model=cb.SegmentationResponseModel,
        attempts=3,
    )
    assert result == {"boundaries": []}
    assert len(calls) == 3
    assert "JSON SYNTAX CORRECTION" in calls[1]["prompt"]
    assert calls[1]["max_tokens"] > calls[0]["max_tokens"]


def test_chat_json_records_prompt_and_keeps_live_draft_off_realtime(monkeypatch, tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build = _build(repo)
    operation_events.drain()

    def fake_chat_complete(**kwargs):
        on_delta = kwargs.get("on_delta")
        assert callable(on_delta)
        on_delta('{"boundaries":')
        live = manager.llm_live_output(build["build_id"])
        assert live["total"] == 1
        assert live["items"][0]["text"] == '{"boundaries":'
        on_delta("[]}")
        return '{"boundaries": []}'

    monkeypatch.setattr(cb, "chat_complete", fake_chat_complete)
    result = manager._chat_json(
        {
            "provider": "ollama",
            "model": "trace-test",
            "base_url": "http://example.invalid",
            "api_key": "SECRET-MUST-NOT-BE-PERSISTED",
        },
        "rendered source-bound prompt",
        response_model=cb.SegmentationResponseModel,
        schema_name="trace_schema",
        build_id=build["build_id"],
    )

    assert result == {"boundaries": []}
    assert manager.llm_live_output(build["build_id"]) == {"items": [], "total": 0}

    trace = manager.llm_trace(build["build_id"])
    assert trace["total"] == 1
    entry = trace["items"][0]
    assert entry["prompt"] == "rendered source-bound prompt"
    assert entry["provider"] == "ollama"
    assert entry["model"] == "trace-test"
    assert entry["schema_name"] == "trace_schema"
    assert entry["raw_response"] == '{"boundaries": []}'
    assert entry["validated_response"] == {"boundaries": []}
    assert entry["status"] == "complete"
    serialized = json.dumps(entry)
    assert "SECRET-MUST-NOT-BE-PERSISTED" not in serialized
    assert "base_url" not in entry

    progress = operation_events.drain().corpus_generation
    assert progress and progress[-1]["final"] is True
    # The realtime note is deliberately text-free; the draft is readable only
    # through the administrator-authenticated live-output endpoint.
    assert set(progress[-1]) == {"build_id", "call_id", "seq", "chars", "gap", "final"}
    assert "rendered source-bound prompt" not in str(progress)


def test_segment_blocks_instead_of_fabricating_record_when_every_llm_response_is_invalid(monkeypatch, tmp_path: Path):
    """Even if every LLM answer is unusable, segmentation stays sound and unblocked.

    Boundaries then come only from the deterministic normalizer; the build is not blocked and has no
    failed windows or review items.
    """
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: "LLM did not return a valid JSON object.")
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build = _build(repo)
    boundaries = manager._segment(_blocks(), {}, {"provider": "ollama", "model": "test"}, build["build_id"])
    assert all(item.get("source")=="deterministic_topology_normalizer" for item in boundaries)
    refreshed = repo.get_build(build["build_id"])
    assert refreshed.get("segmentation_blocked") is False
    assert refreshed.get("segmentation_failed_windows", 0) == 0
    assert refreshed.get("boundary_review_count", 0) == 0


def test_enrichment_failure_returns_reviewable_record_not_exception(monkeypatch, tmp_path: Path):
    """An HTML/garbage reply during enrichment yields a flagged record, not a crash.

    The record comes back with metadata_needs_attention, incomplete metadata, and still has citation
    strings, so a reviewer can finish it by hand.
    """
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: "<html>502 but rendered as text</html>")
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build = _build(repo, blocks=1)
    record = {
        "record_id": "test-00001",
        "record_revision": 1,
        "text": "A source paragraph.",
        "text_length": 19,
        "page_start": 1,
        "page_end": 1,
        "pdf_file": "test.pdf",
        "pdf_pages": [1],
        "source_asset_id": "pdf-test",
        "source_block_ids": ["p001-b001"],
        "source_spans": [{"block_id": "p001-b001", "page": 1}],
        "needs_review": False,
        "accepted": False,
    }
    result = manager._enrich_record(
        record,
        {"title": "Test", "document_author": "Jacques Derrida", "publication_year": 1999},
        {"provider": "ollama", "model": "test"},
        build_id=build["build_id"],
    )
    assert result["needs_review"] is False
    assert result["metadata_needs_attention"] is True
    assert result["metadata_complete"] is False
    assert result["metadata_incomplete_fields"]
    assert "inline_citation" in result


def test_parse_json_robust_accepts_safe_python_literal_objects_from_local_models():
    """Accept a Python-style dict ('single quotes', True, None) from a local model."""
    raw = "{'boundaries': [], 'ok': True, 'note': None}"
    parsed = cb._parse_json_robust(raw)
    assert parsed == {"boundaries": [], "ok": True, "note": None}


def _install_asset(repo: cb.PdfCorpusRepository, blocks: list[dict]):
    """Write an asset and its blocks to the temp repository."""
    asset={
        "asset_id":"pdf-test","sha256":"abc","filename":"test.pdf","page_count":max(int(b["page"]) for b in blocks),
        "block_count":len(blocks),"ocr_pages":0,"warnings":[],"metadata":{},"pages":[],
    }
    cb._json_write(repo.asset_meta_path("pdf-test"), asset)
    with repo.asset_blocks_path("pdf-test").open("w",encoding="utf-8") as handle:
        for block in blocks: handle.write(json.dumps(block)+"\n")
    return asset


def test_run_stops_before_record_construction_when_segmentation_is_unresolved(monkeypatch, tmp_path: Path):
    """A run with truncated LLM output still reaches review with records.

    30 blocks and a model that returns "truncated {" leave the build "awaiting_review" with
    records written (deterministic size splitting), rather than failing outright.
    """
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: "truncated {")
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    blocks=_blocks(30)
    _install_asset(repo,blocks)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_build(repo,blocks=len(blocks))
    manager._run(build["build_id"], {"provider":"ollama","model":"test"})
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="awaiting_review"
    assert refreshed["record_count"]>0
    assert repo.build_records_path(build["build_id"]).exists()


def test_long_source_with_valid_empty_boundary_arrays_is_blocked_by_topology_guard(monkeypatch,tmp_path:Path):
    """A long source where the LLM finds no boundaries is still split by size.

    80 long blocks and an always-empty boundary list produce size-based boundaries only, marked
    provisional, with no blocking and no review items.
    """
    monkeypatch.setattr(cb,"chat_complete",lambda **kwargs:'{"boundaries": []}')
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    blocks=[{**b,"text":b["text"]+(" argument"*40)} for b in _blocks(80)]
    build=_build(repo,blocks=len(blocks))
    boundaries=manager._segment(blocks,{}, {"provider":"ollama","model":"test"}, build["build_id"])
    assert boundaries
    assert all(item.get("boundary_kind") in {"retrieval_size_optimized","absolute_size_safety"} for item in boundaries)
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["segmentation_blocked"] is False
    assert refreshed["segmentation_degraded"] is False
    assert refreshed["boundary_review_count"] == 0
    assert refreshed["provisional_boundary_count"] >= 1
    assert refreshed["segmentation_unresolved_regions"] == []


def test_execution_budget_rejects_impossible_context_before_build():
    """A context window smaller than the requested prompt plus output fails up front.

    Why: better a clear "context is too small" error than hours of truncated LLM output.
    """
    request={"generation":{"num_ctx":4096},"stage_limits":{"segmentation_window_tokens":5000,"segmentation_num_predict":1200}}
    try:
        cb._validate_execution_budget(request)
    except ValueError as exc:
        assert "context is too small" in str(exc)
    else:
        raise AssertionError("expected preflight failure")


def test_finished_corpus_operation_can_be_hidden_without_deleting_build(tmp_path:Path):
    """Removing a finished operation from the list keeps the underlying build."""
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_build(repo)
    build["status"]="blocked"
    repo.save_build(build)
    assert manager.list_operations()
    manager.delete(build["build_id"])
    assert manager.list_operations()==[]
    assert repo.get_build(build["build_id"])["status"]=="blocked"


def test_reconciliation_failure_is_an_explicit_topology_blocker(monkeypatch, tmp_path: Path):
    """A classifier failure on the only candidate keeps the blocks together and is counted."""
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    blocks = _blocks(12)
    build = _build(repo, blocks=len(blocks))

    monkeypatch.setattr(cse, "_deterministic_boundary_candidates", lambda *args, **kwargs: [{"after_block_id": blocks[5]["block_id"], "next_block_id": blocks[6]["block_id"], "signals": ["quotation_frame_change"], "candidate_score": .5, "source": "test", "index": 5, "protected": False}])
    monkeypatch.setattr(manager, "_segment_candidate_batch", lambda *args, **kwargs: ({}, "truncated"))
    boundaries = manager._segment(blocks, {}, {"provider": "ollama", "model": "test"}, build["build_id"])
    assert boundaries == []
    refreshed = repo.get_build(build["build_id"])
    assert refreshed["segmentation_blocked"] is False
    assert refreshed["segmentation_degraded"] is False
    assert refreshed["segmentation_unresolved_regions"] == []
    assert refreshed["boundary_classifier_failure_count"] == 1


def test_cosmopolitanism_scale_empty_segmentation_cannot_collapse_to_one_record(monkeypatch, tmp_path: Path):
    """Regression shape for the 75-page / ~111k-char Cosmopolitanism failure.

    The fixture is synthetic so the packaged test suite does not depend on a
    copyrighted source PDF, but it matches the extracted block/character scale
    that previously collapsed into one giant record when the model returned no
    validated boundaries.
    """
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: '{"boundaries": []}')
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    blocks = []
    for index in range(227):
        text = (f"Scholarly source block {index}. " + "argument relation discourse attribution " * 12).strip()
        blocks.append({
            "block_id": f"p{1 + index // 4:05d}-b{index:04d}",
            "page": 1 + index // 4,
            "printed_page_label": str(1 + index // 4),
            "type": "paragraph",
            "text": text,
            "bbox": [10, 10, 500, 20],
            "extraction_method": "native",
            "confidence": 1.0,
        })
    assert sum(len(block["text"]) for block in blocks) > 100_000
    build = _build(repo, blocks=len(blocks))
    boundaries = manager._segment(blocks, {}, {"provider": "ollama", "model": "test"}, build["build_id"])
    assert boundaries
    assert all(item.get("boundary_kind") in {"retrieval_size_optimized","absolute_size_safety"} for item in boundaries)
    refreshed = repo.get_build(build["build_id"])
    assert refreshed["segmentation_blocked"] is False
    assert all(item.get("kind") == "provisional_size_split" for item in refreshed["segmentation_unresolved_regions"])


def test_blocked_segmentation_resume_marks_retry_and_is_idempotent_while_active(monkeypatch, tmp_path: Path):
    """Resuming a blocked build queues one retry; a second resume does not start another.

    The operation reports "Retrying 1 unresolved segmentation region(s)", the blocked flag is kept
    until the retry resolves it, and only one background job is submitted.
    """
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build = _build(repo, blocks=30)
    build.update({
        "status": "blocked",
        "stage": "segmentation_review",
        "segmentation_blocked": True,
        "segmentation_unresolved_regions": [{
            "kind": "topology_guard_no_boundaries",
            "start_block_id": "p001-b000",
            "end_block_id": "p003-b029",
        }],
        "resumable": True,
    })
    repo.save_build(build)
    submissions = []
    monkeypatch.setattr(manager._executor, "submit", lambda *args, **kwargs: submissions.append((args, kwargs)))

    queued = manager.resume(build["build_id"], {"provider": "ollama", "model": "better-model"})
    assert queued["status"] == "queued"
    assert queued["retrying_segmentation"] is True
    assert queued["segmentation_blocked"] is True  # preserved until the retry resolves it

    operation = cb._operation_from_build(queued)
    assert operation["status"] == "queued"
    assert operation["raw_status"] == "queued"
    assert operation["stage_detail"] == "Retrying 1 unresolved segmentation region(s)"

    duplicate = manager.resume(build["build_id"], {"provider": "ollama", "model": "better-model"})
    assert duplicate["status"] == "queued"
    assert duplicate["retrying_segmentation"] is True
    assert len(submissions) == 1  # no second background worker


def test_restart_resume_preserves_build_contract_and_reviewed_records(monkeypatch, tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    _install_asset(repo, _blocks(3))
    build = _build(repo, blocks=3)
    saved_request = {
        "provider": "ollama", "model": "original",
        "topology_policy": {"mode": "source_units", "source_units_per_record": 2},
        "run_guidance": {"speaker": {"instructions": "Do not flatten attribution."}},
        "stage_limits": {"discourse_num_predict": 1234, "segmentation_num_predict": 4321},
        "document_intelligence_profile": "none",
    }
    build.update(status="running", stage="enriching", request=saved_request)
    repo.save_build(build)
    manifest = {"title": "Reviewed title", "document_author": "Reviewer"}
    repo.save_checkpoint(build["build_id"], "manifest", manifest)
    repo.save_checkpoint(build["build_id"], "boundaries", [{"after_block_id": "p001-b001"}])
    repo.save_records(build["build_id"], [{
        "record_id": "reviewed", "record_revision": 7, "text": "Not a replacement.",
        "accepted": True, "metadata_complete": True, "speaker": "Human reviewer",
    }])
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    assert repo.get_build(build["build_id"])["status"] == "interrupted"
    submissions = []
    monkeypatch.setattr(manager._executor, "submit", lambda *args: submissions.append(args))
    resumed = manager.resume(build["build_id"], {
        "model": "replacement", "api_key": "runtime-only", "stage_limits": {"discourse_num_predict": 2468},
    })
    assert resumed["request"]["topology_policy"] == saved_request["topology_policy"]
    assert resumed["request"]["run_guidance"] == saved_request["run_guidance"]
    assert resumed["request"]["stage_limits"] == {"discourse_num_predict": 2468, "segmentation_num_predict": 4321}
    assert resumed["request"]["document_intelligence_profile"] == "none"
    assert resumed["request"]["model"] == "replacement"
    assert "api_key" not in resumed["request"]
    assert submissions[0][2]["api_key"] == "runtime-only"
    assert submissions[0][3] is True
    assert repo.load_checkpoint(build["build_id"], "manifest") == manifest
    assert repo.get_record(build["build_id"], "reviewed")["record_revision"] == 7


def test_concurrent_resume_submits_one_worker(monkeypatch, tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    build.update(status="interrupted", resumable=True)
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    submissions = []
    monkeypatch.setattr(manager._executor, "submit", lambda *args: submissions.append(args))
    with ThreadPoolExecutor(max_workers=8) as callers:
        results = list(callers.map(lambda _: manager.resume(build["build_id"], {}), range(20)))
    assert all(result["status"] == "queued" for result in results)
    assert len(submissions) == 1


def test_resume_submission_failure_is_visible_and_recoverable(monkeypatch, tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    build.update(status="interrupted", resumable=True)
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    def fail(*args):
        raise RuntimeError("Executor unavailable")
    monkeypatch.setattr(manager._executor, "submit", fail)
    with pytest.raises(RuntimeError, match="Executor unavailable"):
        manager.resume(build["build_id"], {})
    failed = repo.get_build(build["build_id"])
    assert failed["status"] == "failed"
    assert failed["resumable"] is True
    assert "Executor unavailable" in failed["error"]


def test_enrichment_retries_transient_storage_contention(monkeypatch, tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build = _build(repo)
    attempts = []

    def flaky(*args):
        attempts.append(len(attempts))
        if len(attempts) < 3:
            raise PersistenceBusyError("storage busy")
        return [{"record_id": "settled"}]

    monkeypatch.setattr(manager, "_schedule_build_enrichment", flaky)
    monkeypatch.setattr(cb.time, "sleep", lambda _delay: None)

    result = manager._schedule_build_enrichment_with_lock_recovery(
        build["build_id"], {}, {}, []
    )

    assert result == [{"record_id": "settled"}]
    assert len(attempts) == 3
    assert repo.get_build(build["build_id"])["resumable"] is True
    manager._executor.shutdown(wait=True)


def test_exhausted_storage_contention_interrupts_instead_of_borking_build(monkeypatch, tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build = _build(repo)

    monkeypatch.setattr(
        manager,
        "_prepare_build_scope",
        lambda *_args, **_kwargs: types.SimpleNamespace(manifest={}),
    )
    monkeypatch.setattr(manager, "_construct_build_topology", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        manager,
        "_schedule_build_enrichment_with_lock_recovery",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            PersistenceBusyError("storage busy")
        ),
    )

    manager._run(build["build_id"], {})

    interrupted = repo.get_build(build["build_id"])
    assert interrupted["status"] == "interrupted"
    assert interrupted["stage"] == "interrupted"
    assert interrupted["interrupted_stage"] == "enriching"
    assert interrupted["resumable"] is True
    assert "checkpoints were preserved" in interrupted["error"]
    manager._executor.shutdown(wait=True)


def test_failed_build_resume_retires_orphaned_metadata_operation(monkeypatch, tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    build.update(
        status="failed",
        stage="failed",
        resumable=True,
        error="enriching: database is locked",
        metadata_operation={"state": "running", "operation_id": "op-lock"},
    )
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    submissions = []
    monkeypatch.setattr(
        manager._executor,
        "submit",
        lambda *args, **kwargs: submissions.append((args, kwargs)),
    )

    resumed = manager.resume(build["build_id"], {})

    assert resumed["status"] == "queued"
    assert resumed["error"] is None
    assert resumed["metadata_operation"]["state"] == "failed"
    assert resumed["metadata_operation"]["operation_id"] == "op-lock"
    assert len(submissions) == 1
    manager._executor.shutdown(wait=True)


def test_restart_retires_orphaned_metadata_operation_without_replay(tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    build.update(
        status="running", stage="metadata_enrichment_rerun",
        metadata_operation={"state": "running", "operation_id": "op-1"},
    )
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    interrupted = repo.get_build(build["build_id"])
    assert interrupted["interrupted_stage"] == "metadata_enrichment_rerun"
    assert interrupted["metadata_operation"]["state"] == "failed"
    assert interrupted["metadata_operation"]["operation_id"] == "op-1"
    assert "restart" in interrupted["metadata_operation"]["error"]
    assert not manager._runtime_requests
    manager._executor.shutdown(wait=True)


def test_resume_executes_saved_topology_and_preserves_reviewed_text(monkeypatch, tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    blocks = _blocks(3)
    _install_asset(repo, blocks)
    build = _build(repo, blocks=3)
    request = {
        "provider": "ollama", "model": "test", "memory_prefill": False,
        "document_intelligence_profile": "none",
        "topology_policy": {"mode": "source_units", "source_units_per_record": 1},
    }
    build["request"] = request
    repo.save_build(build)
    first = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: "{}")
    def stop_after_topology(*args, **kwargs):
        raise RuntimeError("Simulated interrupted enrichment")
    monkeypatch.setattr(first, "_schedule_build_enrichment", stop_after_topology)
    monkeypatch.setattr(cb.SourceEmbeddingProjection, "sync", lambda *args, **kwargs: {"status": "ready"})
    first._run(build["build_id"], request)
    records = repo.load_records(build["build_id"])
    assert len(records) == 3
    records[0].update(text="Human-reviewed text, not the extraction.", record_revision=7, accepted=True)
    repo.save_records(build["build_id"], records)
    saved = repo.get_build(build["build_id"])
    saved.update(status="running", stage="enriching")
    repo.save_build(saved)
    first._executor.shutdown(wait=True)
    restarted = cb.PdfCorpusBuildManager(repo, max_workers=1)
    resumed_text_edits = []
    run_document_intelligence = restarted._run_document_intelligence

    def review_during_resumed_preparation(build_id, current_records, manifest, current_request):
        snapshot = repo.get_build(build_id)
        assert snapshot["stage"] == "document_intelligence"
        assert snapshot["text_review_available_at"]
        assert snapshot["topology_validation"]["valid"] is True
        target = repo.get_record(build_id, records[0]["record_id"])
        assert target["text"] == records[0]["text"]
        assert target["record_revision"] == 7
        resumed_text_edits.append(restarted.patch_record_text(
            build_id, target["record_id"], "Another human correction during resumed preparation.",
            expected_revision=7,
        ))
        assert repo.get_build(build_id)["stage"] == "document_intelligence"
        with pytest.raises(ValueError, match="not editable"):
            restarted.patch_metadata(build_id, target["record_id"], {"primary_text": True})
        with pytest.raises(ValueError, match="not editable"):
            restarted._assert_human_review_available(build_id, structural=True, text_only=True)
        return run_document_intelligence(build_id, current_records, manifest, current_request)

    monkeypatch.setattr(restarted, "_run_document_intelligence", review_during_resumed_preparation)
    submitted = []
    submit = restarted._executor.submit
    def capture(*args, **kwargs):
        future = submit(*args, **kwargs)
        submitted.append(future)
        return future
    monkeypatch.setattr(restarted._executor, "submit", capture)
    restarted.resume(build["build_id"], {})
    submitted[0].result(timeout=30)
    final = repo.get_build(build["build_id"])
    assert final["status"] == "awaiting_review", final.get("error")
    assert len(resumed_text_edits) == 1
    assert repo.get_record(build["build_id"], records[0]["record_id"])["text"] == resumed_text_edits[0]["text"]
    assert repo.get_record(build["build_id"], records[0]["record_id"])["record_revision"] >= resumed_text_edits[0]["record_revision"]
    assert final["request"]["topology_policy"] == request["topology_policy"]
    restarted._executor.shutdown(wait=True)


@pytest.mark.parametrize("damage", ["gap", "overlap", "order", "unknown_source", "empty_text"])
def test_resume_rechecks_topology_before_exposing_text_review(monkeypatch, tmp_path, damage):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    blocks = _blocks(3)
    _install_asset(repo, blocks)
    build = _build(repo, blocks=3)
    records = cb._construct_records(repo.get_asset(build["asset_id"]), blocks, [
        {"after_block_id": block["block_id"], "decision": "split"} for block in blocks[:-1]
    ])
    if damage == "gap":
        records.pop()
    elif damage == "overlap":
        records[1]["source_block_ids"] = records[0]["source_block_ids"]
    elif damage == "order":
        records.reverse()
    elif damage == "unknown_source":
        records[0]["source_block_ids"].append("missing-source-unit")
    else:
        records[0]["text"] = ""
    repo.save_records(build["build_id"], records)
    build.update(topology_validation={"valid": True}, text_review_available_at="2026-10-03T00:00:00Z")
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    inspected = []

    def inspect_preparation(build_id, *args):
        snapshot = repo.get_build(build_id)
        inspected.append(snapshot)
        assert snapshot["text_review_available_at"] is None
        assert snapshot["topology_validation"]["valid"] is False
        with pytest.raises(ValueError, match="not editable"):
            manager._assert_human_review_available(build_id, text_only=True)
        raise RuntimeError("Stop after checking resumed readiness")

    monkeypatch.setattr(manager, "_run_document_intelligence", inspect_preparation)
    try:
        manager._run(build["build_id"], {
            "topology_policy": {"mode": "source_units", "source_units_per_record": 1},
            "document_intelligence_profile": "none", "memory_prefill": False,
        }, resume=True)
        assert len(inspected) == 1
        assert "Stop after checking resumed readiness" in repo.get_build(build["build_id"])["error"]
        assert repo.load_records(build["build_id"]) == records
    finally:
        manager._executor.shutdown(wait=True)


def test_topology_is_durable_before_optional_embedding_work(monkeypatch, tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    _install_asset(repo, _blocks(3))
    build = _build(repo, blocks=3)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    observed = []
    edited = []
    def inspect_projection(*args, **kwargs):
        stored = repo.load_records(build["build_id"])
        observed.append(len(stored))
        snapshot = repo.get_build(build["build_id"])
        assert snapshot["record_count"] == len(stored)
        assert snapshot["topology_persisted_at"]
        assert snapshot["text_review_available_at"]
        assert not snapshot.get("review_available_at")
        with pytest.raises(ValueError, match="not editable"):
            manager._assert_human_review_available(build["build_id"])
        with pytest.raises(ValueError, match="not editable"):
            manager._assert_human_review_available(build["build_id"], structural=True, text_only=True)
        target = stored[0]
        edited.append(manager.patch_record_text(
            build["build_id"], target["record_id"], "Human correction before optional work.",
            expected_revision=target["record_revision"],
        ))
        with pytest.raises(ValueError, match="not editable"):
            manager.patch_metadata(build["build_id"], target["record_id"], {"primary_text": True})
        return {"status": "ready"}
    monkeypatch.setattr(cb.SourceEmbeddingProjection, "sync", inspect_projection)
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: "{}")
    manager._run(build["build_id"], {
        "provider": "ollama", "model": "test", "memory_prefill": False,
        "document_intelligence_profile": "none",
        "topology_policy": {"mode": "source_units", "source_units_per_record": 1},
    })
    assert observed == [3]
    final = repo.get_build(build["build_id"])
    current = repo.get_record(build["build_id"], edited[0]["record_id"])
    assert current["text"] == edited[0]["text"]
    assert current["source_extracted_text"] != current["text"]
    assert current["text_review_source"] == "human"
    assert current["record_revision"] >= edited[0]["record_revision"]
    assert final["text_review_available_at"] <= final["review_available_at"]
    assert final["topology_persisted_at"] <= final["review_available_at"] <= final["metadata_first_settled_at"]
    manager._executor.shutdown(wait=True)

@pytest.mark.parametrize("stage, milestone, valid", [
    ("constructing_records", None, True),
    ("constructing_records", "2026-10-03T00:00:00Z", False),
    ("segmenting", "2026-10-03T00:00:00Z", True),
    ("constructing_topology", "2026-10-03T00:00:00Z", True),
])
def test_preparation_text_review_rejects_missing_or_incompatible_readiness(tmp_path, stage, milestone, valid):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build.update(status="running", stage=stage, text_review_available_at=milestone, topology_validation={"valid": valid})
    repo.save_build(build)
    try:
        with pytest.raises(ValueError, match="not editable"):
            manager._assert_human_review_available(build["build_id"], text_only=True)
    finally:
        manager._executor.shutdown(wait=True)


def test_preparation_resets_text_review_milestone_before_resume(tmp_path, monkeypatch):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build.update(status="running", stage="constructing_records",
                 text_review_available_at="2026-10-03T00:00:00Z", topology_validation={"valid": True})
    repo.save_build(build)
    observed = []

    def prepare(build_id, request, resume):
        snapshot = repo.get_build(build_id)
        observed.append(snapshot["text_review_available_at"])
        assert snapshot["stage"] == "preparing"
        assert resume is True
        with pytest.raises(ValueError, match="not editable"):
            manager._assert_human_review_available(build_id, text_only=True)
        return None

    monkeypatch.setattr(manager, "_prepare_build_scope", prepare)
    try:
        manager._run(build["build_id"], {}, resume=True)
        assert observed == [None]
    finally:
        manager._executor.shutdown(wait=True)


def test_record_context_enforces_budget_and_retains_exact_locator(tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    repo.save_records(build["build_id"], [
        {"record_id": "before", "record_revision": 2, "text": "before-text", "source_document_id": "doc"},
        {"record_id": "focus", "text": "focus"},
        {"record_id": "after", "record_revision": 3, "text": "after-text", "source_document_id": "doc"},
    ])
    context = repo.record_context(build["build_id"], "focus", max_chars=8)
    assert context["truncated"] is True
    assert context["before"][0]["text"] == "text"
    assert context["after"][0]["text"] == "afte"
    assert sum(len(item["text"]) for item in context["before"] + context["after"]) == 8
    previous = context["before"][0]
    assert previous["record_revision"] == 2
    assert previous["record_character_start"] == 7
    assert previous["record_character_end"] == 11
    assert previous["text_truncated"] is True
    assert not repo.record_context(build["build_id"], "focus", max_chars=0)["before"]


def test_sparse_resume_sizing_is_validated_against_saved_settings(monkeypatch, tmp_path):
    from app.models import PdfCorpusBuildResume
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    build.update(status="interrupted", resumable=True, request={
        "record_sizing": {
            "preferred_record_chars": 5000, "record_length_tolerance": 200,
            "long_record_chars": 7000, "absolute_record_chars": 9000,
        },
    })
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    monkeypatch.setattr(manager._executor, "submit", lambda *args: None)
    overrides = PdfCorpusBuildResume(record_sizing={"preferred_record_chars": 6000})
    resumed = manager.resume(build["build_id"], overrides.model_dump(exclude_unset=True, exclude_none=True))
    assert resumed["request"]["record_sizing"]["preferred_record_chars"] == 6000
    assert resumed["request"]["record_sizing"]["long_record_chars"] == 7000
    manager._executor.shutdown(wait=True)



def test_resume_reuses_current_document_intelligence(monkeypatch, tmp_path: Path):
    """A paused/resumed build must not redo whole-document NLP when its binding is unchanged."""
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    records = [{"record_id": "r1", "text": "Stable documentary text."}]
    persisted = {
        "version": cb.DOCUMENT_INTELLIGENCE_VERSION,
        "status": "ok",
        "stale": False,
        "profile": "scholarly",
        "selected_provider": "auto",
        "configuration": {"include_events": False, "language": "en"},
    }
    monkeypatch.setattr(
        manager,
        "_document_intelligence_for_records",
        lambda build_id, rows: dict(persisted),
    )

    reused = manager._reusable_document_intelligence(
        "build-1",
        records,
        {"language": "en"},
        {
            "document_intelligence_profile": "scholarly",
            "document_nlp_provider": "auto",
            "document_nlp_include_events": False,
        },
    )
    assert reused == persisted

    changed = manager._reusable_document_intelligence(
        "build-1",
        records,
        {"language": "en"},
        {
            "document_intelligence_profile": "scholarly",
            "document_nlp_provider": "auto",
            "document_nlp_include_events": True,
        },
    )
    assert changed is None


def test_cancel_persists_intent_and_exposes_cancelling_stage(tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    build.update(
        status="running",
        stage="enriching",
        metadata_operation={"state": "running", "operation_id": "op-1"},
    )
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    try:
        cancelled = manager.cancel(build["build_id"])
        assert cancelled["status"] == "running"
        assert cancelled["stage"] == "cancelling"
        assert cancelled["stage_before_cancel"] == "enriching"
        assert cancelled["cancel_requested"] is True
        assert cancelled["cancel_requested_at"]
        assert cancelled["metadata_operation"]["state"] == "cancelling"

        persisted = repo.get_build(build["build_id"])
        assert persisted["cancel_requested"] is True
        assert persisted["stage"] == "cancelling"
        assert manager._cancelled(build["build_id"]) is True
    finally:
        manager._executor.shutdown(wait=True)


def test_durable_cancel_flag_is_honoured_without_live_token(tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    build.update(status="running", stage="enriching", cancel_requested=True)
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    try:
        manager._cancel.discard(build["build_id"])
        assert manager._cancelled(build["build_id"]) is True
        assert build["build_id"] in manager._cancel
    finally:
        manager._executor.shutdown(wait=True)


def test_worker_progress_cannot_erase_cancelling_stage(tmp_path):
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    build = _build(repo)
    build.update(status="running", stage="enriching")
    repo.save_build(build)
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    try:
        manager.cancel(build["build_id"])
        updated = manager._update(
            build["build_id"],
            status="running",
            stage="metadata_family",
            progress=0.75,
        )
        assert updated["stage"] == "cancelling"

        terminal = manager._update(
            build["build_id"],
            status="cancelled",
            stage="cancelled",
            resumable=True,
        )
        assert terminal["status"] == "cancelled"
        assert terminal["stage"] == "cancelled"
    finally:
        manager._executor.shutdown(wait=True)
