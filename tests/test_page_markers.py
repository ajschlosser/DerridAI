# Copyright 2026 Aaron John Schlosser, PhD.
"""Deterministic page-number detection in plain-text sources."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import page_markers as pm  # noqa: E402
from app import source_text as st  # noqa: E402

PAGE = ("The philosophical text continues at length across this page, developing its argument. " * 6).strip()


def doc(markers, *, before=True):
    """Pages of prose separated by marker lines. ``before`` puts each marker ahead of its page."""
    parts = []
    for marker in markers:
        parts += ([marker, PAGE] if before else [PAGE, marker])
    return "\n\n".join(parts)


@pytest.mark.parametrize("fmt", ["[{n}]", "{{{n}}}", "({n})", "<{n}>", "[p. {n}]", "[Page {n}]", "Page {n}.", "p. {n}", "- {n} -", "— {n} —", "Page {n} of 300", "{n} / 300"])
def test_common_marker_styles_are_detected(fmt):
    text = doc([fmt.format(n=n) for n in range(30, 36)])
    detection = pm.detect(text)
    assert detection.status == "detected", fmt
    assert [m.value for m in detection.markers] == list(range(30, 36))
    assert detection.confidence > 0.7


def test_bare_footer_numbers_are_detected_and_treated_as_footers():
    text = doc([str(n) for n in range(30, 40)], before=False)
    detection = pm.detect(text)
    assert detection.status == "detected" and detection.pattern == "bare"
    assert detection.convention == "end"


def test_spelled_out_page_numbers():
    words = ["thirty-one", "thirty-two", "thirty-three", "thirty-four"]
    detection = pm.detect(doc([f"Page {w}." for w in words]))
    assert detection.status == "detected" and [m.value for m in detection.markers] == [31, 32, 33, 34]


def test_roman_numeral_front_matter():
    detection = pm.detect(doc([f"[{r}]" for r in ["iv", "v", "vi", "vii"]]))
    assert detection.status == "detected" and [m.value for m in detection.markers] == [4, 5, 6, 7]


def test_running_header_folios_beside_a_repeated_title():
    lines = []
    for n in range(40, 46):
        lines += [f"{n}    ON GRAMMATOLOGY", PAGE]
    detection = pm.detect("\n\n".join(lines))
    assert detection.status == "detected" and detection.pattern == "header"


def test_inline_page_tags_inside_paragraphs():
    text = f"{PAGE} [Page 12] {PAGE}\n\n{PAGE} [Page 13] {PAGE}\n\n{PAGE} [Page 14] {PAGE}"
    detection = pm.detect(text)
    assert detection.status == "detected" and [m.value for m in detection.markers] == [12, 13, 14]


@pytest.mark.parametrize("text", [
    "1\n2\n3\n4\n5\n6",                                   # a numbered list
    "\n\n".join([PAGE, "1968", PAGE, PAGE]),              # a lone year
    "\n\n".join(["1", PAGE, "2", PAGE, "3", PAGE]),       # three chapter numbers: not enough to be pages
    "\n\n".join([PAGE, "[12]", PAGE, "[3]", PAGE, "[41]", PAGE]),  # no sequence
    "",
])
def test_things_that_are_not_page_numbers_are_left_alone(text):
    assert pm.detect(text).status == "not_found"


def test_the_obvious_bracketed_txt_case():
    text = "\n\n".join(["Preface text. " * 20, "[31]", PAGE, "[32]", PAGE, "[33]", PAGE])
    blocks, pages = st.prose_to_blocks(text, extraction_method="text", detection_out=(summary := {}))
    assert summary["status"] == "detected" and summary["pattern"] == "bracket"
    labels = [b["printed_page_label"] for b in blocks if b["type"] == "paragraph"]
    assert labels == ["30", "31", "32", "33"]  # front text is inferred, not invented as 31
    assert [b["printed_page_label_source"] for b in blocks if b["type"] == "paragraph"][0] == "inferred_from_folios"
    assert all(b.get("excluded_reason") == "page_number" for b in blocks if b["type"] == "header_footer")
    assert len(pages) == 4


def test_detection_conserves_text():
    text = "\n\n".join(["Intro. " * 30, "[1]", PAGE, "[2]", PAGE, "[3]", PAGE])
    blocks, _ = st.prose_to_blocks(text, extraction_method="text")
    rebuilt = "\n\n".join(b["text"] for b in blocks)
    assert rebuilt.split() == text.split()


def test_detection_can_be_turned_off_and_falls_back_to_synthetic_pages():
    text = doc([f"[{n}]" for n in range(1, 6)])
    blocks, _ = st.prose_to_blocks(text, extraction_method="text", detect_pages=False, detection_out=(summary := {}))
    assert summary["status"] == "disabled"
    assert {b["printed_page_label_source"] for b in blocks} == {"synthetic_span"}


def test_not_found_keeps_the_previous_synthetic_pages():
    blocks, _ = st.prose_to_blocks("Just prose. " * 50, extraction_method="text", detection_out=(summary := {}))
    assert summary["status"] == "not_found"
    assert blocks and blocks[0]["printed_page_label_source"] == "synthetic_span"


def test_number_words_and_numerals():
    assert pm.words_to_int("thirty-two") == 32
    assert pm.words_to_int("Ninety nine") == 99
    assert pm.words_to_int("one hundred and five") == 105
    assert pm.words_to_int("quatre-vingt-dix-sept") == 97
    assert pm.words_to_int("banana") is None
    assert pm.roman_to_int("xiv") == 14 and pm.roman_to_int("mix") is None or pm.roman_to_int("mix") == 1009


def test_document_from_text_reports_the_detection_and_excluded_markers():
    text = "\n\n".join(["Intro. " * 30, "[1]", PAGE, "[2]", PAGE, "[3]", PAGE])
    result = st.document_from_text(text, filename="a.txt", extraction_method="text", media_kind="text")
    assert result["page_number_detection"]["status"] == "detected"
    assert result["excluded_block_count"] == 3
    assert result["included_block_count"] == result["block_count"] - 3


def test_html_page_anchors_become_markers():
    body = "".join(f'<a name="Page_{n}" id="Page_{n}"></a><p>{PAGE}</p>' for n in range(20, 25))
    text, _ = st.html_to_text(f"<html><body>{body}</body></html>")
    detection = pm.detect(text)
    assert detection.status == "detected" and [m.value for m in detection.markers] == [20, 21, 22, 23, 24]


def test_saved_text_asset_carries_detection_and_records_get_printed_pages(tmp_path):
    from app import corpus_builder as cb
    from app.corpus_segmentation import _construct_records

    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    text = "\n\n".join(["Preface. " * 30, "[31]", PAGE, "[32]", PAGE, "[33]", PAGE])
    asset = repo.save_asset(text.encode(), filename="essay.txt")
    assert asset["page_number_detection"]["status"] == "detected"
    blocks = [b for b in repo.load_blocks(asset["asset_id"]) if not b.get("excluded_reason")]
    records = _construct_records(asset, blocks, [{"after_block_id": blocks[1]["block_id"]}])
    assert (records[0]["page_start"], records[0]["page_end"]) == (30, 31)  # 30 is inferred from the first marker
    assert records[1]["page_start"] == 32


def test_turning_detection_off_yields_a_separate_asset(tmp_path):
    from app import corpus_builder as cb

    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    text = doc([f"[{n}]" for n in range(1, 6)])
    on = repo.save_asset(text.encode(), filename="a.txt")
    off = repo.save_asset(text.encode(), filename="a.txt", detect_page_numbers=False)
    assert on["asset_id"] != off["asset_id"]
    assert off["page_number_detection"]["status"] == "disabled"
