"""Regression coverage for corpus-neutral built-in LLM prompts.

Built-in prompts may use source metadata supplied at runtime, especially
`document_author`, but must not bake a particular author or work into the
instructions.  That distinction lets the same pipeline operate over arbitrary
corpora without weakening attribution provenance.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

corpus_segmentation_execution = importlib.import_module("app.corpus_segmentation_execution")
llm = importlib.import_module("app.llm")
llm_tools = importlib.import_module("app.llm_tools")
models = importlib.import_module("app.models")
rag = importlib.import_module("app.rag")


PROMPT_SOURCE_PATHS = (
    "api/app/llm.py",
    "api/app/rag.py",
    "api/app/llm_tools.py",
    "api/app/corpus_segmentation_execution.py",
    "api/app/corpus_metadata_enrichment_execution.py",
    "web/src/components/metadata-schemas/SchemaPreviewPanel.vue",
)

LEGACY_HARDCODED_REFERENCES = (
    r"\bDerrida\b",
    r"\bFreud\b",
    r"\bLevinas\b",
    r"\bHeidegger\b",
    r"\bFukuyama\b",
    r"\bKant\b",
    r"\bHusserl\b",
    r"\bRousseau\b",
    r"\bHobbes\b",
    r"\bOf Grammatology\b",
    r"\bArchive Fever\b",
    r"\bOf Hospitality\b",
)


def test_builtin_prompt_sources_do_not_hardcode_authors_or_works() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative_path in PROMPT_SOURCE_PATHS:
        text = (root / relative_path).read_text(encoding="utf-8")
        for pattern in LEGACY_HARDCODED_REFERENCES:
            assert re.search(pattern, text, re.IGNORECASE) is None, (
                f"{relative_path} contains hard-coded prompt reference {pattern}"
            )


def test_record_audit_and_research_prompts_use_document_author_context() -> None:
    assert "record_context.document_author" in llm.SYSTEM_PROMPT
    assert "default author" in llm.SYSTEM_PROMPT
    assert "document_author from each evidence record" in rag.FOCUSED_PROMPT
    assert "Do not equate document authorship with proposition ownership" in rag.FOCUSED_PROMPT
    root = Path(__file__).resolve().parents[1]
    enrichment_source = (root / "api/app/corpus_metadata_enrichment_execution.py").read_text(
        encoding="utf-8"
    )
    assert "use it as source-document authorship context" in enrichment_source


class _SegmentationProbe(corpus_segmentation_execution.BuildSegmentationExecutionMixin):
    def __init__(self) -> None:
        self.last_prompt = ""

    def _chat_json(self, request, prompt, **kwargs):
        self.last_prompt = prompt
        return {"decision": "keep", "confidence": 1.0, "changes": []}


def test_segmentation_prompts_receive_document_author_dynamically() -> None:
    probe = _SegmentationProbe()
    manifest = {
        "title": "Sample Work",
        "document_author": "Sample Author",
        "language": "en",
        "document_type": "book",
    }
    blocks = [
        {"block_id": "b1", "page": 1, "type": "paragraph", "text": "First passage."},
        {"block_id": "b2", "page": 1, "type": "paragraph", "text": "Second passage."},
    ]

    compact = probe._compact_segment_prompt(blocks, manifest)
    assert '"document_author": "Sample Author"' in compact
    assert "source-document authorship context" in compact

    decision, failure = probe._segment_pair(
        blocks[0],
        blocks[1],
        manifest,
        {"provider": "ollama", "model": "test-model"},
        "build-test",
    )
    assert failure is None
    assert decision is not None
    assert '"document_author": "Sample Author"' in probe.last_prompt
    assert "source-document authorship context" in probe.last_prompt


def test_rag_grader_uses_evidence_document_author(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_chat_complete(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return '{"categories": {}, "overall": {"score": 0, "analysis": ""}}'

    monkeypatch.setattr(llm_tools, "chat_complete", fake_chat_complete)
    body = models.RAGGradeRequest(
        question="What follows from the passage?",
        answer="A source-bound answer.",
        provider="ollama",
        model="test-model",
        evidence=[
            {
                "evidence_id": "E0",
                "inline_citation": "(Sample Author, 1)",
                "record": {
                    "work": "Sample Work",
                    "document_author": "Sample Author",
                    "text": "A source passage.",
                },
            }
        ],
    )

    llm_tools.run_rag_grade(body, store=None)  # type: ignore[arg-type]

    prompt = captured["prompt"]
    assert "document_author=Sample Author" in prompt
    assert "source-document author" in prompt
    assert re.search(r"\bDerrida\b", prompt, re.IGNORECASE) is None
