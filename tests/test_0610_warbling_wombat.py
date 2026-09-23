from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape
import sys

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app import corpus_builder as cb
from app import corpus_segmentation as segmentation
from app import source_gutenberg as gutenberg
from app import source_media as sm
from app.locales.en_us import EN_US
from app.locales.fr_ca import FR_CA


def minimal_docx(title: str, author: str, paragraphs: list[str]) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{escape(paragraph)}</w:t></w:r></w:p>" for paragraph in paragraphs)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>{escape(title)}</dc:title><dc:creator>{escape(author)}</dc:creator></cp:coreProperties>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        package.writestr("word/document.xml", document)
        package.writestr("docProps/core.xml", core)
    return buffer.getvalue()


def test_locale_keys_for_generic_sources_match():
    assert set(EN_US) == set(FR_CA)
    for key in (
        "pdf_corpus.source_illegibility",
        "pdf_corpus.gutenberg_search",
        "pdf_corpus.deterministic_check",
        "pdf_corpus.source_ingested_checked",
    ):
        assert key in EN_US and key in FR_CA


def test_text_load_runs_deterministic_metadata_immediately(tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path)
    source = (
        "Title: Of Hospitality\n"
        "Author: Jacques Derrida\n\n"
        "The law of hospitality remains unconditional.\n"
    ).encode()
    asset = repo.save_asset(source, filename="hospitality.txt")
    assert asset["media_kind"] == "text"
    assert asset["deterministic_checked_at"]
    assert asset["initial_metadata"]["title"] == "Of Hospitality"
    assert asset["initial_metadata"]["document_author"] == "Jacques Derrida"
    assert asset["source_quality"]["valid_for_enrichment"] is True
    assert asset["block_count"] >= 1


def test_word_rtf_and_html_metadata(tmp_path: Path):
    repo = cb.PdfCorpusRepository(tmp_path)
    docx = repo.save_asset(
        minimal_docx("Of Hospitality", "Jacques Derrida", ["The threshold is not a simple door."]),
        filename="hospitality.docx",
    )
    assert docx["initial_metadata"]["document_author"] == "Jacques Derrida"
    assert docx["initial_metadata"]["title"] == "Of Hospitality"
    assert docx["media_kind"] == "docx"

    rtf = rb"{\rtf1\ansi{\title Of Hospitality}{\author Jacques Derrida}\par The law of hospitality remains unconditional.}"
    rich = repo.save_asset(rtf, filename="hospitality.rtf")
    assert rich["media_kind"] == "rtf"
    assert rich["initial_metadata"]["document_author"] == "Jacques Derrida"

    html = (
        "<html><head><title>Of Hospitality</title>"
        '<meta name="author" content="Jacques Derrida"></head>'
        "<body><p>The threshold remains open.</p></body></html>"
    ).encode()
    page = repo.save_asset(html, filename="hospitality.html", content_type="text/html")
    assert page["media_kind"] == "html"
    assert page["initial_metadata"]["document_author"] == "Jacques Derrida"
    assert page["initial_metadata"]["title"] == "Of Hospitality"


def test_dialogue_speakers_and_record_inheritance():
    blocks, _pages = sm.prose_to_blocks(
        "ADA: The gift exceeds the economy.\n\nADA: It does so without return.",
        extraction_method="text",
    )
    assert [block["speaker"] for block in blocks] == ["ADA", "ADA"]
    records = segmentation._construct_records(
        {"filename": "seminar.txt", "asset_id": "asset"},
        blocks,
        [],
    )
    assert records[0]["speaker"] == "ADA"
    assert records[0]["metadata_field_status"]["speaker"]["method"] == "source_span_speaker"
    segmentation._apply_manifest_metadata(records[0], {"speaker": "Not Ada", "title": "Seminar"})
    assert records[0]["speaker"] == "ADA"
    assert records[0]["document_title"] == "Seminar"


