from app.corpus_segmentation import _apply_manifest_metadata, _construct_records
from app.field_assertions import (
    create_human_assertion,
    current_assertion_by_name,
    project_record_assertions,
)


def rec(pages):
    return {"record_id": "r", "pdf_pages": pages, "text": "x", "metadata_field_status": {}}


def test_record_across_start_page_is_flagged_for_the_reviewer():
    record = rec([5, 6])
    _apply_manifest_metadata(record, {"main_text_start_page": 6})
    assert record["needs_review"] is True
    assert any(i["code"] == "main_text_start_straddle" for i in record["boundary_quality_issues"])
    assert "split" in record["review_reason"]


def test_flag_clears_when_start_page_moves_and_no_duplicates():
    record = rec([5, 6])
    _apply_manifest_metadata(record, {"main_text_start_page": 6})
    _apply_manifest_metadata(record, {"main_text_start_page": 6})
    assert sum(i["code"] == "main_text_start_straddle" for i in record["boundary_quality_issues"]) == 1
    _apply_manifest_metadata(record, {"main_text_start_page": 5})
    assert not record["boundary_quality_issues"]


def test_human_chosen_region_is_not_flagged():
    record = rec([5, 6])
    record["metadata_field_status"]["region_type"] = {"status": "human_confirmed"}
    _apply_manifest_metadata(record, {"main_text_start_page": 6})
    assert not record.get("boundary_quality_issues")


def test_manifest_page_range_creates_canonical_structural_assertions():
    record = rec([12])
    _apply_manifest_metadata(record, {"main_text_start_page": 10, "main_text_end_page": 20})

    primary = current_assertion_by_name(record, "primary_text")
    region = current_assertion_by_name(record, "region_type")
    assert primary is not None and primary.derivation_method == "deterministic"
    assert primary.method == "manifest_page_range"
    assert primary.value is True
    assert region is not None and region.value == "main_text"


def test_human_structural_assertion_survives_manifest_reclassification():
    record = rec([5, 6])
    create_human_assertion(record, "region_type", "main_text", reason="Reviewer chose the region.")
    project_record_assertions(record)

    # A misleading compatibility token must not permit manifest logic to replace
    # the canonical human decision.
    record["metadata_field_status"]["region_type"]["status"] = "model_inferred"
    _apply_manifest_metadata(record, {"main_text_start_page": 6})

    region = current_assertion_by_name(record, "region_type")
    assert region is not None and region.authority_status == "human_confirmed"
    assert record["region_type"] == "main_text"
    assert not record.get("boundary_quality_issues")


def test_record_construction_creates_assertions_not_only_status_tokens():
    records = _construct_records(
        {"asset_id": "asset-1", "filename": "book.pdf", "media_kind": "pdf"},
        [{
            "block_id": "b1",
            "page": 1,
            "text": "Derrida: Hospitality remains conditional.",
            "type": "paragraph",
            "deterministic_region_type": "main_text",
            "speaker": "Derrida",
            "printed_page_label": "1",
            "extraction_method": "native",
            "confidence": 0.99,
        }],
        [],
    )

    assert len(records) == 1
    record = records[0]
    region = current_assertion_by_name(record, "region_type")
    primary = current_assertion_by_name(record, "primary_text")
    speaker = current_assertion_by_name(record, "speaker")
    assert region is not None and region.method == "human_document_layout"
    assert primary is not None and primary.derivation_method == "deterministic"
    assert speaker is not None and speaker.method == "source_span_speaker"
    assert record["metadata_field_status"]["speaker"]["assertion_id"] == speaker.assertion_id
