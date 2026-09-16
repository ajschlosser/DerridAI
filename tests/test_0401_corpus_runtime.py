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


def test_segment_degrades_instead_of_failing_when_every_llm_response_is_invalid(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cb, "chat_complete", lambda **kwargs: "LLM did not return a valid JSON object.")
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    manager = cb.PdfCorpusBuildManager(repo, max_workers=1)
    build = _build(repo)
    boundaries = manager._segment(_blocks(), {}, {"provider": "ollama", "model": "test"}, build["build_id"])
    assert boundaries == []
    refreshed = repo.get_build(build["build_id"])
    assert refreshed.get("segmentation_degraded") is True
    assert refreshed.get("segmentation_failed_windows", 0) > 0
    assert any("segmentation" in warning.casefold() for warning in refreshed.get("warnings") or [])


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
