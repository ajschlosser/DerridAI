from __future__ import annotations

from schemas.schemas import EvidenceRecord


def _line(key: str, value) -> str | None:
    if value is None or value == "" or value == []:
        return None
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    return f"{key}={value}"


def generate_context_string(records: list[EvidenceRecord]) -> str:
    """Compact evidence packet: only provenance-bearing fields plus verbatim text."""

    blocks: list[str] = []
    for record in records:
        lines = [
            _line("record_id", record.record_id),
            _line("work", record.work),
            _line("canonical_work_id", record.canonical_work_id),
            _line("document_author", record.document_author),
            _line("speaker", record.speaker),
            _line("quoted_speaker", record.quoted_speaker),
            _line("position_holder", record.position_holder),
            _line("stance", record.stance),
            _line("proposition_status", record.proposition_status),
            _line("target", record.target),
            _line("discourse_role", record.discourse_role),
            _line("language", record.language),
            _line("page_start", record.page_start),
            _line("page_end", record.page_end),
            _line("citation", record.inline_citation),
        ]
        metadata = "\n".join(line for line in lines if line)
        blocks.append(
            f"<BEGIN_EVIDENCE {record.evidence_tag}>\n"
            f"{metadata}\n"
            f"text=\n{record.text.strip()}\n"
            f"<END_EVIDENCE {record.evidence_tag}>"
        )
    return "\n\n".join(blocks)
