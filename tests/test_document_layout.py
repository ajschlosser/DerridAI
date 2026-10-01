"""Document layout derivation for two-up and bilingual scans.

Why: many scholarly PDFs place two book pages on one sheet, may put the main text
after front matter, and may print two language versions side by side. Region types,
printed page labels, and language threads must be derived from a few reviewer
settings so citations point to the right printed page.
How: builds a four-sheet, eight-block asset in a temporary repository and applies
update_document_layout.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

try:
    import chromadb  # type: ignore  # noqa
except ModuleNotFoundError:
    sys.modules["chromadb"] = types.SimpleNamespace()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from app import corpus_builder as cb


def test_document_layout_derives_two_up_pages_regions_and_threads(tmp_path: Path):
    """Layout settings produce region types, printed page labels, and language threads.

    Setup: 4 sheets, each with a left block (x 50-450) and a right block (x 550-950).
    Layout: two-up, main text starts on sheet 2 in the right slot as printed page 1,
    bibliography starts at sheet 4, left = thread A (fr_fr), right = thread B (en_us).
    Checks: sheet 1 is front_matter, sheet 2 main_text, sheet 4 bibliography. On sheet
    2 the left half has no printed page (it precedes the main-text start) and the right
    half is "1"; the next sheet's left half is "2". Blocks are tagged thread_a/thread_b
    with their languages.
    Why: a wrong printed-page label becomes a wrong page number in a citation.
    """
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset = {
        "asset_id": "layout-a", "sha256": "x", "filename": "book.pdf",
        "page_count": 4, "block_count": 8, "ocr_pages": 0, "warnings": [], "metadata": {},
        "pages": [{"pdf_page": i, "width": 1000.0, "height": 1400.0} for i in range(1, 5)],
    }
    cb._json_write(repo.asset_meta_path("layout-a"), asset)
    blocks = []
    for page in range(1, 5):
        blocks += [
            {"block_id": f"p{page}l", "page": page, "bbox": [50, 100, 450, 300], "type": "paragraph", "text": "left", "extraction_method": "native", "confidence": 1.0},
            {"block_id": f"p{page}r", "page": page, "bbox": [550, 100, 950, 300], "type": "paragraph", "text": "right", "extraction_method": "native", "confidence": 1.0},
        ]
    with repo.asset_blocks_path("layout-a").open("w", encoding="utf-8") as handle:
        for block in blocks:
            handle.write(json.dumps(block) + "\n")
    updated = repo.update_document_layout("layout-a", {
        "page_layout": "two_up", "reading_order": "left_to_right",
        "main_text_pdf_start": 2, "main_text_printed_start": 1, "main_text_slot": "right",
        "bibliography_pdf_start": 4, "thread_mode": "left_right",
        "thread_a_language": "fr_fr", "thread_b_language": "en_us",
    })
    assert updated["pages"][0]["deterministic_region_type"] == "front_matter"
    assert updated["pages"][1]["deterministic_region_type"] == "main_text"
    assert updated["pages"][3]["deterministic_region_type"] == "bibliography"
    # A right-hand main-text start means the preceding left half is not assigned a later folio.
    assert updated["pages"][1]["logical_pages"][0]["printed_page_label"] is None
    assert updated["pages"][1]["logical_pages"][1]["printed_page_label"] == "1"
    derived = {b["block_id"]: b for b in repo.load_blocks("layout-a")}
    assert derived["p2r"]["printed_page_label"] == "1"
    assert derived["p3l"]["printed_page_label"] == "2"
    assert derived["p2l"]["document_thread"] == "thread_a"
    assert derived["p2r"]["document_thread"] == "thread_b"
    assert derived["p2l"]["thread_language"] == "fr_fr"
    assert derived["p2r"]["thread_language"] == "en_us"


def _write_layout_asset(tmp_path: Path, asset_id: str = "layout-regions") -> cb.PdfCorpusRepository:
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset = {
        "asset_id": asset_id, "sha256": "x", "filename": "gloss.pdf",
        "page_count": 2, "block_count": 4, "ocr_pages": 0, "warnings": [], "metadata": {},
        "pages": [{"pdf_page": i, "width": 1000.0, "height": 1400.0} for i in range(1, 3)],
    }
    cb._json_write(repo.asset_meta_path(asset_id), asset)
    blocks = []
    for page in range(1, 3):
        blocks += [
            {"block_id": f"p{page}m", "page": page, "bbox": [40, 80, 140, 500], "type": "paragraph", "text": "gloss", "extraction_method": "native", "confidence": 1.0},
            {"block_id": f"p{page}b", "page": page, "bbox": [280, 80, 900, 500], "type": "paragraph", "text": "body", "extraction_method": "native", "confidence": 1.0},
        ]
    with repo.asset_blocks_path(asset_id).open("w", encoding="utf-8") as handle:
        for block in blocks:
            handle.write(json.dumps(block) + "\n")
    return repo


def test_margin_region_is_a_separate_thread_and_does_not_break_the_main_text(tmp_path: Path):
    """A repeating margin rectangle keeps the gloss out of the main reading order.

    The left band is notes on thread B. The body stays thread A and is emitted
    first, for every page, before the margin sequence. A polygon is refused.
    """
    from app.corpus_segmentation import _deterministic_boundary_candidates, _candidate_route
    from app.document_layout_regions import reading_sequence

    repo = _write_layout_asset(tmp_path)
    updated = repo.update_document_layout("layout-regions", {
        "page_layout": "single",
        "reading_order": "left_to_right",
        "main_text_pdf_start": 1,
        "main_text_printed_start": 1,
        "thread_mode": "continuous",
        "layout_regions": [
            {"id": "main", "role": "main", "thread": "thread_a", "flow": "with_main", "x0": 0, "y0": 0, "x1": 1, "y1": 1, "applies_to": "all"},
            {"id": "margin", "role": "margin_apparatus", "thread": "thread_b", "language": "fr_fr", "flow": "separate", "x0": 0, "y0": 0.04, "x1": 0.2, "y1": 0.96, "applies_to": "all"},
        ],
    })
    derived = {block["block_id"]: block for block in repo.load_blocks("layout-regions")}
    assert derived["p1m"]["document_thread"] == "thread_b"
    assert derived["p1m"]["deterministic_region_type"] == "notes"
    assert derived["p1m"]["thread_language"] == "fr_fr"
    assert derived["p1m"]["layout_flow"] == "separate"
    assert derived["p1b"]["document_thread"] == "thread_a"
    assert derived["p1b"]["deterministic_region_type"] == "main_text"
    assert derived["p1b"]["layout_flow"] == "with_main"
    assert "thread_b" in updated["pages"][0]["thread_ids"]
    ordered = reading_sequence(repo.load_blocks("layout-regions"), ["main", "margin"])
    assert [block["block_id"] for block in ordered] == ["p1b", "p2b", "p1m", "p2m"]
    assert len(ordered) == 4
    candidates = _deterministic_boundary_candidates(ordered, {})
    change = next(item for item in candidates if "layout_region_change" in item["signals"])
    assert change["after_block_id"] == "p2b"
    assert _candidate_route(change, {}) == "split"
    try:
        repo.update_document_layout("layout-regions", {
            "page_layout": "single",
            "layout_regions": [{"id": "bad", "role": "infobox", "polygon": [[0, 0], [1, 0], [1, 1]]}],
        })
    except ValueError as exc:
        assert "rectangle" in str(exc).lower()
    else:
        raise AssertionError("a polygon region should be rejected")


def test_block_quote_region_stays_inside_the_main_thread():
    """An inset quotation is marked, but it is not pulled out of the argument."""
    from app.document_layout_regions import apply_layout_regions

    blocks = [{
        "block_id": "q", "page": 1, "bbox": [200, 400, 800, 700], "type": "paragraph",
        "text": "quoted", "document_thread": "thread_a", "deterministic_region_type": "main_text",
    }]
    apply_layout_regions(blocks, [{"pdf_page": 1, "width": 1000.0, "height": 1400.0}], [
        {"id": "main", "role": "main", "thread": "thread_a", "flow": "with_main", "language": None, "x0": 0, "y0": 0, "x1": 1, "y1": 1, "applies_to": "all", "page": None, "page_start": None, "page_end": None, "label": None},
        {"id": "quote", "role": "block_quote", "thread": "thread_b", "flow": "with_main", "language": None, "x0": 0.14, "y0": 0.28, "x1": 0.86, "y1": 0.55, "applies_to": "all", "page": None, "page_start": None, "page_end": None, "label": None},
    ])
    assert blocks[0]["layout_region_role"] == "block_quote"
    assert blocks[0]["layout_flow"] == "with_main"
    assert blocks[0]["document_thread"] == "thread_a"
    assert blocks[0]["deterministic_region_type"] == "main_text"


def test_layout_regions_do_not_merge_across_threads():
    """Line joining stops when the reviewer assigned the lines to different threads."""
    atoms = cb._semantic_atoms([
        {"block_id": "b1", "page": 1, "type": "body", "text": "A short visual line", "document_thread": "thread_a", "layout_region_id": "main", "layout_flow": "with_main"},
        {"block_id": "b2", "page": 1, "type": "body", "text": "continues the same sentence.", "document_thread": "thread_b", "layout_region_id": "margin", "layout_flow": "separate"},
    ])
    assert [atom["block_id"] for atom in atoms] == ["b1", "b2"]






