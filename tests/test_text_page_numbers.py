# Copyright 2026 Aaron John Schlosser, PhD.
"""Page numbers for text that has no PDF pages.

File and provider conventions come first. A word-count estimate is only the last resort,
and that estimate can be one record per page.
"""

import io
import sys
import zipfile
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import source_text as st  # noqa: E402
from app import source_wikisource as ws  # noqa: E402
from app.corpus_segmentation import _construct_records, page_record_boundaries  # noqa: E402
from app.source_provider import ProviderPolicy  # noqa: E402

PARA = ("The argument continues across this estimated page. " * 20).strip()


def test_word_count_groups_whole_paragraphs_and_can_be_retargeted(tmp_path):
    from app import corpus_builder as cb

    paragraphs = ["alpha " * 80] * 4  # 80 words each
    text = "\n\n".join(paragraph.strip() for paragraph in paragraphs)
    result = st.document_from_text(text, filename="notes.txt", extraction_method="text", media_kind="text")
    assert result["page_number_detection"]["status"] == "estimated"
    assert result["page_estimate"]["words_per_page"] == 300
    assert result["page_estimate"]["one_record_per_page"] is True
    # 80+80+80 = 240, the fourth paragraph starts the next page.
    assert result["page_count"] == 2
    assert " ".join(word for block in result["blocks"] for word in block["text"].split()) == " ".join(text.split())

    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset = repo.save_asset(text.encode(), filename="notes.txt")
    revised = repo.apply_page_estimate(asset["asset_id"], words_per_page=80, one_record_per_page=True)
    assert revised["page_count"] == 4
    assert revised["page_number_detection"]["confirmed"] is True
    blocks = [block for block in repo.load_blocks(revised["asset_id"]) if not block.get("excluded_reason")]
    boundaries = page_record_boundaries(blocks)
    records = _construct_records(revised, blocks, boundaries)
    assert len(records) == 4
    assert [record["page_start"] for record in records] == [1, 2, 3, 4]

    kept = repo.apply_page_estimate(asset["asset_id"], words_per_page=80, one_record_per_page=False)
    assert kept["page_estimate"]["one_record_per_page"] is False


def test_form_feeds_and_word_documents_supply_page_numbers():
    blocks, pages = st.prose_to_blocks("First page of the essay.\fSecond page of the essay.", extraction_method="text")
    assert pages[0]["printed_page_label_source"] == "form_feed"
    assert [page["printed_page_label"] for page in pages] == ["1", "2"]
    assert [block["text"] for block in blocks] == ["First page of the essay.", "Second page of the essay."]

    document = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:r><w:t>Opening page.</w:t></w:r></w:p>
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
<w:p><w:r><w:t>Following page.</w:t></w:r></w:p>
<w:sectPr><w:pgNumType w:start="14"/></w:sectPr>
</w:body></w:document>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as package:
        package.writestr("word/document.xml", document)
    text, embedded = st.docx_to_text(buf.getvalue())
    result = st.document_from_text(text, filename="essay.docx", extraction_method="docx", embedded=embedded, media_kind="docx")
    assert result["page_number_detection"]["pattern"] == "docx_page_break"
    assert [page["printed_page_label"] for page in result["pages"]] == ["14", "15"]


def test_rtf_page_breaks_keep_the_declared_start():
    data = r"{\rtf1\ansi\pgnstart40 First page of the letter.\page Second page of the letter.}".encode("latin-1")
    text, embedded = st.rtf_to_text(data)
    result = st.document_from_text(text, filename="letter.rtf", extraction_method="rtf", embedded=embedded, media_kind="rtf")
    assert result["page_number_detection"]["pattern"] == "rtf_page_break"
    assert [page["printed_page_label"] for page in result["pages"]] == ["40", "41"]
    assert "First page" in result["blocks"][0]["text"] and "Second page" in result["blocks"][-1]["text"]


def test_wikisource_and_gutenberg_page_markup_becomes_printed_pages():
    page = ("The transcribed scan line continues here. " * 12).strip()
    html = "".join(
        f'<span class="pagenum ws-noexport" id="{n}">{n}</span><p>{page}</p>' for n in range(20, 24)
    )
    html += "<!-- Page 24 --><p>" + page + "</p>"
    text, _ = st.html_to_text(f"<html><body>{html}</body></html>")
    detection_blocks, _ = st.prose_to_blocks(text, extraction_method="html", detection_out=(summary := {}))
    assert summary["status"] == "detected"
    labels = [block["printed_page_label"] for block in detection_blocks if block["type"] == "paragraph"]
    assert labels[:4] == ["20", "21", "22", "23"]
    assert "20" not in " ".join(block["text"] for block in detection_blocks if block["type"] == "paragraph")


def test_wikisource_scan_targets_are_saved_as_jpeg_pages(tmp_path):
    titles = ["Page:Grammatology.djvu/2", "Page:Grammatology.djvu/2", "Page:Grammatology.djvu/3"]
    targets = ws.scan_targets_from_titles(titles)
    assert targets == [{"file": "Grammatology.djvu", "djvu_page": 2}, {"file": "Grammatology.djvu", "djvu_page": 3}]
    html = '<span class="pagenum" data-page-name="Page:Grammatology.djvu/2">2</span>'
    assert ws.scan_targets_from_html(html)[0]["djvu_page"] == 2

    class Http:
        policy = ProviderPolicy(hosts=("upload.wikimedia.org",), min_interval_s=0, max_concurrent=1)

        def get_json(self, url, params):
            assert "page2-640px" in params["iiurlparam"] or "page3-640px" in params["iiurlparam"]
            return {"query": {"pages": [{"imageinfo": [{"thumburl": "https://upload.wikimedia.org/scan.jpg"}]}]}}

        def get(self, url, max_bytes=None):
            return httpx.Response(200, content=b"\xff\xd8\xff\xd9")

    scans, warnings = ws.fetch_wikisource_scans(Http(), "https://en.wikisource.org", targets)
    assert warnings == [] and len(scans) == 2 and scans[0]["data"].startswith(b"\xff\xd8")

    from app import corpus_builder as cb

    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset = repo.save_asset(b"A short note without page marks.\n\nAnother paragraph.", filename="work.html")
    stored = repo.store_source_scans(asset["asset_id"], scans, source="wikisource_djvu")
    assert stored["scans"]["count"] == 2
    path = repo.scan_image_path(stored["asset_id"], 1)
    assert path.read_bytes().startswith(b"\xff\xd8")


def test_a_word_estimate_cannot_replace_printed_page_numbers(tmp_path):
    from app import corpus_builder as cb

    text = "\n\n".join(["Preface. " * 30, "[31]", PARA, "[32]", PARA, "[33]", PARA])
    repo = cb.PdfCorpusRepository(tmp_path / "repo")
    asset = repo.save_asset(text.encode(), filename="essay.txt")
    assert asset["page_number_detection"]["status"] == "detected"
    with pytest.raises(ValueError, match="printed page numbers"):
        repo.apply_page_estimate(asset["asset_id"], words_per_page=100, one_record_per_page=True)
