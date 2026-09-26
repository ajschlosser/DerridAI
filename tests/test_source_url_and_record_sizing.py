# Copyright 2026 Aaron John Schlosser, PhD.
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app.models import PdfCorpusRecordSizing  # noqa: E402
from app.source_gutenberg import fetch_source_url  # noqa: E402


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_wikisource_page_url_uses_mediawiki_api_not_page_scrape():
    payload = {"parse": {"title": "Père Goriot", "text": "<p>Balzac</p>"}}
    with patch("app.source_gutenberg.httpx.get", return_value=_response(payload)) as get, patch(
        "app.source_gutenberg.httpx.stream"
    ) as stream:
        data, name, kind = fetch_source_url("https://en.wikisource.org/wiki/P%C3%A8re_Goriot", max_bytes=10_000)
    stream.assert_not_called()
    assert get.call_args.args[0] == "https://en.wikisource.org/w/api.php"
    assert get.call_args.kwargs["params"]["page"] == "Père Goriot"
    assert get.call_args.kwargs["headers"]["User-Agent"]
    assert data == b"<p>Balzac</p>" and name.endswith(".html") and "html" in kind


def test_wikisource_api_error_is_a_user_error():
    with patch("app.source_gutenberg.httpx.get", return_value=_response({"error": {"info": "no such page"}})):
        with pytest.raises(ValueError, match="no such page"):
            fetch_source_url("https://en.wikisource.org/wiki/Nope", max_bytes=10_000)


def test_small_record_sizing_is_accepted():
    policy = PdfCorpusRecordSizing(
        preferred_record_chars=300, record_length_tolerance=30, long_record_chars=400, absolute_record_chars=500
    )
    assert policy.absolute_record_chars == 500


def test_inconsistent_record_sizing_is_still_rejected():
    with pytest.raises(ValueError):
        PdfCorpusRecordSizing(preferred_record_chars=300, record_length_tolerance=30, long_record_chars=310)


def test_ledger_decode_endpoint_returns_plain_jsonl(tmp_path):
    import asyncio
    import io
    import json

    zstd = pytest.importorskip("zstandard")
    from app.routers.corpus import decode_corpus_ledger
    from fastapi import UploadFile

    record = {"record_id": "r1", "source_document_id": "d1", "text": "Il n'y a pas de hors-texte.", "source_spans": [{"source_document_id": "d1", "block_id": "b1", "page": 1}]}
    raw = zstd.ZstdCompressor().compress((json.dumps(record) + "\n").encode())
    upload = UploadFile(io.BytesIO(raw), filename="corpus.jsonl.zst")
    result = asyncio.run(decode_corpus_ledger(upload))
    assert result["record_count"] == 1
    assert json.loads(result["text"].strip())["text"] == record["text"]
    assert result["filename"] == "corpus.jsonl"


def test_small_reviewer_sizing_is_not_silently_raised_by_segmentation():
    from app.corpus_segmentation import _record_sizing_policy

    policy = _record_sizing_policy(
        {"record_sizing": {"preferred_record_chars": 300, "record_length_tolerance": 30,
                           "long_record_chars": 400, "absolute_record_chars": 500}}, {},
    )
    assert policy == {"preferred_record_chars": 300, "record_length_tolerance": 30,
                      "long_record_chars": 400, "absolute_record_chars": 500}


def test_upstream_http_errors_are_reported_as_bad_gateway_not_server_faults():
    import httpx
    from app.models import PdfSourceUrlImport
    from app.routers import corpus as routes
    from fastapi import HTTPException

    request = httpx.Request("GET", "https://example.org/x")
    error = httpx.HTTPStatusError("nope", request=request, response=httpx.Response(403, request=request))
    with patch.object(routes, "fetch_source_url", side_effect=error):
        with pytest.raises(HTTPException) as info:
            routes.import_pdf_asset_url(PdfSourceUrlImport(url="https://example.org/x"))
    assert info.value.status_code == 502 and "403" in info.value.detail


def test_wikisource_subpage_urls_use_the_api():
    payload = {"parse": {"title": "Balzac/Preface", "text": "<p>x</p>"}}
    with patch("app.source_gutenberg.httpx.get", return_value=_response(payload)) as get, patch(
        "app.source_gutenberg.httpx.stream"
    ) as stream:
        _, name, _ = fetch_source_url("https://en.wikisource.org/wiki/Balzac/Preface", max_bytes=10_000)
    stream.assert_not_called()
    assert get.call_args.kwargs["params"]["page"] == "Balzac/Preface" and name.endswith(".html")
