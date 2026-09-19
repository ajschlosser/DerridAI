from __future__ import annotations

import re
from hashlib import sha256
from typing import Any, Iterable

from schemas.schemas import EvidenceInput, EvidenceRecord, ValidationIssue
from utils.generate_citation_strings import generate_citation_strings_from_metadata

TOKEN_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", flags=re.UNICODE)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _document_text(doc: Any) -> str:
    page_content = getattr(doc, "page_content", None)
    metadata = getattr(doc, "metadata", {}) or {}
    return str(page_content if page_content not in (None, "") else metadata.get("text", "") or "").strip()


def stable_evidence_key(doc: Any) -> str:
    metadata = dict(getattr(doc, "metadata", {}) or {})
    record_id = _as_text(metadata.get("record_id"))
    if record_id:
        return f"record:{record_id}"
    material = "|".join([
        _as_text(metadata.get("canonical_work_id")),
        _as_text(metadata.get("work")),
        _as_text(metadata.get("page_start")),
        _as_text(metadata.get("page_end")),
        _document_text(doc),
    ])
    return "content:" + sha256(material.encode("utf-8")).hexdigest()


def deduplicate_documents(docs: Iterable[Any]) -> list[Any]:
    seen: dict[str, Any] = {}
    for doc in docs:
        key = stable_evidence_key(doc)
        if key not in seen:
            seen[key] = doc
            continue
        existing = seen[key]
        methods = {
            str(existing.metadata.get("retrieval_method", "")).strip(),
            str(doc.metadata.get("retrieval_method", "")).strip(),
        }
        existing.metadata["retrieval_method"] = sorted(method for method in methods if method)
    return list(seen.values())


def lexical_overlap_score(query: str, text: str) -> float:
    """Conservative lexical signal with no stopword removal or destructive stemming."""

    q_tokens = [m.group(0).casefold() for m in TOKEN_RE.finditer(query or "")]
    d_tokens = [m.group(0).casefold() for m in TOKEN_RE.finditer(text or "")]
    if not q_tokens or not d_tokens:
        return 0.0
    q_set, d_set = set(q_tokens), set(d_tokens)
    coverage = len(q_set & d_set) / max(1, len(q_set))
    query_cf = (query or "").casefold().strip()
    phrase_bonus = 0.2 if len(query_cf) >= 4 and query_cf in (text or "").casefold() else 0.0
    return min(1.0, coverage + phrase_bonus)


def filter_documents(
    docs: Iterable[Any],
    *,
    languages: list[str] | None = None,
    canonical_work_ids: list[str] | None = None,
) -> list[Any]:
    allowed_languages = {str(x).casefold() for x in (languages or []) if str(x).strip()}
    allowed_works = {str(x).casefold() for x in (canonical_work_ids or []) if str(x).strip()}
    result: list[Any] = []
    for doc in docs:
        metadata = dict(getattr(doc, "metadata", {}) or {})
        language = _as_text(metadata.get("language") or metadata.get("document_language")).casefold()
        work_id = _as_text(metadata.get("canonical_work_id")).casefold()
        if allowed_languages and language and language not in allowed_languages:
            continue
        if allowed_works and work_id not in allowed_works:
            continue
        result.append(doc)
    return result


def validate_evidence_metadata(metadata: dict[str, Any], text: str) -> list[str]:
    warnings: list[str] = []
    if not _as_text(metadata.get("record_id")):
        warnings.append("missing_record_id")
    if not _as_text(metadata.get("work")):
        warnings.append("missing_work")
    if not _as_text(metadata.get("document_author")):
        warnings.append("missing_document_author")
    if metadata.get("page_start") in (None, ""):
        warnings.append("missing_page_start")
    if not text.strip():
        warnings.append("missing_text")
    try:
        if metadata.get("page_start") not in (None, "") and metadata.get("page_end") not in (None, ""):
            if int(metadata["page_end"]) < int(metadata["page_start"]):
                warnings.append("invalid_page_range")
    except (TypeError, ValueError):
        pass
    return warnings


def document_to_evidence_record(doc: Any, *, evidence_tag: str) -> EvidenceRecord:
    metadata = dict(getattr(doc, "metadata", {}) or {})
    text = _document_text(doc)
    inline, full = generate_citation_strings_from_metadata(metadata)
    return EvidenceRecord(
        evidence_tag=evidence_tag,
        record_id=_as_text(metadata.get("record_id")) or stable_evidence_key(doc),
        text=text,
        work=_as_text(metadata.get("work")),
        canonical_work_id=_as_text(metadata.get("canonical_work_id")),
        document_author=_as_text(metadata.get("document_author")),
        speaker=metadata.get("speaker"),
        quoted_speaker=metadata.get("quoted_speaker"),
        position_holder=metadata.get("position_holder"),
        stance=metadata.get("stance"),
        proposition_status=metadata.get("proposition_status"),
        target=metadata.get("target"),
        discourse_role=metadata.get("discourse_role"),
        language=metadata.get("language") or metadata.get("document_language"),
        page_start=metadata.get("page_start"),
        page_end=metadata.get("page_end"),
        year=metadata.get("year"),
        edition=metadata.get("edition"),
        translator=metadata.get("translator"),
        publisher=metadata.get("publisher"),
        inline_citation=inline,
        full_citation=full,
        retrieval_score=metadata.get("retrieval_score"),
        rerank_score=metadata.get("rerank_score"),
        retrieval_method=metadata.get("retrieval_method"),
        provenance_warnings=validate_evidence_metadata(metadata, text),
    )


def input_to_evidence_record(item: EvidenceInput, *, evidence_tag: str) -> EvidenceRecord:
    metadata = item.model_dump(exclude={"text"})
    inline, full = generate_citation_strings_from_metadata(metadata)
    return EvidenceRecord(
        **item.model_dump(),
        evidence_tag=evidence_tag,
        inline_citation=inline,
        full_citation=full,
        provenance_warnings=validate_evidence_metadata(metadata, item.text),
    )


def validation_issues(records: list[EvidenceRecord]) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            severity="warning",
            code=warning,
            record_id=record.record_id,
            message=warning.replace("_", " "),
        )
        for record in records
        for warning in record.provenance_warnings
    ]
