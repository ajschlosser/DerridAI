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

"""ProviderHttp is the one bounded HTTP boundary for Corpus Capture providers.

Why: providers fetch URLs that remote APIs name. Following a redirect or an
off-list host would be SSRF; unbounded bodies or endless retries would stall a
capture; a cancelled capture must stop between attempts.
How: every response comes from ``httpx.MockTransport``.
"""
from __future__ import annotations

import httpx
import pytest
from _capture_support import http_for, json_response, no_rate_gate
from app.source_identity import CaptureError, CaptureErrorCode
from app.source_provider import POLICIES, host_allowed

pytestmark = pytest.mark.unit
API = "https://en.wikisource.org/w/api.php"


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    no_rate_gate(monkeypatch)


def _counting(responses):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        item = responses[min(len(calls), len(responses)) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    return handler, calls


@pytest.mark.parametrize(
    "url",
    ["https://evil.example/w/api.php", "http://en.wikisource.org/w/api.php", "https://en.wikisource.org:8443/", "https://user:pw@en.wikisource.org/", "https://wikisource.org.evil.example/"],
)
def test_disallowed_hosts_are_refused_before_any_request(url):
    handler, calls = _counting([json_response({})])
    with pytest.raises(CaptureError) as error:
        http_for(handler).get(url)
    assert error.value.code == CaptureErrorCode.UNSUPPORTED_SOURCE
    assert calls == []


def test_allow_list_accepts_project_subdomains_only_for_its_family():
    assert host_allowed("https://de.wikisource.org/w/api.php", POLICIES["wikimedia"])
    assert not host_allowed("https://de.wikisource.org/w/api.php", POLICIES["gutenberg"])


def test_a_redirect_is_returned_not_followed():
    handler, calls = _counting([httpx.Response(302, headers={"location": "https://evil.example/"})])
    response = http_for(handler).get(API)
    assert response.status_code == 302
    assert calls == [API]


def test_oversize_body_is_refused():
    handler, _ = _counting([httpx.Response(200, content=b"x" * 2048)])
    with pytest.raises(CaptureError) as error:
        http_for(handler).get(API, max_bytes=1024)
    assert error.value.code == CaptureErrorCode.SOURCE_TOO_LARGE


def test_server_errors_and_timeouts_are_retried_with_backoff_then_succeed():
    handler, calls = _counting([httpx.Response(503), httpx.ReadTimeout("slow"), json_response({"ok": True})])
    waits: list[float] = []
    payload = http_for(handler, sleep=waits.append).get_json(API)
    assert payload == {"ok": True}
    assert len(calls) == 3
    assert waits == [1.0, 2.0]  # bounded exponential backoff


def test_retries_are_bounded():
    handler, calls = _counting([httpx.Response(500)])
    with pytest.raises(CaptureError) as error:
        http_for(handler).get(API)
    assert error.value.code == CaptureErrorCode.PROVIDER_UNAVAILABLE
    assert len(calls) == POLICIES["wikimedia"].max_attempts


def test_not_found_is_not_retried():
    handler, calls = _counting([httpx.Response(404)])
    with pytest.raises(CaptureError) as error:
        http_for(handler).get_json(API)
    assert error.value.code == CaptureErrorCode.SOURCE_NOT_FOUND
    assert len(calls) == 1


def test_cancellation_stops_before_the_next_attempt():
    state = {"cancel": False}
    calls: list[int] = []

    def handler(request):
        calls.append(1)
        state["cancel"] = True
        return httpx.Response(503)

    with pytest.raises(CaptureError) as error:
        http_for(handler, cancelled=lambda: state["cancel"]).get(API)
    assert error.value.code == CaptureErrorCode.CANCELLED
    assert len(calls) == 1


def test_mediawiki_ratelimited_error_is_classified_as_rate_limited():
    handler, calls = _counting([json_response({"error": {"code": "ratelimited", "info": "slow down"}})])
    with pytest.raises(CaptureError) as error:
        http_for(handler).get_json(API)
    assert error.value.code == CaptureErrorCode.RATE_LIMITED
    assert error.value.transient


def test_mediawiki_missing_page_is_source_not_found():
    handler, _ = _counting([json_response({"error": {"code": "missingtitle", "info": "no page"}})])
    with pytest.raises(CaptureError) as error:
        http_for(handler).get_json(API)
    assert error.value.code == CaptureErrorCode.SOURCE_NOT_FOUND


def test_invalid_json_is_an_invalid_provider_response():
    handler, _ = _counting([httpx.Response(200, content=b"<html>")])
    with pytest.raises(CaptureError) as error:
        http_for(handler).get_json(API)
    assert error.value.code == CaptureErrorCode.INVALID_PROVIDER_RESPONSE
