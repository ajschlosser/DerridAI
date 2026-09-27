/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { MetadataDecisionResult } from "../../../api/corpus";

type I18nValues = Record<string, string | number>;
type Translate = (
  key: string,
  fallbackOrValues?: string | I18nValues,
  values?: I18nValues,
) => string;

/**
 * Summarize a saved batch of reviewer decisions for the status line.
 *
 * Deferred fields (held for a blind second opinion) and derived-memory warnings are
 * reported explicitly: the reviewer must not believe a deferred value was saved.
 */
export function describeDecisionResult(
  result: Pick<MetadataDecisionResult, "changed_fields" | "deferred_fields" | "warnings">,
  tf: Translate,
): { message: string; tone: "error" | "notice" } {
  const parts: string[] = [];
  const saved = result.changed_fields?.length ?? 0;
  const deferred = result.deferred_fields?.length ?? 0;
  if (saved) parts.push(tf("pdf_corpus.llm_suggestions_saved", { count: saved }));
  if (deferred) parts.push(tf("pdf_corpus.metadata_decisions_deferred", { count: deferred }));
  for (const detail of result.warnings ?? []) {
    parts.push(tf("pdf_corpus.metadata_decisions_warning", { detail }));
  }
  return { message: parts.join(" "), tone: result.warnings?.length ? "error" : "notice" };
}
