"""Evidence-bound metadata exemplars for progressive enrichment."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.metadata_exemplars import (
    budget_prompt_examples,
    build_correction_exemplars,
    build_metadata_exemplar,
    prompt_example,
    prompt_example_token_estimate,
)


def blocks() -> dict[str, dict]:
    return {
        "b1": {"block_id": "b1", "page": 7, "text": "Derrida introduces the question of responsibility."},
        "b2": {
            "block_id": "b2",
            "page": 7,
            "text": "For Levinas, responsibility precedes the freedom of the subject.",
        },
        "b3": {"block_id": "b3", "page": 8, "text": "Derrida then complicates this formulation."},
    }


def reviewed_record(**overrides):
    record = {
        "record_id": "r1",
        "record_revision": 4,
        "source_document_id": "doc-1",
        "source_block_ids": ["b1", "b2", "b3"],
        "source_spans": [
            {"block_id": "b1", "page": 7},
            {"block_id": "b2", "page": 7, "bbox": [1, 2, 3, 4]},
            {"block_id": "b3", "page": 8},
        ],
        "text": (
            "Derrida introduces the question of responsibility. "
            "For Levinas, responsibility precedes the freedom of the subject. "
            "Derrida then complicates this formulation."
        ),
        "position_holder": "Levinas",
        "speaker": "Derrida",
        "discourse_role": "reported_position",
        "metadata_field_status": {
            "position_holder": {
                "status": "human_confirmed",
                "method": "human_review_of_llm_proposal",
            }
        },
        "metadata_evidence": {
            "position_holder": {
                "block_ids": ["b2"],
                "confidence": 0.94,
                "reason": "The proposition is explicitly introduced as Levinas's.",
            }
        },
    }
    record.update(overrides)
    return record


def test_build_metadata_exemplar_binds_field_to_exact_source_evidence():
    exemplar = build_metadata_exemplar(
        reviewed_record(),
        "position_holder",
        blocks(),
        schema_id="derrida",
        schema_version="v7",
    )

    assert exemplar is not None
    assert exemplar["field_name"] == "position_holder"
    assert exemplar["field_value"] == "Levinas"
    assert exemplar["record_revision"] == 4
    assert exemplar["evidence_text"] == blocks()["b2"]["text"]
    assert exemplar["context_text"] == "\n\n".join(
        blocks()[block_id]["text"] for block_id in ("b1", "b2", "b3")
    )
    assert exemplar["evidence_ref"]["block_ids"] == ["b2"]
    assert exemplar["evidence_ref"]["source_spans"] == [
        {"block_id": "b2", "page": 7, "bbox": [1, 2, 3, 4]}
    ]
    assert len(exemplar["evidence_ref"]["quote_hash"]) == 64
    assert exemplar["page_start"] == 7
    assert exemplar["page_end"] == 7


def test_exemplar_identity_changes_with_record_revision_or_evidence():
    original = build_metadata_exemplar(reviewed_record(), "position_holder", blocks())
    revised = build_metadata_exemplar(
        reviewed_record(record_revision=5),
        "position_holder",
        blocks(),
    )
    changed_blocks = blocks()
    changed_blocks["b2"] = {**changed_blocks["b2"], "text": "A changed source block."}
    changed_evidence = build_metadata_exemplar(
        reviewed_record(),
        "position_holder",
        changed_blocks,
    )

    assert original is not None and revised is not None and changed_evidence is not None
    assert original["metadata_exemplar_id"] != revised["metadata_exemplar_id"]
    assert original["metadata_exemplar_id"] != changed_evidence["metadata_exemplar_id"]


def test_unreviewed_or_stale_evidence_does_not_become_an_exemplar():
    unreviewed = reviewed_record(
        metadata_field_status={
            "position_holder": {"status": "model_inferred", "method": "llm"}
        }
    )
    human_correction_with_old_model_evidence = reviewed_record(
        position_holder="Derrida",
        metadata_field_status={
            "position_holder": {"status": "human_confirmed", "method": "human"}
        },
    )
    foreign_block = reviewed_record(
        metadata_evidence={
            "position_holder": {
                "block_ids": ["other-record-block"],
                "reviewed_by": "human",
            }
        }
    )

    assert build_metadata_exemplar(unreviewed, "position_holder", blocks()) is None
    assert (
        build_metadata_exemplar(
            human_correction_with_old_model_evidence,
            "position_holder",
            blocks(),
        )
        is None
    )
    assert build_metadata_exemplar(foreign_block, "position_holder", blocks()) is None


def test_explicit_human_evidence_allows_a_direct_human_value():
    record = reviewed_record(
        position_holder="Derrida",
        metadata_field_status={
            "position_holder": {"status": "human_confirmed", "method": "human"}
        },
        metadata_evidence={
            "position_holder": {
                "block_ids": ["b3"],
                "reviewed_by": "human",
                "reviewed_at": "2026-09-23T10:00:00Z",
            }
        },
    )

    exemplar = build_metadata_exemplar(record, "position_holder", blocks())

    assert exemplar is not None
    assert exemplar["field_value"] == "Derrida"
    assert exemplar["evidence_text"] == blocks()["b3"]["text"]
    assert exemplar["reviewed_at"] == "2026-09-23T10:00:00Z"


def test_correction_exemplar_keeps_rejected_value_as_negative_only():
    record = reviewed_record(
        position_holder="Derrida",
        metadata_field_status={
            "position_holder": {"status": "human_confirmed", "method": "human"}
        },
        metadata_evidence={
            "position_holder": {
                "block_ids": ["b3"],
                "reviewed_by": "human",
            }
        },
        llm_rejections=[
            {
                "field": "position_holder",
                "rejected_value": "Levinas",
                "chosen_value": "Derrida",
                "model": "small-model",
                "at": "2026-09-23T10:00:00Z",
            }
        ],
    )

    corrections = build_correction_exemplars(record, blocks())

    assert len(corrections) == 1
    correction = corrections[0]
    assert correction["kind"] == "correction"
    assert correction["field_value"] == "Derrida"
    assert correction["rejected_value"] == "Levinas"
    rendered = prompt_example(correction, similarity=0.83)
    assert rendered["value"] == "Derrida"
    assert rendered["rejected_value"] == "Levinas"
    assert rendered["evidence"] == blocks()["b3"]["text"]
    assert rendered["similarity"] == 0.83



def test_editorial_memory_prefers_bound_evidence_over_whole_record_excerpt():
    from app.corpus_editorial_memory import EditorialMemoryMixin

    reviewed = reviewed_record(
        text=(
            "Unrelated setup about sovereignty and law. "
            "For Levinas, responsibility precedes the freedom of the subject. "
            "Unrelated closing discussion about institutions."
        )
    )
    current = {
        "record_id": "r2",
        "record_revision": 1,
        "text": "Levinas is presented as making responsibility prior to subjective freedom.",
        "metadata_field_status": {},
    }

    class Repo:
        def load_records(self, build_id):
            assert build_id == "build-1"
            return [reviewed, current]

        def get_build(self, build_id):
            assert build_id == "build-1"
            return {
                "asset_id": "asset-1",
                "schema_id": "derrida",
                "schema_version": "v7",
            }

        def load_blocks(self, asset_id):
            assert asset_id == "asset-1"
            return list(blocks().values())

    class GlobalLearning:
        def conventions(self, *, exclude_build_id=""):
            return {}

    class Memory(EditorialMemoryMixin):
        repo = Repo()
        _global_learning = GlobalLearning()

        def _append_warning(self, build_id, message):
            raise AssertionError(f"Unexpected editorial-memory warning: {build_id}: {message}")

    memory = Memory()._editorial_memory(
        "build-1",
        current,
        exclude_record_id="r2",
    )
    example = memory["examples"]["position_holder"][0]

    assert example["evidence_bound"] is True
    assert example["record_revision"] == 4
    assert example["evidence"] == blocks()["b2"]["text"]
    assert example["excerpt"] == blocks()["b2"]["text"]
    assert "sovereignty" not in example["excerpt"]



def test_prompt_example_budget_caps_each_field_and_total_packet():
    examples = {
        "speaker": [
            {"record_id": f"s{index}", "value": "Derrida", "excerpt": "x" * 120}
            for index in range(6)
        ],
        "position_holder": [
            {"record_id": f"p{index}", "value": "Levinas", "excerpt": "y" * 120}
            for index in range(6)
        ],
        "stance": [
            {"record_id": f"t{index}", "value": "critical", "excerpt": "z" * 120}
            for index in range(6)
        ],
    }

    bounded = budget_prompt_examples(examples, token_budget=220)

    assert len(bounded.get("speaker", [])) <= 2
    assert len(bounded.get("position_holder", [])) <= 3
    assert len(bounded.get("stance", [])) <= 3
    assert prompt_example_token_estimate(bounded) <= 230


def test_prompt_example_budget_round_robins_across_fields():
    examples = {
        "speaker": [{"record_id": "s", "value": "Derrida", "excerpt": "x" * 40}],
        "position_holder": [{"record_id": "p", "value": "Levinas", "excerpt": "y" * 40}],
        "stance": [{"record_id": "t", "value": "critical", "excerpt": "z" * 40}],
    }

    bounded = budget_prompt_examples(examples, token_budget=120)

    assert set(bounded) == {"position_holder", "speaker", "stance"}



def test_editorial_memory_semantic_retrieval_uses_bound_canonical_exemplars():
    from app.corpus_editorial_memory import EditorialMemoryMixin

    reviewed = reviewed_record()
    current = {
        "record_id": "r2",
        "record_revision": 1,
        "text": "Responsibility and alterity are discussed in relation to Levinas.",
        "language": "en",
        "metadata_field_status": {},
    }

    class Repo:
        def load_records(self, build_id):
            return [reviewed, current]

        def get_build(self, build_id):
            return {
                "asset_id": "asset-1",
                "schema_id": "derrida",
                "schema_version": "v7",
            }

        def load_blocks(self, asset_id):
            return list(blocks().values())

    class GlobalLearning:
        def conventions(self, *, exclude_build_id=""):
            return {}

    class SemanticIndex:
        def __init__(self):
            self.calls = []

        def retrieve(self, **kwargs):
            self.calls.append(kwargs)
            assert kwargs["scope_id"] == "build-1"
            assert kwargs["schema_id"] == "derrida"
            assert kwargs["schema_version"] == "v7"
            assert kwargs["language"] == "en"
            assert kwargs["exclude_record_id"] == "r2"
            assert len(kwargs["exemplars"]) == 1
            exemplar = kwargs["exemplars"][0]
            assert exemplar["evidence_text"] == blocks()["b2"]["text"]
            return {
                "ok": True,
                "examples": {
                    "position_holder": [prompt_example(exemplar, similarity=0.97)]
                },
                "telemetry": {
                    "query_ms": 8,
                    "search_ms": 3,
                    "select_ms": 1,
                    "examples_considered": 1,
                    "examples_used": 1,
                    "fields_served": ["position_holder"],
                },
            }

    class Memory(EditorialMemoryMixin):
        repo = Repo()
        _global_learning = GlobalLearning()
        _progressive_metadata_index = SemanticIndex()
        _progressive_metadata_warning_builds = set()

        def _append_warning(self, build_id, message):
            raise AssertionError(f"Unexpected warning: {message}")

    manager = Memory()
    memory = manager._editorial_memory(
        "build-1",
        current,
        exclude_record_id="r2",
    )

    assert len(manager._progressive_metadata_index.calls) == 1
    example = memory["examples"]["position_holder"][0]
    assert example["evidence_bound"] is True
    assert example["similarity"] == 0.97
    assert memory["progressive_retrieval"]["query_ms"] == 8


def test_editorial_memory_can_disable_progressive_retrieval_for_ablation():
    from app.corpus_editorial_memory import EditorialMemoryMixin

    reviewed = reviewed_record()
    current = {
        "record_id": "r2",
        "text": "Levinas and responsibility.",
        "metadata_field_status": {},
    }

    class Repo:
        def load_records(self, build_id):
            return [reviewed, current]

        def get_build(self, build_id):
            return {
                "asset_id": "asset-1",
                "schema_id": "derrida",
                "schema_version": "v7",
            }

        def load_blocks(self, asset_id):
            return list(blocks().values())

    class GlobalLearning:
        def conventions(self, *, exclude_build_id=""):
            return {}

    class MustNotRun:
        def retrieve(self, **kwargs):
            raise AssertionError("semantic retrieval should be disabled")

    class Memory(EditorialMemoryMixin):
        repo = Repo()
        _global_learning = GlobalLearning()
        _progressive_metadata_index = MustNotRun()

        def _append_warning(self, build_id, message):
            raise AssertionError(f"Unexpected warning: {message}")

    memory = Memory()._editorial_memory(
        "build-1",
        current,
        exclude_record_id="r2",
        use_progressive=False,
    )

    assert memory["progressive_retrieval"] == {}
    assert memory["examples"]["position_holder"][0]["evidence_bound"] is True



def test_editorial_memory_semantic_index_can_serve_evidence_bound_quotation_field():
    from app.corpus_editorial_memory import EditorialMemoryMixin

    reviewed = reviewed_record(
        quoted_speaker=["Levinas"],
        metadata_field_status={
            "quoted_speaker": {
                "status": "human_confirmed",
                "method": "human_review_of_llm_proposal",
            }
        },
        metadata_evidence={
            "quoted_speaker": {
                "block_ids": ["b2"],
                "confidence": 0.93,
                "reason": "The quoted position is explicitly attributed to Levinas.",
            }
        },
    )
    current = {
        "record_id": "r2",
        "record_revision": 1,
        "language": "en",
        "text": "The passage quotes Levinas on responsibility.",
        "metadata_field_status": {},
    }

    class Repo:
        def load_records(self, build_id):
            return [reviewed, current]

        def get_build(self, build_id):
            return {
                "asset_id": "asset-1",
                "schema_id": "derrida",
                "metadata_schema_version": "1.0.0",
            }

        def load_blocks(self, asset_id):
            return list(blocks().values())

    class GlobalLearning:
        def conventions(self, *, exclude_build_id=""):
            return {}

    class SemanticIndex:
        def retrieve(self, **kwargs):
            assert "quoted_speaker" in kwargs["fields"]
            exemplar = next(
                item
                for item in kwargs["exemplars"]
                if item["field_name"] == "quoted_speaker"
            )
            return {
                "ok": True,
                "examples": {
                    "quoted_speaker": [prompt_example(exemplar, similarity=0.91)]
                },
                "telemetry": {
                    "query_ms": 3,
                    "search_ms": 2,
                    "select_ms": 1,
                    "examples_considered": 1,
                    "examples_used": 1,
                },
            }

    class Memory(EditorialMemoryMixin):
        repo = Repo()
        _global_learning = GlobalLearning()
        _progressive_metadata_index = SemanticIndex()

        def _append_warning(self, build_id, message):
            raise AssertionError(f"Unexpected editorial-memory warning: {message}")

    memory = Memory()._editorial_memory(
        "build-1",
        current,
        exclude_record_id="r2",
    )

    example = memory["examples"]["quoted_speaker"][0]
    assert example["evidence_bound"] is True
    assert example["value"] == ["Levinas"]
    assert example["evidence"] == blocks()["b2"]["text"]


def test_metadata_prompts_receive_only_examples_for_their_family(monkeypatch):
    import app.corpus_metadata_enrichment_execution as execution
    from app.corpus_metadata_enrichment_execution import MetadataEnrichmentExecutionMixin
    from app.corpus_models import CORPUS_PROFILES, PROFILE_VERSION
    from app.metadata_schema import default_schema

    monkeypatch.setattr(execution, "adjudication_suggestions", lambda **kwargs: {})

    class Harness(MetadataEnrichmentExecutionMixin):
        pass

    record = {
        "record_id": "r-current",
        "text": 'Derrida writes "responsibility precedes freedom."',
        "source_block_ids": ["b1"],
        "metadata_field_status": {},
    }
    examples = {
        "speaker": [
            {
                "record_id": "r-speaker",
                "value": "Derrida",
                "excerpt": "SPEAKER_ONLY_PROGRESSIVE_MARKER",
            }
        ],
        "quoted_speaker": [
            {
                "record_id": "r-quote",
                "value": ["Levinas"],
                "excerpt": "QUOTATION_ONLY_PROGRESSIVE_MARKER",
            }
        ],
    }

    tasks, _, _ = Harness()._prepare_metadata_tasks(
        record,
        {},
        {"enrichment_mode": "deep", "semantic_indexing": True},
        dict(CORPUS_PROFILES[PROFILE_VERSION]),
        {},
        examples,
        "",
        "",
        None,
        schema=default_schema(),
    )
    prompts = {name: prompt for name, prompt, *_ in tasks}

    assert "SPEAKER_ONLY_PROGRESSIVE_MARKER" in prompts["discourse"]
    assert "QUOTATION_ONLY_PROGRESSIVE_MARKER" not in prompts["discourse"]
    assert "QUOTATION_ONLY_PROGRESSIVE_MARKER" in prompts["quotation"]
    assert "SPEAKER_ONLY_PROGRESSIVE_MARKER" not in prompts["quotation"]
