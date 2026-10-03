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

"""Corpus Capture lifecycle: discover → review → acquire → retry/refresh, durable across restarts.

Why: a capture can run for hours across many sources. One failure must not fail the
batch, a cancellation must keep finished work, a refresh must never re-download or drop
what was registered, and a restart must never report an interrupted capture as done.
How: a tmp-path CaptureStore, fake providers and a content-addressed fake registrar.
"""
from __future__ import annotations

import pytest
from _capture_support import FakeProvider, FakeRegistrar, author, candidate
from app.capture_store import CaptureStore
from app.source_capture import CorpusCaptureService
from app.source_identity import CaptureError, CaptureErrorCode, CaptureOptions

pytestmark = pytest.mark.unit


def _service(tmp_path, providers, registrar=None):
    store = CaptureStore(tmp_path / "captures.sqlite")
    service = CorpusCaptureService(
        store,
        provider_factory=lambda name, cancelled: providers[name],
        registrar=registrar or FakeRegistrar(),
        identity_enricher=lambda found, who, cancelled: [],
        sleep=lambda _s: None,
    )
    return store, service


def _by_item(store, capture_id):
    return {row["provider_item_id"]: row for row in store.candidates(capture_id)}


def _discovered(tmp_path, gutenberg, wikisource=None, registrar=None):
    providers = {"gutenberg": gutenberg, "wikisource": wikisource or FakeProvider("wikisource", [])}
    store, service = _service(tmp_path, providers, registrar)
    capture = service.create(author(), CaptureOptions())
    service.discover(capture["capture_id"])
    return store, service, capture["capture_id"]


def test_create_then_discover_selects_only_exact_authored_works_by_default(tmp_path):
    gutenberg = FakeProvider("gutenberg", [
        candidate("1", "Own work"),
        candidate("2", "Co-written", contribution_role="coauthor"),
        candidate("3", "Unsure", identity_confidence="needs_review"),
        candidate("4", "Translated by them", contribution_role="translator"),
    ])
    store, service, capture_id = _discovered(tmp_path, gutenberg)
    capture = store.get_capture(capture_id)
    assert capture["status"] == "awaiting_review"
    assert capture["discovery_contract_version"].startswith("derridai-corpus-capture-")
    assert [s["provider"] for s in capture["provider_snapshots"]] == ["gutenberg", "wikisource"]
    rows = _by_item(store, capture_id)
    assert {k: r["selection_status"] for k, r in rows.items()} == {"1": "selected", "2": "selected", "3": "excluded", "4": "excluded"}
    assert rows["3"]["selection_reason"] == "needs_review"
    assert rows["4"]["selection_reason"] == "role:translator"
    assert capture["summary"]["selected"] == 2


def test_a_failing_provider_leaves_the_other_providers_results(tmp_path):
    class Broken(FakeProvider):
        def enumerate_author_sources(self, *args):
            raise CaptureError(CaptureErrorCode.PROVIDER_UNAVAILABLE, "down")

    store, _service_, capture_id = _discovered(tmp_path, FakeProvider("gutenberg", [candidate("1", "A")]), Broken("wikisource", []))
    capture = store.get_capture(capture_id)
    assert capture["status"] == "awaiting_review"
    assert capture["errors"] == [{"provider": "wikisource", "code": "provider_unavailable", "message": "down"}]
    assert list(_by_item(store, capture_id)) == ["1"]


def test_selection_patch_changes_only_the_named_candidates(tmp_path):
    store, service, capture_id = _discovered(tmp_path, FakeProvider("gutenberg", [candidate("1", "A"), candidate("2", "B")]))
    first = _by_item(store, capture_id)["1"]["candidate_id"]
    summary = service.set_selection(capture_id, [first], False)["summary"]
    rows = _by_item(store, capture_id)
    assert (rows["1"]["selection_status"], rows["1"]["selection_reason"]) == ("excluded", "user")
    assert rows["2"]["selection_status"] == "selected"
    assert summary["selected"] == 1
    assert service.set_selection(capture_id, None, True)["summary"]["selected"] == 2
    with pytest.raises(KeyError):
        service.set_selection(capture_id, ["cand-nope"], True)


def test_one_failed_source_makes_the_capture_partial_and_retry_fetches_only_it(tmp_path):
    items = [candidate(str(i), f"Work {i}") for i in range(1, 6)]
    gutenberg = FakeProvider("gutenberg", items, failures={"3": CaptureError(CaptureErrorCode.SOURCE_NOT_FOUND, "gone")})
    registrar = FakeRegistrar()
    store, service, capture_id = _discovered(tmp_path, gutenberg, registrar=registrar)

    capture = service.acquire(capture_id)
    rows = _by_item(store, capture_id)
    assert capture["status"] == "partial"
    assert capture["summary"]["acquisition"] == {"registered": 4, "failed": 1}
    assert rows["3"]["error"] == {"code": "source_not_found", "message": "gone"}
    assert rows["1"]["source_document_id"].startswith("pdf-")
    assert registrar.registered[0].catalog_metadata["captured_by"]["capture_id"] == capture_id

    gutenberg.failures.clear()
    gutenberg.fetched.clear()
    assert [row["provider_item_id"] for row in service.acquisition_queue(capture_id, retry_failed_only=True)] == ["3"]
    capture = service.acquire(capture_id, retry_failed_only=True)
    assert gutenberg.fetched == ["3"]
    assert capture["status"] == "complete"
    assert _by_item(store, capture_id)["3"]["error"] is None


