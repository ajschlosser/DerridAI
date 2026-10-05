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

"""Regression coverage for corpus-neutral built-in LLM prompts.

Built-in prompts may use source metadata supplied at runtime, especially
`document_author`, but must not bake a particular author or work into the
instructions.  That distinction lets the same pipeline operate over arbitrary
corpora without weakening attribution provenance.
"""

from __future__ import annotations

import importlib
import re
import types
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
    assert "source-document author" in rag.FOCUSED_PROMPT
    assert "Do not equate document authorship with proposition ownership" in rag.FOCUSED_PROMPT
    root = Path(__file__).resolve().parents[1]
    enrichment_source = (root / "api/app/corpus_metadata_enrichment_execution.py").read_text(
        encoding="utf-8"
    )
    assert "use it as source-document authorship context" in enrichment_source


class _SegmentationProbe(corpus_segmentation_execution.BuildSegmentationExecutionMixin):
    """Captures each boundary prompt instead of asking a model."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def _boundary_call(self, session, request, prompt, **kwargs):
        self.prompts.append(prompt)
        return {"decisions": []}

    def _boundary_editorial_examples(self, build_id, limit=3):
        return []


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
    request = {"provider": "ollama", "model": "test-model"}

    probe._segment_candidate_batch(
        [{"index": 0, "after_block_id": "b1", "signals": []}], blocks, manifest, request, "build-test", session=None
    )
    probe._adjudicate_record_boundary_pair(
        {"record_id": "r1", "text": "First passage.", "source_block_ids": ["b1"]},
        {"record_id": "r2", "text": "Second passage.", "source_block_ids": ["b2"]},
        manifest,
        request,
        "build-test",
        session=types.SimpleNamespace(identity=dict),
    )

    assert len(probe.prompts) == 2
    for prompt in probe.prompts:
        assert '"document_author": "Sample Author"' in prompt
        assert "source-document authorship context" in prompt


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
