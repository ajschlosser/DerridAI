from app.corpus_builder import PdfCorpusBuildManager as M


def rec(pages):
    return {"record_id": "r", "pdf_pages": pages, "text": "x", "metadata_field_status": {}}


def test_record_across_start_page_is_flagged_for_the_reviewer():
    record = rec([5, 6])
    M._apply_manifest_metadata(record, {"main_text_start_page": 6})
    assert record["needs_review"] is True
    assert any(i["code"] == "main_text_start_straddle" for i in record["boundary_quality_issues"])
    assert "split" in record["review_reason"]


def test_flag_clears_when_start_page_moves_and_no_duplicates():
    record = rec([5, 6])
    M._apply_manifest_metadata(record, {"main_text_start_page": 6})
    M._apply_manifest_metadata(record, {"main_text_start_page": 6})
    assert sum(i["code"] == "main_text_start_straddle" for i in record["boundary_quality_issues"]) == 1
    M._apply_manifest_metadata(record, {"main_text_start_page": 5})
    assert not record["boundary_quality_issues"]


def test_human_chosen_region_is_not_flagged():
    record = rec([5, 6])
    record["metadata_field_status"]["region_type"] = {"status": "human_confirmed"}
    M._apply_manifest_metadata(record, {"main_text_start_page": 6})
    assert not record.get("boundary_quality_issues")