def test_whisper_spans_use_whisperx_speakers_after_full_transcript():
    transcript = {
        "text": "Hello there. And good evening.",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "Hello there.", "avg_logprob": -0.2},
            {"start": 2.2, "end": 4.4, "text": "And good evening.", "avg_logprob": -0.2},
        ],
    }
    turns = [
        {"start": 0.0, "end": 2.1, "speaker": "SPEAKER_00"},
        {"start": 2.1, "end": 5.0, "speaker": "SPEAKER_01"},
    ]
    blocks = sm.spans_from_transcript(transcript, turns)
    assert [block["speaker"] for block in blocks] == ["SPEAKER_00", "SPEAKER_01"]
    assert blocks[0]["extraction_method"] == "whisper"
    meta = sm.infer_initial_metadata(transcript["text"], blocks=blocks)
    assert meta["speakers"] == ["SPEAKER_00", "SPEAKER_01"]
    assert "speaker" not in meta


def test_high_confidence_ingest_metadata_overrides_blank_manifest_fields():
    result = sm.apply_deterministic_ingest_metadata(
        {"title": None, "document_author": "Catalog Guess"},
        {"deterministic_checked_at": "t", "initial_metadata": {
            "title": "Of Hospitality",
            "document_author": "Jacques Derrida",
            "field_provenance": {
                "title": {"method": "labeled_line", "confidence": 0.9},
                "document_author": {"method": "labeled_line", "confidence": 0.9},
            },
        }},
    )
    assert result["title"] == "Of Hospitality"
    assert result["document_author"] == "Jacques Derrida"


def test_gutenberg_search_and_import(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(gutenberg, "_pygutenberg_client", lambda: object())
    monkeypatch.setattr(gutenberg, "_search_with_client", lambda client, query: [{
        "id": 1342, "title": "Pride and Prejudice", "authors": [{"name": "Austen, Jane"}], "languages": ["en"],
    }])
    hits = sm.search_project_gutenberg("austen")
    assert hits[0]["etext_id"] == 1342
    assert hits[0]["author"] == "Jane Austen"

    monkeypatch.setattr(sm, "load_gutenberg_etext", lambda etext_id: (
        "It is a truth universally acknowledged.\n",
        {"title": "Pride and Prejudice", "document_author": "Jane Austen", "language": "en", "gutenberg_id": 1342, "publisher": "Project Gutenberg", "document_type": "book"},
    ))
    plain, catalog = sm.load_gutenberg_etext(1342)
    asset = cb.PdfCorpusRepository(tmp_path).save_asset(
        plain.encode(), filename="Pride and Prejudice.txt", content_type="text/plain", catalog_metadata=catalog,
        source_url="https://www.gutenberg.org/ebooks/1342",
    )
    assert asset["media_kind"] == "gutenberg"
    assert asset["initial_metadata"]["document_author"] == "Jane Austen"
    assert asset["initial_metadata"]["title"] == "Pride and Prejudice"
    assert asset["deterministic_checked_at"]


def test_illegibility_forces_ocr_and_zero_preserves_native_text(monkeypatch, tmp_path: Path):
    assert sm.native_text_ocr_threshold(0) == 24
    assert sm.native_text_ocr_threshold(100) >= 10**8
    calls: list[int] = []

    def boom(self, *args, **kwargs):
        calls.append(1)
        raise RuntimeError("no-ocr")

    monkeypatch.setattr(fitz.Page, "get_textpage_ocr", boom)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "A complete native text layer for this page.")
    data = doc.tobytes()
    doc.close()
    repo = cb.PdfCorpusRepository(tmp_path)
    legible = repo.save_asset(data, filename="legible.pdf", source_illegibility=0)
    assert calls == []
    assert legible["media_kind"] == "pdf"
    illegible = repo.save_asset(data, filename="illegible.pdf", source_illegibility=100)
    assert calls
    assert any("OCR unavailable" in warning for warning in illegible["warnings"])
    assert illegible["deterministic_checked_at"]


def test_url_scheme_is_http_only():
    try:
        sm.fetch_source_url("file:///tmp/secret.txt", max_bytes=1000)
    except ValueError as exc:
        assert "http" in str(exc)
    else:
        raise AssertionError("file URLs must be rejected")
