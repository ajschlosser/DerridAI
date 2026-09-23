# Copyright 2026 Aaron John Schlosser, PhD.
"""Schema resolution, autofill-suspension logging, and enrichment run counters.

Which metadata schema a build was started with (a copy on the build, so editing or
deleting the saved schema changes nothing about a running/finished build), which fields
a model or person may set or edit, when autofill is suspended/resumed for a model+field
pair, and the aggregate enrichment metrics/concurrency counters. Moved verbatim out of
PdfCorpusBuildManager as a mixin (see corpus_review_actions.py's module docstring for
why a mixin, not free functions, and corpus_build_lifecycle.py's for why every mixin's
mypy stub block must be wrapped in `if TYPE_CHECKING:`).

_profile_of_build/_profile_for/_edit_model, part of the same originally-planned cluster,
were NOT moved: they use CORPUS_PROFILES/PROFILE_VERSION or RecordMetadataModel, both
defined in corpus_builder.py itself -- the same circular-import shape as
validate_records/_refresh_workflow_fields/create/preview_schema_group.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import settings
from .corpus_metadata import HUMAN_EDITABLE_METADATA_FIELDS
from .corpus_reviewer_helpers import _allowed_for
from .enrichment_ledger import RESUMED, SUSPENDED
from .enrichment_metrics import compute as compute_enrichment_metrics
from .metadata_schema import MetadataSchema, default_schema


class SchemaProfileMixin:
    """Mixin members declared here exist on PdfCorpusBuildManager, not on this mixin itself.

    See corpus_review_actions.py's identical block for the full explanation, including why
    everything below is wrapped in `if TYPE_CHECKING:`.
    """

    if TYPE_CHECKING:
        repo: Any
        _lock: Any
        _ledger: Any
        _schema_cache: dict[str, MetadataSchema]
        _suspended: set[tuple[str, str]]


    def _schema_of_build(self, build: dict[str, Any]) -> MetadataSchema:
        """The schema a build was started with. It is a copy stored on the build, so editing or deleting the saved one changes nothing."""
        build_id = str(build.get("build_id") or "")
        cached = self._schema_cache.get(build_id)
        if cached is not None:
            return cached
        raw = build.get("schema")
        schema = MetadataSchema.model_validate(raw) if isinstance(raw, dict) and raw else default_schema()
        if build_id:
            self._schema_cache[build_id] = schema
        return schema


    def _allowed_fields(self, build_id: str) -> set[str]:
        """Every field a model or a person may set on a record of this build: the fixed ones plus its schema's."""
        return _allowed_for(self._schema_for(build_id))


    def _editable_fields(self, build_id: str) -> set[str]:
        """Fields a person may edit: the fixed editable ones, minus the default schema's, plus this build's schema's."""
        return (HUMAN_EDITABLE_METADATA_FIELDS - {f.name for f in default_schema().fields}) | set(self._schema_for(build_id).field_names())


    def _schema_for(self, build_id: str) -> MetadataSchema:
        if not build_id:
            return default_schema()
        return self._schema_of_build(self.repo.get_build(build_id))


    def _note_suspension(self, model: str, field: str, suspended: bool, reviews: int, accepted: int, build_id: str, run_id: str) -> None:
        """Log the moment autofill is switched off or back on for a model and field, once, not on every value."""
        with self._lock:
            was = (model, field) in self._suspended
            if suspended == was:
                return
            (self._suspended.add if suspended else self._suspended.discard)((model, field))
        self._ledger.append(SUSPENDED if suspended else RESUMED, model=model, field=field, build_id=build_id, run_id=run_id, reviews=reviews, accepted=accepted)


    def enrichment_metrics(self, build_id: str = "", run_id: str = "", arm: str = "", group_by: str = "") -> dict[str, Any]:
        """The ten enrichment measures for the whole ledger, one build, or one run."""
        records = self.repo.load_records(build_id) if build_id else None
        return {
            **compute_enrichment_metrics(self._ledger.events(), records, build_id=build_id, run_id=run_id, arm=arm, group_by=group_by),
            "concurrency": {"limit": max(1, int(settings.enrichment_max_concurrent_runs)), "working": self.active_enrichment_runs()},
        }


    def active_enrichment_runs(self) -> int:
        listing = self.repo.list_builds(offset=0, limit=10000)
        return sum(1 for b in listing["items"] if b.get("status") in {"queued", "running"} and b.get("stage") == "metadata_enrichment_rerun")


    def active_count(self) -> int:
        listing = self.repo.list_builds(offset=0, limit=10000)
        return sum(1 for build in listing["items"] if build.get("status") in {"queued", "running"})

