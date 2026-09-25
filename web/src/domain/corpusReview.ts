import type { CorpusRecord } from "../api/pdfCorpus";

/** Prefer authoritative queue/state values, with legacy-record fallbacks. */
export function recordIssueKinds(record: CorpusRecord) {
  if (Array.isArray(record.review_issue_codes))
    return record.review_issue_codes.filter((code) =>
      ["source", "metadata", "topology"].includes(String(code)),
    );
  const issues: string[] = [];
  if (record.source_quality_issues?.length) issues.push("source");
  if (
    (record.metadata_incomplete_fields || []).length ||
    (record.metadata_review_fields || []).length
  )
    issues.push("metadata");
  const reason = String(record.review_reason || "").toLowerCase();
  if (
    record.needs_review &&
    ["boundary", "merge", "split", "topology"].some((token) => reason.includes(token))
  )
    issues.push("topology");
  return issues;
}
export function recordState(record: CorpusRecord) {
  const authoritative = String(record.review_state || "");
  if (["ready", "metadata", "topology", "source", "accepted", "rejected"].includes(authoritative))
    return authoritative;
  if (record.accepted) return "accepted";
  if (record.rejected) return "rejected";
  const issues = recordIssueKinds(record);
  return issues[0] || "ready";
}
