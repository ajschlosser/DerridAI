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


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")








def test_document_layout_derives_two_up_pages_regions_and_threads(tmp_path: Path):
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