def test_transient_fetch_errors_are_retried_before_failing(tmp_path):
    class Flaky(FakeProvider):
        def fetch_source(self, c, *, max_bytes):
            if len(self.fetched) < 2:
                self.fetched.append(c.provider_item_id)
                raise CaptureError(CaptureErrorCode.NETWORK_TIMEOUT, "slow")
            return super().fetch_source(c, max_bytes=max_bytes)

    gutenberg = Flaky("gutenberg", [candidate("1", "A")])
    store, service, capture_id = _discovered(tmp_path, gutenberg)
    assert service.acquire(capture_id)["status"] == "complete"
    assert _by_item(store, capture_id)["1"]["attempts"] == 3


def test_cancel_mid_acquire_keeps_completed_sources(tmp_path):
    state = {"cancel": False}
    registrar = FakeRegistrar(after=lambda acquired: state.update(cancel=True))
    items = [candidate(str(i), f"Work {i}") for i in range(1, 4)]
    store, service, capture_id = _discovered(tmp_path, FakeProvider("gutenberg", items), registrar=registrar)
    capture = service.acquire(capture_id, cancelled=lambda: state["cancel"])
    rows = _by_item(store, capture_id)
    assert capture["status"] == "cancelled"
    assert rows["1"]["acquisition_status"] == "registered"
    assert {rows["2"]["acquisition_status"], rows["3"]["acquisition_status"]} == {"cancelled"}
    # Cancelled items are queued again by the next acquire; the registered one is not.
    assert [row["provider_item_id"] for row in service.acquisition_queue(capture_id)] == ["2", "3"]


def test_terminal_acquisition_progress_matches_queue_and_summary(tmp_path):
    items = [candidate("1", "A"), candidate("2", "B")]
    store, service, capture_id = _discovered(tmp_path, FakeProvider("gutenberg", items))
    progress = []
    capture = service.acquire(capture_id, progress=lambda phase, detail: progress.append((phase, detail)))
    assert capture["status"] == "complete"
    assert capture["progress"] == {"done": 2, "total": 2}
    assert progress[-1] == ("complete", {"done": 2, "total": 2})


def test_refresh_reports_new_changed_and_missing_without_redownloading(tmp_path):
    gutenberg = FakeProvider("gutenberg", [candidate("1", "Kept"), candidate("2", "Renamed"), candidate("3", "Withdrawn")])
    store, service, capture_id = _discovered(tmp_path, gutenberg)
    service.acquire(capture_id)
    registered = _by_item(store, capture_id)["1"]["source_document_id"]

    gutenberg.candidates = [candidate("1", "Kept"), candidate("2", "Renamed: new subtitle"), candidate("4", "New")]
    gutenberg.fetched.clear()
    capture = service.discover(capture_id)
    diff = capture["last_refresh_diff"]
    assert (diff["new"], diff["changed"], diff["unchanged"], diff["missing"]) == (1, 1, 1, 1)
    assert capture["last_refreshed_at"]
    rows = _by_item(store, capture_id)
    assert rows["2"]["metadata_changed_fields"] == ["title"]
    assert rows["3"]["upstream_status"] == "missing"
    # Nothing registered is lost or re-fetched; only the new source is acquired next.
    assert rows["1"]["source_document_id"] == registered and rows["3"]["acquisition_status"] == "registered"
    service.acquire(capture_id)
    assert gutenberg.fetched == ["4"]


def test_identical_bytes_from_two_providers_share_storage_and_keep_both_links(tmp_path):
    same = b"Also sprach Zarathustra."
    gutenberg = FakeProvider("gutenberg", [candidate("1998", "Also sprach Zarathustra", document_languages=["de"])], payloads={"1998": same})
    wikisource = FakeProvider("wikisource", [candidate("de:Also sprach Zarathustra", "Also sprach Zarathustra", provider="wikisource", document_languages=["de"])], payloads={"de:Also sprach Zarathustra": same})
    store, service, capture_id = _discovered(tmp_path, gutenberg, wikisource)
    service.acquire(capture_id)
    rows = _by_item(store, capture_id)
    first, second = rows["1998"], rows["de:Also sprach Zarathustra"]
    assert first["source_document_id"] == second["source_document_id"]
    assert second["digital_duplicate_of"] == first["candidate_id"]
    assert first["digital_duplicate_of"] is None
    links = store.links_for_sources([first["source_document_id"]])[first["source_document_id"]]
    assert sorted(link["provider"] for link in links) == ["gutenberg", "wikisource"]


def test_restart_marks_running_captures_interrupted_and_unfinished_items_failed(tmp_path):
    store, service, capture_id = _discovered(tmp_path, FakeProvider("gutenberg", [candidate("1", "A"), candidate("2", "B")]))
    rows = _by_item(store, capture_id)
    store.update_candidate(rows["1"]["candidate_id"], acquisition_status="fetching")
    store.update_capture(capture_id, status="acquiring")

    restarted = CaptureStore(tmp_path / "captures.sqlite")
    capture = restarted.get_capture(capture_id)
    assert capture["status"] == "interrupted"
    assert "interrupted_by_restart" in capture["warnings"]
    after = {row["provider_item_id"]: row for row in restarted.candidates(capture_id)}
    assert after["1"]["acquisition_status"] == "failed"
    assert after["1"]["error"]["code"] == "cancelled"
    assert after["2"]["acquisition_status"] == "pending"


def test_unsupported_provider_is_refused_at_creation(tmp_path):
    _store, service = _service(tmp_path, {})
    with pytest.raises(CaptureError) as error:
        service.create(author(), CaptureOptions(providers=["archive_org"]))
    assert error.value.code == CaptureErrorCode.UNSUPPORTED_SOURCE
