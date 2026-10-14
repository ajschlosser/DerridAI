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

"""Offline helpers shared by the Corpus Capture suites: a routed httpx mock and fake providers.

No helper here touches the network. Provider HTTP goes through ``httpx.MockTransport``;
the capture service gets an in-memory provider factory and registrar.
"""
from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "api"))

from app import source_provider  # noqa: E402
from app.source_identity import (  # noqa: E402
    CaptureError,
    CaptureOptions,
    ResolvedAuthor,
    SourceCandidate,
)
from app.source_provider import (  # noqa: E402
    AcquiredSource,
    DiscoveryReport,
    ProviderHttp,
)

Handler = Callable[[httpx.Request], httpx.Response]


def no_rate_gate(monkeypatch) -> None:
    """The shared per-family gate sleeps between requests; offline tests do not need to wait."""
    monkeypatch.setattr(source_provider._Gate, "wait_turn", lambda self: None)


def http_for(handler: Handler, family: str = "wikimedia", **kwargs: Any) -> ProviderHttp:
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    return ProviderHttp(family, client=client, sleep=kwargs.pop("sleep", lambda _s: None), **kwargs)


def json_response(payload: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def author(**overrides: Any) -> ResolvedAuthor:
    data: dict[str, Any] = {
        "identity_id": "wikidata:Q9358",
        "canonical_name": "Friedrich Nietzsche",
        "wikidata_qid": "Q9358",
        "aliases": ["Friedrich Wilhelm Nietzsche"],
        "birth_year": 1844,
        "death_year": 1900,
    }
    data.update(overrides)
    return ResolvedAuthor(**data)


def candidate(item_id: str, title: str, *, provider: str = "gutenberg", **overrides: Any) -> SourceCandidate:
    data: dict[str, Any] = {
        "provider": provider,
        "provider_item_id": item_id,
        "title": title,
        "source_uri": f"https://example.invalid/{provider}/{item_id}",
        "contribution_role": "author",
        "document_languages": ["en"],
        "identity_confidence": "exact",
    }
    data.update(overrides)
    return SourceCandidate(**data)


class FakeProvider:
    """Enumerates a fixed candidate list; fetches bytes or raises a scripted CaptureError per item id."""

    def __init__(self, provider_id: str, candidates: list[SourceCandidate], *, failures: dict[str, CaptureError] | None = None, payloads: dict[str, bytes] | None = None) -> None:
        self.provider_id = provider_id
        self.candidates = candidates
        self.failures = dict(failures or {})
        self.payloads = dict(payloads or {})
        self.fetched: list[str] = []

    def enumerate_author_sources(self, author: ResolvedAuthor, options: CaptureOptions, report: DiscoveryReport, progress) -> Iterator[SourceCandidate]:
        progress(f"discovering_{self.provider_id}", {"done": 0, "total": 1})
        report.projects_searched.append(self.provider_id)
        report.result_count = len(self.candidates)
        yield from (SourceCandidate.from_dict(item.to_dict()) for item in self.candidates)

    def fetch_source(self, candidate: SourceCandidate, *, max_bytes: int) -> AcquiredSource:
        self.fetched.append(candidate.provider_item_id)
        failure = self.failures.get(candidate.provider_item_id)
        if failure is not None:
            raise failure
        data = self.payloads.get(candidate.provider_item_id, f"text of {candidate.provider_key}".encode())
        return AcquiredSource(data=data, filename=f"{candidate.provider_item_id}.txt", content_type="text/plain", source_uri=candidate.source_uri, catalog_metadata={"title": candidate.title})


class FakeRegistrar:
    """Content-addressed like ``save_asset``: identical bytes register as the same asset id."""

    def __init__(self, after: Callable[[AcquiredSource], None] | None = None) -> None:
        self.registered: list[AcquiredSource] = []
        self.after = after

    def __call__(self, acquired: AcquiredSource) -> dict[str, Any]:
        self.registered.append(acquired)
        digest = hashlib.sha256(acquired.data).hexdigest()
        if self.after:
            self.after(acquired)
        return {"asset_id": f"pdf-{digest[:12]}", "sha256": digest}
