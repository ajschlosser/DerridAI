from __future__ import annotations

from pathlib import Path
import json
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

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


def _blocks(count: int = 30):
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
    raw = '''Here is the requested object:\n```json\n{"boundaries": [{"after_block_id": "p001-b001", "decision": "keep", "confidence": 0.9, "reason": "continuous", "change": {},},],}\n```\nextra'''
    parsed = cb.PdfCorpusBuildManager._parse_json_robust(raw)
    assert parsed["boundaries"][0]["after_block_id"] == "p001-b001"


def test_chat_json_retries_malformed_output_then_validates(monkeypatch, tmp_path: Path):
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
    assert "previous response could not be validated" in calls[1]["prompt"]
    assert calls[1]["max_tokens"] > calls[0]["max_tokens"]


def test_segment_blocks_instead_of_fabricating_record_when_every_llm_response_is_invalid(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: "LLM did not return a valid JSON object.")
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build = _build(repo)
    boundaries = manager._segment(_blocks(), {}, {"provider": "ollama", "model": "test"}, build["build_id"])
    assert boundaries == []
    refreshed = repo.get_build(build["build_id"])
    assert refreshed.get("segmentation_blocked") is True
    assert refreshed.get("segmentation_failed_windows", 0) > 0
    assert refreshed.get("segmentation_unresolved_regions")
    assert any("no record set was constructed" in warning.casefold() for warning in refreshed.get("warnings") or [])


def test_enrichment_failure_returns_reviewable_record_not_exception(monkeypatch, tmp_path: Path):
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
    assert result["needs_review"] is True
    assert result["metadata_complete"] is False
    assert "could not be validated" in result["review_reason"]
    assert "inline_citation" in result


def test_parse_json_robust_accepts_safe_python_literal_objects_from_local_models():
    raw = "{'boundaries': [], 'ok': True, 'note': None}"
    parsed = cb.PdfCorpusBuildManager._parse_json_robust(raw)
    assert parsed == {"boundaries": [], "ok": True, "note": None}


def _install_asset(repo: cb.PdfCorpusRepository, blocks: list[dict]):
    asset={
        "asset_id":"pdf-test","sha256":"abc","filename":"test.pdf","page_count":max(int(b["page"]) for b in blocks),
        "block_count":len(blocks),"ocr_pages":0,"warnings":[],"metadata":{},"pages":[],
    }
    cb._json_write(repo.asset_meta_path("pdf-test"), asset)
    with repo.asset_blocks_path("pdf-test").open("w",encoding="utf-8") as handle:
        for block in blocks: handle.write(json.dumps(block)+"\n")
    return asset


def test_run_stops_before_record_construction_when_segmentation_is_unresolved(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: "truncated {")
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    blocks=_blocks(30)
    _install_asset(repo,blocks)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_build(repo,blocks=len(blocks))
    manager._run(build["build_id"], {"provider":"ollama","model":"test","review_manifest_before_segmentation":False})
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["status"]=="blocked"
    assert refreshed["record_count"]==0
    assert not repo.build_records_path(build["build_id"]).exists()


def test_long_source_with_valid_empty_boundary_arrays_is_blocked_by_topology_guard(monkeypatch,tmp_path:Path):
    monkeypatch.setattr(cb,"chat_complete",lambda **kwargs:'{"boundaries": []}')
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    blocks=[{**b,"text":b["text"]+(" argument"*40)} for b in _blocks(80)]
    build=_build(repo,blocks=len(blocks))
    boundaries=manager._segment(blocks,{}, {"provider":"ollama","model":"test"}, build["build_id"])
    assert boundaries==[]
    refreshed=repo.get_build(build["build_id"])
    assert refreshed["segmentation_blocked"] is True
    assert any(item.get("kind")=="topology_guard_no_boundaries" for item in refreshed["segmentation_unresolved_regions"])


def test_execution_budget_rejects_impossible_context_before_build():
    request={"generation":{"num_ctx":4096},"stage_limits":{"segmentation_window_tokens":5000,"segmentation_num_predict":1200}}
    try:
        cb.PdfCorpusBuildManager._validate_execution_budget(request)
    except ValueError as exc:
        assert "context is too small" in str(exc)
    else:
        raise AssertionError("expected preflight failure")


def test_finished_corpus_operation_can_be_hidden_without_deleting_build(tmp_path:Path):
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
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    blocks = _blocks(12)
    build = _build(repo, blocks=len(blocks))

    # Pretend first-pass segmentation produced one plausible but uncertain split.
    monkeypatch.setattr(
        manager,
        "_segment_window_recursive",
        lambda *args, **kwargs: ([{
            "after_block_id": blocks[5]["block_id"],
            "decision": "uncertain",
            "confidence": 0.61,
            "changes": ["discourse_role"],
            "source": "test",
        }], []),
    )
    # Reconciliation itself must not silently turn malformed output into KEEP.
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: "truncated {")
    boundaries = manager._segment(blocks, {}, {"provider": "ollama", "model": "test"}, build["build_id"])
    assert boundaries == []
    refreshed = repo.get_build(build["build_id"])
    assert refreshed["segmentation_blocked"] is True
    assert any(item.get("kind") == "reconciliation" for item in refreshed["segmentation_unresolved_regions"])


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
    assert boundaries == []
    refreshed = repo.get_build(build["build_id"])
    assert refreshed["segmentation_blocked"] is True
    assert any(item.get("kind") == "topology_guard_no_boundaries" for item in refreshed["segmentation_unresolved_regions"])


def test_manifest_review_checkpoint_stops_before_segmentation_and_confirm_resumes(monkeypatch, tmp_path: Path):
    repo=cb.PdfCorpusRepository(tmp_path/"repo")
    blocks=_blocks(8)
    _install_asset(repo,blocks)
    manager=cb.PdfCorpusBuildManager(repo,max_workers=1)
    build=_build(repo,blocks=len(blocks))
    monkeypatch.setattr(manager,"_document_manifest",lambda *args,**kwargs:{"title":"Test","document_author":"Jacques Derrida"})
    called={"segment":0}
    monkeypatch.setattr(manager,"_segment",lambda *args,**kwargs: called.__setitem__("segment",called["segment"]+1) or [])
    manager._run(build["build_id"], {"provider":"ollama","model":"test","review_manifest_before_segmentation":True})
    paused=repo.get_build(build["build_id"])
    assert paused["status"]=="awaiting_manifest_review"
    assert paused["stage"]=="document_review"
    assert called["segment"]==0
    # Confirming records the reviewed manifest revision before queueing resume.
    monkeypatch.setattr(manager._executor,"submit",lambda *args,**kwargs: None)
    queued=manager.confirm_manifest(build["build_id"], {"provider":"ollama","model":"test","review_manifest_before_segmentation":True})
    assert queued["status"]=="queued"
    confirmed=repo.get_build(build["build_id"])
    assert confirmed.get("manifest_confirmed_at")
    assert confirmed.get("manifest_confirmed_revision")==1
