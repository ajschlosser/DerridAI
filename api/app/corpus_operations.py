# Copyright 2026 Aaron John Schlosser, PhD.
"""Operations feed management: list, dismiss, clear, and cancel corpus builds as jobs.

The generic Operations feed shows every corpus build as a dismissible job row, distinct
from the scholarly build/record data itself: "dismiss" hides an operation entry without
deleting the underlying build, its source bindings, or a publication. Moved verbatim out
of PdfCorpusBuildManager as a mixin (see corpus_review_actions.py's module docstring for
why a mixin, not free functions, and corpus_build_lifecycle.py's for why every mixin's
mypy stub block must be wrapped in `if TYPE_CHECKING:`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .corpus_record_quality import iso_now
from .corpus_review_actions import _serialize_record_mutation
from .corpus_reviewer_helpers import _operation_from_build


class OperationsMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    See corpus_review_actions.py's identical block for the full explanation, including why
    everything below is wrapped in `if TYPE_CHECKING:`.
    """

    if TYPE_CHECKING:
        repo: Any
        _lock: Any
        _cancel: set[str]


    def list_operations(self, limit: int = 200) -> list[dict[str, Any]]:
        listing = self.repo.list_builds(offset=0, limit=max(1, min(1000, limit)))
        return [
            _operation_from_build(build)
            for build in listing["items"]
            if not build.get("operation_hidden")
        ]


    def operation(self, build_id: str) -> dict[str, Any]:
        return _operation_from_build(self.repo.get_build(build_id))


    def delete(self, build_id: str) -> None:
        """Dismiss a finished build from the global Operations feed.

        Corpus builds are scholarly artifacts, not disposable job-log rows. The
        generic Operations "Remove" action therefore hides the operation entry
        without deleting the build, its source bindings, or a publication.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") in {"queued", "running"}:
            raise ValueError("Running corpus builds must be cancelled before they can be dismissed from Operations.")
        build["operation_hidden"] = True
        build["operation_hidden_at"] = iso_now()
        self.repo.save_build(build)


    def clear_finished(self) -> int:
        count = 0
        listing = self.repo.list_builds(offset=0, limit=10000)
        for build in listing["items"]:
            if build.get("status") in {"queued", "running"} or build.get("operation_hidden"):
                continue
            build["operation_hidden"] = True
            build["operation_hidden_at"] = iso_now()
            self.repo.save_build(build)
            count += 1
        return count


    def cancel(self, build_id: str) -> dict[str, Any]:
        build = self.repo.get_build(build_id)
        with self._lock:
            self._cancel.add(build_id)
        if build.get("status") in {"queued", "running"}:
            build["cancel_requested"] = True
            self.repo.save_build(build)
        return build


    @_serialize_record_mutation
    def settle_metadata_unresolved(self, build_id: str) -> dict[str, Any]:
        """Ask active enrichment workers to stop scheduling automatic families.

        The currently executing provider call is allowed to reach its bounded read
        deadline; subsequent families settle as explicit review exceptions. Source
        text, topology, and already completed metadata checkpoints are preserved.
        """
        build = self.repo.get_build(build_id)
        if build.get("status") not in {"queued", "running"} or build.get("stage") != "enriching":
            raise ValueError("Metadata can only be settled while enrichment is running.")
        build["metadata_settle_requested"] = True
        build["metadata_settle_requested_at"] = iso_now()
        self.repo.save_build(build)
        return build


    def _cancelled(self, build_id: str) -> bool:
        with self._lock:
            return build_id in self._cancel

