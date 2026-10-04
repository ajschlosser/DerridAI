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

"""CorpusCaptureService: discovery → reconciliation → review → acquisition → source registration.

Corpus Capture creates and manages *sources*; it never starts a Corpus Builder
build. Provider transport lives in the provider modules, reconciliation in
``source_reconcile``, persistence in ``capture_store`` and job threads in
``job_capture``. Nothing on this path consults a language model.
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

from .capture_store import CaptureStore, now_iso
from .source_identity import (
    CAPTURE_CONTRACT_VERSION,
    CaptureError,
    CaptureErrorCode,
    CaptureOptions,
    ContributionRole,
    ResolvedAuthor,
    SourceCandidate,
    WorkRelationship,
)
from .source_provider import (
    AcquiredSource,
    DiscoveryReport,
    ProviderHttp,
    SourceProvider,
)
from .source_reconcile import dedupe_exact, reconcile, summarize
from .source_safety import MAX_SOURCE_BYTES

Cancelled = Callable[[], bool]
Progress = Callable[[str, dict[str, Any]], None]
ProviderFactory = Callable[[str, Cancelled], SourceProvider]
Registrar = Callable[[AcquiredSource], dict[str, Any]]

PROVIDERS = ("gutenberg", "wikisource")
DEFAULT_SELECTED_ROLES = {ContributionRole.AUTHOR, ContributionRole.COAUTHOR}
MAX_ACQUIRE_ATTEMPTS = 3


def default_provider_factory(provider: str, cancelled: Cancelled) -> SourceProvider:
    if provider == "gutenberg":
        from .source_gutenberg import GutenbergProvider

        return GutenbergProvider(ProviderHttp("gutenberg", cancelled=cancelled))
    if provider == "wikisource":
        from .source_wikisource import WikisourceProvider

        return WikisourceProvider(ProviderHttp("wikimedia", cancelled=cancelled))
    raise CaptureError(CaptureErrorCode.UNSUPPORTED_SOURCE, f"Unknown provider: {provider}")


def default_registrar(acquired: AcquiredSource) -> dict[str, Any]:
    """Register through the same SourceDocument path as uploads, URLs and single library imports."""
    from .corpus_builder import pdf_corpus_repository

    asset = pdf_corpus_repository.save_asset(
        acquired.data,
        filename=acquired.filename,
        content_type=acquired.content_type,
        catalog_metadata=acquired.catalog_metadata,
        source_url=acquired.source_uri,
        detect_page_numbers=True,
    )
    if acquired.scans:
        warnings = list((acquired.catalog_metadata or {}).get("scan_warnings") or [])
        asset = pdf_corpus_repository.store_source_scans(
            asset["asset_id"], acquired.scans, source="wikisource_djvu", warnings=warnings,
        )
    return asset


def default_identity_enricher(candidates: list[SourceCandidate], author: ResolvedAuthor, cancelled: Cancelled) -> list[str]:
    """Attach Wikidata work/edition identities; failures become warnings, never capture failures."""
    from . import source_wikidata
    from .source_wikisource import WikisourceProvider

    warnings: list[str] = []
    # A locally resolved Gutenberg author plus Gutenberg-only candidates has a
    # complete acquisition path without Wikimedia. Work/edition reconciliation
    # remains optional enrichment rather than a hidden network prerequisite.
    if not author.wikidata_qid and candidates and all(c.provider == "gutenberg" for c in candidates):
        return warnings
    http = ProviderHttp("wikimedia", cancelled=cancelled)
    try:
        wikisource = [c for c in candidates if c.provider == "wikisource"]
        if wikisource:
            WikisourceProvider(http).enrich_work_ids(wikisource)
        gutenberg = [c for c in candidates if c.provider == "gutenberg"]
        if gutenberg:
            items = source_wikidata.gutenberg_edition_items(http, [c.provider_item_id for c in gutenberg])
            for candidate in gutenberg:
                candidate.wikidata_edition_id = items.get(candidate.provider_item_id)
        source_wikidata.apply_work_identities(http, candidates, author.wikidata_qid)
    except CaptureError as exc:
        if exc.code == CaptureErrorCode.CANCELLED:
            raise
        warnings.append(f"wikidata_reconciliation_incomplete:{exc.code}")
    return warnings


class CorpusCaptureService:
    def __init__(
        self,
        store: CaptureStore,
        *,
        provider_factory: ProviderFactory = default_provider_factory,
        registrar: Registrar = default_registrar,
        identity_enricher: Callable[[list[SourceCandidate], ResolvedAuthor, Cancelled], list[str]] = default_identity_enricher,
        sleep: Callable[[float], None] = time.sleep,
        max_source_bytes: int = MAX_SOURCE_BYTES,
    ) -> None:
        self.store = store
        self.provider_factory = provider_factory
        self.registrar = registrar
        self.identity_enricher = identity_enricher
        self.sleep = sleep
        self.max_source_bytes = max_source_bytes

    # --- lifecycle ----------------------------------------------------------------

    def create(self, author: ResolvedAuthor, options: CaptureOptions) -> dict[str, Any]:
        unknown = [p for p in options.providers if p not in PROVIDERS]
        if unknown or not options.providers:
            raise CaptureError(CaptureErrorCode.UNSUPPORTED_SOURCE, "Choose at least one supported library.")
        created = now_iso()
        capture = {
            "capture_id": f"cc_{uuid.uuid4().hex[:16]}",
            "author": author.to_dict(),
            "options": options.to_dict(),
            "status": "draft",
            "phase": "created",
            "created_at": created,
            "discovery_started_at": None,
            "discovery_completed_at": None,
            "last_refreshed_at": None,
            "provider_snapshots": [],
            "summary": summarize([]),
            "progress": {},
            "warnings": [],
            "errors": [],
            "last_refresh_diff": None,
            "discovery_contract_version": CAPTURE_CONTRACT_VERSION,
        }
        return self.store.save_capture(capture)

    def _set(self, capture_id: str, **fields: Any) -> dict[str, Any]:
        return self.store.update_capture(capture_id, **fields)

    def _resummarize(self, capture_id: str, **fields: Any) -> dict[str, Any]:
        return self._set(capture_id, summary=summarize(self.store.candidates(capture_id)), **fields)

    # --- discovery ------------------------------------------------------------------

    def discover(self, capture_id: str, *, cancelled: Cancelled = lambda: False, progress: Progress | None = None) -> dict[str, Any]:
        capture = self.store.get_capture(capture_id)
        author = ResolvedAuthor.from_dict(capture["author"])
        options = CaptureOptions.from_dict(capture["options"])
        refreshing = bool(capture.get("discovery_completed_at"))
        started = now_iso()
        self._set(capture_id, status="discovering", phase="resolving_author", discovery_started_at=capture.get("discovery_started_at") or started, errors=[])

        def report_progress(phase: str, detail: dict[str, Any]) -> None:
            self._set(capture_id, phase=phase, progress=detail)
            if progress:
                progress(phase, detail)

        found: list[SourceCandidate] = []
        snapshots: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        warnings: list[str] = []
        try:
            for provider_id in options.providers:
                if cancelled():
                    raise CaptureError(CaptureErrorCode.CANCELLED, "The capture was cancelled.")
                report = DiscoveryReport(provider=provider_id, projects_searched=[], identities_used=[])
                try:
                    provider = self.provider_factory(provider_id, cancelled)
                    found.extend(provider.enumerate_author_sources(author, options, report, report_progress))
                except CaptureError as exc:
                    if exc.code == CaptureErrorCode.CANCELLED:
                        raise
                    # A provider that fails leaves the other providers' results intact.
                    errors.append({"provider": provider_id, **exc.to_dict()})
                    report.errors = [*(report.errors or []), exc.to_dict()]
                snapshots.append({**report.__dict__, "searched_at": now_iso()})
            report_progress("reconciling", {"candidates": len(found)})
            found, duplicates = dedupe_exact(found)
            if duplicates:
                warnings.append(f"exact_provider_duplicates_removed:{duplicates}")
            warnings.extend(self.identity_enricher(found, author, cancelled))
            if not options.include_originals:
                found = [
                    candidate
                    for candidate in found
                    if candidate.relationship_to_work == WorkRelationship.TRANSLATION
                ]
        except CaptureError as exc:
            if exc.code != CaptureErrorCode.CANCELLED:
                raise
            result = self._resummarize(capture_id, status="cancelled", phase="cancelled", provider_snapshots=snapshots)
            if progress:
                progress("cancelled", {"done": len(options.providers), "total": len(options.providers)})
            return result
        rows = self._candidate_rows(found)
        discovered_at = now_iso()
        diff = self.store.merge_candidates(capture_id, rows, discovered_at=discovered_at)
        completed = now_iso()
        fields: dict[str, Any] = {
            "status": "awaiting_review",
            "phase": "awaiting_review",
            "provider_snapshots": snapshots,
            "discovery_completed_at": completed,
            "errors": errors,
            "warnings": warnings,
            "progress": {},
        }
        if refreshing:
            fields["last_refreshed_at"] = completed
            fields["last_refresh_diff"] = {
                "new": len(diff["new"]), "changed": len(diff["changed"]), "unchanged": diff["unchanged"], "missing": len(diff["missing"]),
                "new_ids": diff["new"], "changed_ids": diff["changed"], "missing_ids": diff["missing"],
            }
        result = self._resummarize(capture_id, **fields)
        if progress:
            progress("awaiting_review", {"done": len(options.providers), "total": len(options.providers)})
        return result

    @staticmethod
    def _candidate_rows(found: list[SourceCandidate]) -> list[dict[str, Any]]:
        rows = []
        for candidate, recon in zip(found, reconcile(found), strict=True):
            row = candidate.to_dict()
            row.update(recon)
            row["provider_key"] = candidate.provider_key
            # Default inclusion: the person's own works with an exact identity. Unknown roles,
            # uncertain identities and every other role stay visible but deselected for review.
            selected = (
                candidate.contribution_role in DEFAULT_SELECTED_ROLES
                and candidate.identity_confidence == "exact"
            )
            row["selection_status"] = "selected" if selected else "excluded"
            row["selection_reason"] = "default_rule" if selected else (
                "needs_review" if candidate.identity_confidence != "exact" else f"role:{candidate.contribution_role}"
            )
            rows.append(row)
        return rows

    # --- review -------------------------------------------------------------------------

    def set_selection(self, capture_id: str, candidate_ids: list[str] | None, selected: bool) -> dict[str, Any]:
        """Select/deselect candidates (``None`` = all). Registered candidates keep their source either way."""
        self.store.get_capture(capture_id)
        rows = self.store.candidates(capture_id)
        wanted = set(candidate_ids) if candidate_ids is not None else None
        unknown = (wanted or set()) - {row["candidate_id"] for row in rows}
        if unknown:
            raise KeyError(sorted(unknown)[0])
        changed = []
        for row in rows:
            if wanted is None or row["candidate_id"] in wanted:
                row["selection_status"] = "selected" if selected else "excluded"
                row["selection_reason"] = "user"
                changed.append(row)
        self.store.update_candidates(changed)
        return self._resummarize(capture_id)

    # --- acquisition ----------------------------------------------------------------------

    def acquisition_queue(self, capture_id: str, *, retry_failed_only: bool = False) -> list[dict[str, Any]]:
        rows = self.store.candidates(capture_id)
        if retry_failed_only:
            return [row for row in rows if row["acquisition_status"] == "failed"]
        return [row for row in rows if row["selection_status"] == "selected" and row["acquisition_status"] in {"pending", "failed", "cancelled"}]

    def acquire(
        self,
        capture_id: str,
        *,
        retry_failed_only: bool = False,
        cancelled: Cancelled = lambda: False,
        progress: Progress | None = None,
    ) -> dict[str, Any]:
        queue = self.acquisition_queue(capture_id, retry_failed_only=retry_failed_only)
        self._set(capture_id, status="acquiring", phase="acquiring", progress={"done": 0, "total": len(queue)})
        providers: dict[str, SourceProvider] = {}
        hashes = {
            str(row.get("source_sha256")): row["candidate_id"]
            for row in self.store.candidates(capture_id)
            if row.get("acquisition_status") == "registered" and row.get("source_sha256")
        }
        was_cancelled = False
        for index, row in enumerate(queue):
            if cancelled():
                was_cancelled = True
                for rest in queue[index:]:
                    self.store.update_candidate(rest["candidate_id"], acquisition_status="cancelled")
                break
            detail = {"done": index, "total": len(queue), "current": row["title"]}
            self._set(capture_id, progress=detail)
            if progress:
                progress("acquiring", detail)
            try:
                provider = providers.get(row["provider"]) or self.provider_factory(row["provider"], cancelled)
                providers[row["provider"]] = provider
                self._acquire_one(row, provider, hashes, cancelled)
            except CaptureError as exc:
                if exc.code == CaptureErrorCode.CANCELLED:
                    self.store.update_candidate(row["candidate_id"], acquisition_status="cancelled")
                    was_cancelled = True
                    for rest in queue[index + 1 :]:
                        self.store.update_candidate(rest["candidate_id"], acquisition_status="cancelled")
                    break
                # One failed source never fails the batch; the error stays on its candidate.
                self.store.update_candidate(row["candidate_id"], acquisition_status="failed", error=exc.to_dict(), error_detail=exc.detail[:2000])
        rows = self.store.candidates(capture_id)
        failed = sum(1 for r in rows if r["acquisition_status"] == "failed")
        status = "cancelled" if was_cancelled else ("partial" if failed else "complete")
        result = self._resummarize(
            capture_id,
            status=status,
            phase=status,
            progress={"done": len(queue), "total": len(queue)},
        )
        if progress:
            progress(status, {"done": len(queue), "total": len(queue)})
        return result

    def _acquire_one(self, row: dict[str, Any], provider: SourceProvider, hashes: dict[str, str], cancelled: Cancelled) -> None:
        candidate = SourceCandidate.from_dict(row)
        attempts = int(row.get("attempts") or 0)
        self.store.update_candidate(row["candidate_id"], acquisition_status="fetching", error=None)
        acquired: AcquiredSource | None = None
        for attempt in range(MAX_ACQUIRE_ATTEMPTS):
            attempts += 1
            try:
                acquired = provider.fetch_source(candidate, max_bytes=self.max_source_bytes)
                break
            except CaptureError as exc:
                if not exc.transient or attempt + 1 == MAX_ACQUIRE_ATTEMPTS:
                    self.store.update_candidate(row["candidate_id"], attempts=attempts)
                    raise
                if cancelled():
                    raise CaptureError(CaptureErrorCode.CANCELLED, "The capture was cancelled.") from exc
                self.sleep(2.0 * (2**attempt))
        assert acquired is not None
        if len(acquired.data) > self.max_source_bytes:
            raise CaptureError(CaptureErrorCode.SOURCE_TOO_LARGE, "The source exceeds the ingestion size limit.")
        acquired_at = now_iso()
        self.store.update_candidate(row["candidate_id"], acquisition_status="acquired", attempts=attempts)
        # Provider + capture provenance travels with the SourceDocument's catalogue metadata.
        acquired.catalog_metadata.update({
            "provider_item_id": candidate.provider_item_id,
            "source_project_language": candidate.source_project_language,
            "document_languages": candidate.document_languages,
            "original_language": candidate.original_language,
            "relationship_to_work": candidate.relationship_to_work,
            "canonical_work_id": row.get("canonical_work_id"),
            "wikidata_work_id": candidate.wikidata_work_id,
            "wikidata_edition_id": candidate.wikidata_edition_id,
            "contribution_role": candidate.contribution_role,
            "rights_status": candidate.rights_status,
            "rights_source": candidate.rights_source,
            "discovery_method": candidate.discovery_method,
            "captured_by": {"capture_id": row["capture_id"], "candidate_id": row["candidate_id"], "discovered_at": row.get("discovered_at"), "acquired_at": acquired_at},
        })
        if not acquired.catalog_metadata.get("translator") and candidate.translators:
            acquired.catalog_metadata["translator"] = "; ".join(candidate.translators)
        try:
            asset = self.registrar(acquired)
        except (ValueError, OSError) as exc:
            raise CaptureError(CaptureErrorCode.REGISTRATION_FAILED, "The source could not be registered.", detail=str(exc)) from exc
        source_id = str(asset.get("asset_id") or "")
        digest = str(asset.get("sha256") or "")
        duplicate_of = hashes.get(digest) if digest else None
        self.store.link_source(source_id, row, acquired_at)
        self.store.update_candidate(
            row["candidate_id"],
            acquisition_status="registered",
            source_document_id=source_id,
            source_sha256=digest,
            acquired_at=acquired_at,
            error=None,
            # Identical bytes through another provider identity: storage is shared, both relations survive.
            digital_duplicate_of=duplicate_of if duplicate_of and duplicate_of != row["candidate_id"] else None,
        )
        if digest:
            hashes.setdefault(digest, row["candidate_id"])
