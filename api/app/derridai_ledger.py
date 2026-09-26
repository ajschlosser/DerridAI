# Copyright 2026 Aaron John Schlosser, PhD.
"""Compact, provenance-preserving JSONL+Zstandard archival ledger support.

This module is intentionally a publication/storage codec.  It does not change
DerridAI's live canonical FieldAssertion model.  The compact representation is
lossless for the declared contract:

* unresolved assertions are retained;
* assertion-backed root projections are removed;
* repeated evidence on superseding assertions is replaced by a pointer to the
  preceding assertion when the evidence is byte-for-byte semantically equal;
* nullable/empty payload members are omitted except where DERRIDAI Core requires
  an explicit null (evaluated assertions with unavailable confidence);
* JSONL is written atomically as a streaming Zstandard frame.

A reader can rehydrate evidence pointers before passing assertions back to the
current in-memory FieldAssertion model.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, MutableMapping

JsonObject = dict[str, Any]
RecordSerializer = Callable[[dict[str, Any]], dict[str, Any]]
RecordValidator = Callable[[dict[str, Any]], list[str]]

_EVALUATION_STATUSES = {
    "not_evaluated",
    "value_supported",
    "no_supported_value",
    "evaluation_failed",
}
_VALUE_STATUSES = {"present", "confirmed_absent", "invalid", "unresolved"}
_AUTHORITY_STATUSES = {"unreviewed", "human_confirmed", "human_override", "disputed"}
_DERIVATION_METHODS = {"deterministic", "model", "human", "inherited", "imported", "other"}


class LedgerValidationError(ValueError):
    """Raised when compaction would produce a lossy or invalid ledger."""


@dataclass(frozen=True, slots=True)
class LedgerWriteResult:
    record_count: int
    content_sha256: str
    archive_sha256: str
    uncompressed_bytes: int
    compressed_bytes: int


def _is_field_assertion(value: Mapping[str, Any]) -> bool:
    """Recognize the current/native FieldAssertion mapping conservatively."""
    return (
        "assertion_id" in value
        and "record_id" in value
        and "field_id" in value
        and "derivation_method" in value
        and "evaluation_status" in value
        and "authority_status" in value
        and "value_status" in value
    )


def _is_empty_json_value(value: Any) -> bool:
    return value is None or value == [] or value == {}


def sparse_json(value: Any) -> Any:
    """Recursively omit null/empty object members without erasing epistemic state.

    DERRIDAI Core requires confidence to be omitted when a field was not
    evaluated, but *present as either a number or explicit null* when evaluation
    occurred.  Therefore evaluated ``confidence: null`` is the one intentional
    exception to the general null-elision rule.

    List positions are preserved.  We prune object members, not arbitrary list
    elements, because positional arrays may have domain meaning.
    """

    if isinstance(value, Mapping):
        assertion = _is_field_assertion(value)
        evaluation_status = str(value.get("evaluation_status") or "") if assertion else ""
        out: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if assertion and key == "confidence":
                if evaluation_status == "not_evaluated":
                    # CORE-ID-017: confidence MUST be omitted.
                    continue
                if raw_value is None:
                    # CORE-ID-017: evaluated-but-unavailable confidence MUST be
                    # represented by an explicit null, not omission.
                    out[key] = None
                    continue
            compacted = sparse_json(raw_value)
            if _is_empty_json_value(compacted):
                continue
            out[key] = compacted

        if assertion and evaluation_status != "not_evaluated" and "confidence" not in out:
            # Normalize old/native assertions that evaluated a field but did not
            # serialize a confidence key.  Explicit null is the Core-compliant
            # representation of "evaluation occurred; confidence unavailable".
            out["confidence"] = None
        return out

    if isinstance(value, list):
        return [sparse_json(item) for item in value]

    return value


def _json_fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _assertion_buckets(record: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    raw = record.get("field_assertions")
    if not isinstance(raw, Mapping):
        return {}
    result: dict[str, list[dict[str, Any]]] = {}
    for raw_field_id, raw_bucket in raw.items():
        if not isinstance(raw_bucket, list):
            continue
        bucket = [item for item in raw_bucket if isinstance(item, dict)]
        result[str(raw_field_id)] = bucket
    return result


def _assertion_projection_names(record: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for bucket in _assertion_buckets(record).values():
        for assertion in bucket:
            name = str(assertion.get("field_name") or "").strip()
            if name:
                names.add(name)
    return names


def _resolve_bucket_evidence(
    assertion_id: str,
    by_id: Mapping[str, Mapping[str, Any]],
    *,
    stack: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    if assertion_id in stack:
        chain = " -> ".join((*stack, assertion_id))
        raise LedgerValidationError(f"Evidence pointer cycle detected: {chain}")
    assertion = by_id.get(assertion_id)
    if assertion is None:
        raise LedgerValidationError(f"Evidence pointer references missing assertion {assertion_id!r}.")

    evidence = assertion.get("evidence")
    pointer = str(assertion.get("evidence_source_assertion_id") or "").strip()
    if evidence not in (None, [], {}) and pointer:
        raise LedgerValidationError(
            f"Assertion {assertion_id!r} contains both inline evidence and an evidence pointer."
        )
    if isinstance(evidence, list) and evidence:
        return copy.deepcopy([item for item in evidence if isinstance(item, dict)])
    if pointer:
        return _resolve_bucket_evidence(pointer, by_id, stack=(*stack, assertion_id))
    return []


def deduplicate_assertion_evidence(record: Mapping[str, Any]) -> dict[str, Any]:
    """Replace repeated evidence on superseding assertions with assertion pointers.

    Deduplication is intentionally conservative: an assertion may point only to
    the assertion it explicitly supersedes, and only when the resolved evidence
    is identical.  We do not coalesce unrelated assertions merely because they
    happen to cite the same block(s).
    """

    out = copy.deepcopy(dict(record))
    raw_buckets = out.get("field_assertions")
    if not isinstance(raw_buckets, MutableMapping):
        return out

    for field_id, raw_bucket in list(raw_buckets.items()):
        if not isinstance(raw_bucket, list):
            continue

        compacted_bucket: list[dict[str, Any]] = []
        by_id: dict[str, dict[str, Any]] = {}

        for raw_assertion in raw_bucket:
            if not isinstance(raw_assertion, dict):
                continue
            assertion = copy.deepcopy(raw_assertion)
            assertion_id = str(assertion.get("assertion_id") or "").strip()
            if not assertion_id:
                compacted_bucket.append(assertion)
                continue

            supersedes_id = str(assertion.get("supersedes_assertion_id") or "").strip()
            evidence = assertion.get("evidence")
            if supersedes_id and isinstance(evidence, list) and evidence and supersedes_id in by_id:
                prior_evidence = _resolve_bucket_evidence(supersedes_id, by_id)
                if _json_fingerprint(evidence) == _json_fingerprint(prior_evidence):
                    assertion.pop("evidence", None)
                    assertion["evidence_source_assertion_id"] = supersedes_id

            compacted_bucket.append(assertion)
            by_id[assertion_id] = assertion

        raw_buckets[field_id] = compacted_bucket

    return out


def rehydrate_evidence_pointers(record: Mapping[str, Any]) -> dict[str, Any]:
    """Expand compact evidence pointers back into native inline ``evidence`` arrays.

    The returned object is suitable for current code that validates FieldAssertion
    with ``extra='forbid'`` and does not yet know about
    ``evidence_source_assertion_id``.
    """

    out = copy.deepcopy(dict(record))
    raw_buckets = out.get("field_assertions")
    if not isinstance(raw_buckets, MutableMapping):
        return out

    for field_id, raw_bucket in list(raw_buckets.items()):
        if not isinstance(raw_bucket, list):
            continue
        by_id = {
            str(item.get("assertion_id")): item
            for item in raw_bucket
            if isinstance(item, dict) and item.get("assertion_id")
        }
        hydrated: list[dict[str, Any]] = []
        for raw_assertion in raw_bucket:
            if not isinstance(raw_assertion, dict):
                continue
            assertion = copy.deepcopy(raw_assertion)
            pointer = str(assertion.get("evidence_source_assertion_id") or "").strip()
            if pointer:
                assertion["evidence"] = _resolve_bucket_evidence(pointer, by_id)
                assertion.pop("evidence_source_assertion_id", None)
            hydrated.append(assertion)
        raw_buckets[field_id] = hydrated

    return out


def _validate_assertions(record: Mapping[str, Any], *, compact: bool) -> list[str]:
    errors: list[str] = []
    buckets = _assertion_buckets(record)
    all_assertion_ids: dict[str, str] = {}

    for field_id, bucket in buckets.items():
        by_id: dict[str, dict[str, Any]] = {}
        for index, assertion in enumerate(bucket):
            assertion_id = str(assertion.get("assertion_id") or "").strip()
            location = f"field_assertions[{field_id!r}][{index}]"
            if not assertion_id:
                errors.append(f"{location}: assertion_id is required")
                continue
            prior_field = all_assertion_ids.get(assertion_id)
            if prior_field is not None:
                errors.append(
                    f"{location}: duplicate assertion_id {assertion_id!r} also appears under {prior_field!r}"
                )
            all_assertion_ids[assertion_id] = field_id
            by_id[assertion_id] = assertion

            if str(assertion.get("record_id") or "") != str(record.get("record_id") or ""):
                errors.append(f"{location}: record_id does not match enclosing record")
            if str(assertion.get("field_id") or "") != field_id:
                errors.append(f"{location}: field_id does not match assertion bucket")

            derivation = str(assertion.get("derivation_method") or "")
            evaluation = str(assertion.get("evaluation_status") or "")
            authority = str(assertion.get("authority_status") or "")
            value_status = str(assertion.get("value_status") or "")
            if derivation not in _DERIVATION_METHODS:
                errors.append(f"{location}: invalid derivation_method {derivation!r}")
            if evaluation not in _EVALUATION_STATUSES:
                errors.append(f"{location}: invalid evaluation_status {evaluation!r}")
            if authority not in _AUTHORITY_STATUSES:
                errors.append(f"{location}: invalid authority_status {authority!r}")
            if value_status not in _VALUE_STATUSES:
                errors.append(f"{location}: invalid value_status {value_status!r}")

            if evaluation == "not_evaluated":
                if "confidence" in assertion:
                    errors.append(f"{location}: confidence must be omitted when not evaluated")
            elif evaluation in _EVALUATION_STATUSES:
                if "confidence" not in assertion:
                    errors.append(f"{location}: evaluated assertion must include confidence number or null")
                else:
                    confidence = assertion.get("confidence")
                    if confidence is not None and not (
                        isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and 0.0 <= float(confidence) <= 1.0
                    ):
                        errors.append(f"{location}: confidence must be null or a number in [0, 1]")

            pointer = str(assertion.get("evidence_source_assertion_id") or "").strip()
            evidence = assertion.get("evidence")
            if compact and pointer and evidence not in (None, [], {}):
                errors.append(f"{location}: compact assertion cannot contain both evidence and evidence pointer")

        if compact:
            # Resolve every pointer after the full bucket is indexed.  We also
            # require a pointer to stay within the same field bucket, preventing
            # accidental cross-field evidence substitution.
            for assertion in bucket:
                if not isinstance(assertion, dict):
                    continue
                pointer = str(assertion.get("evidence_source_assertion_id") or "").strip()
                if not pointer:
                    continue
                if pointer not in by_id:
                    errors.append(
                        f"field_assertions[{field_id!r}]: evidence pointer {pointer!r} does not resolve in this field bucket"
                    )
                    continue
                try:
                    _resolve_bucket_evidence(str(assertion.get("assertion_id") or ""), by_id)
                except LedgerValidationError as exc:
                    errors.append(str(exc))

    selected = record.get("current_field_assertions")
    if selected is not None and not isinstance(selected, Mapping):
        errors.append("current_field_assertions must be an object when present")
    elif isinstance(selected, Mapping):
        for raw_field_id, raw_assertion_id in selected.items():
            field_id = str(raw_field_id)
            assertion_id = str(raw_assertion_id)
            bucket_ids = {
                str(item.get("assertion_id"))
                for item in buckets.get(field_id, [])
                if isinstance(item, dict) and item.get("assertion_id")
            }
            if assertion_id not in bucket_ids:
                errors.append(
                    f"current_field_assertions[{field_id!r}] points to missing assertion {assertion_id!r}"
                )

    return errors


def validate_compact_record(record: Mapping[str, Any]) -> list[str]:
    """Validate the compact archival form against core provenance invariants."""

    errors: list[str] = []
    record_id = str(record.get("record_id") or "").strip()
    source_document_id = str(record.get("source_document_id") or "").strip()
    if not record_id:
        errors.append("record_id is required")
    if not source_document_id:
        errors.append("source_document_id is required")
    text = record.get("text")
    if not isinstance(text, str) or not text.strip():
        errors.append("text is required")

    spans = record.get("source_spans")
    if not isinstance(spans, list) or not spans:
        errors.append("one or more source_spans are required")
    else:
        for index, span in enumerate(spans):
            if not isinstance(span, Mapping):
                errors.append(f"source_spans[{index}] must be an object")
                continue
            span_source = str(span.get("source_document_id") or "").strip()
            if not span_source:
                errors.append(f"source_spans[{index}].source_document_id is required")
            elif source_document_id and span_source != source_document_id:
                errors.append(
                    f"source_spans[{index}].source_document_id does not match Record source_document_id"
                )

    errors.extend(_validate_assertions(record, compact=True))
    return errors


def compact_public_record(
    record: dict[str, Any],
    *,
    serialize_record: RecordSerializer,
    validate_record: RecordValidator | None = None,
) -> dict[str, Any]:
    """Create the lossless compact publication representation for one Record."""

    public = serialize_record(record)

    # Validate the native/public assertion representation before compaction so
    # compaction cannot hide an already-invalid epistemic state.
    native_assertion_errors = _validate_assertions(public, compact=False)
    if native_assertion_errors:
        raise LedgerValidationError("; ".join(native_assertion_errors[:12]))

    if validate_record is not None:
        schema_errors = validate_record(public)
        if schema_errors:
            raise LedgerValidationError("; ".join(schema_errors[:12]))

    # The root materialized values are a read-model projection.  The complete
    # assertion history and current-field selector remain canonical in the
    # archival ledger.
    compact = copy.deepcopy(public)
    for field_name in _assertion_projection_names(compact):
        compact.pop(field_name, None)

    compact = deduplicate_assertion_evidence(compact)
    compact = sparse_json(compact)

    errors = validate_compact_record(compact)
    if errors:
        raise LedgerValidationError("; ".join(errors[:12]))
    return compact


def _import_zstandard() -> Any:
    try:
        import zstandard as zstd  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "Zstandard support requires the 'zstandard' package. "
            "Add zstandard>=0.23,<1 to api/requirements.txt."
        ) from exc
    return zstd


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl_zst(
    path: str | Path,
    records: Iterable[dict[str, Any]],
    *,
    serialize_record: RecordSerializer,
    validate_record: RecordValidator | None = None,
    compression_level: int = 10,
) -> LedgerWriteResult:
    """Atomically stream compact JSONL directly into a Zstandard archive."""

    zstd = _import_zstandard()
    target = Path(path)
    if not str(target.name).endswith(".jsonl.zst"):
        raise ValueError("DERRIDAI archival ledger path must end in .jsonl.zst")
    target.parent.mkdir(parents=True, exist_ok=True)

    content_hasher = hashlib.sha256()
    uncompressed_bytes = 0
    record_count = 0

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as raw:
            compressor = zstd.ZstdCompressor(
                level=int(compression_level),
                write_checksum=True,
                write_content_size=False,
            )
            with compressor.stream_writer(raw, closefd=False) as compressed:
                for record in records:
                    public = compact_public_record(
                        record,
                        serialize_record=serialize_record,
                        validate_record=validate_record,
                    )
                    line = (
                        json.dumps(
                            public,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        + "\n"
                    ).encode("utf-8")
                    content_hasher.update(line)
                    uncompressed_bytes += len(line)
                    compressed.write(line)
                    record_count += 1
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(tmp, target)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass

    return LedgerWriteResult(
        record_count=record_count,
        content_sha256=content_hasher.hexdigest(),
        archive_sha256=_sha256_file(target),
        uncompressed_bytes=uncompressed_bytes,
        compressed_bytes=target.stat().st_size,
    )


def iter_jsonl_zst(
    path: str | Path,
    *,
    rehydrate_evidence: bool = True,
) -> Iterator[dict[str, Any]]:
    """Stream-decompress a ``.jsonl.zst`` ledger one Record at a time."""

    zstd = _import_zstandard()
    source = Path(path)
    with source.open("rb") as raw:
        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(raw, closefd=False) as reader:
            text = io.TextIOWrapper(reader, encoding="utf-8", newline="")
            try:
                for line_number, line in enumerate(text, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise LedgerValidationError(
                            f"Invalid JSON on decompressed JSONL line {line_number}: {exc}"
                        ) from exc
                    if not isinstance(record, dict):
                        raise LedgerValidationError(
                            f"JSONL line {line_number} is not a Record object."
                        )
                    errors = validate_compact_record(record)
                    if errors:
                        raise LedgerValidationError(
                            f"Invalid compact Record on line {line_number}: "
                            + "; ".join(errors[:12])
                        )
                    if rehydrate_evidence:
                        record = rehydrate_evidence_pointers(record)
                    yield record
            finally:
                # Detach so TextIOWrapper does not attempt a second close of the
                # context-managed Zstandard stream reader.
                try:
                    text.detach()
                except (ValueError, OSError):
                    pass


def read_jsonl_zst(
    path: str | Path,
    *,
    rehydrate_evidence: bool = True,
) -> list[dict[str, Any]]:
    """Convenience wrapper for callers that explicitly want all Records in RAM."""

    return list(iter_jsonl_zst(path, rehydrate_evidence=rehydrate_evidence))


def iter_ledger_records(
    path: str | Path,
    *,
    rehydrate_evidence: bool = True,
) -> Iterator[dict[str, Any]]:
    """Read either the new Zstd ledger or a legacy plaintext JSONL publication.

    This compatibility reader allows existing immutable ``.jsonl`` publications
    to remain readable while all newly written publications use ``.jsonl.zst``.
    """

    source = Path(path)
    if source.name.endswith(".jsonl.zst"):
        yield from iter_jsonl_zst(source, rehydrate_evidence=rehydrate_evidence)
        return

    if not source.name.endswith(".jsonl"):
        raise ValueError("Ledger path must end in .jsonl.zst or legacy .jsonl")

    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LedgerValidationError(
                    f"Invalid JSON on legacy JSONL line {line_number}: {exc}"
                ) from exc
            if not isinstance(record, dict):
                raise LedgerValidationError(
                    f"Legacy JSONL line {line_number} is not a Record object."
                )
            yield record