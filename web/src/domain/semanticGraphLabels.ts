// Copyright 2026 Aaron John Schlosser, PhD.

type Translate = (key: string) => string;

export const SEMANTIC_INDEX_PAGE = 50;

export function relationLabel(predicate: string): string {
  return String(predicate || "").replaceAll("_", " ");
}

/** Reviewer authority for a semantic relation; anything not confirmed or disputed reads as unreviewed. */
export function authorityLabel(status: string, t: Translate): string {
  if (status === "human_confirmed") return t("pdf_corpus.semantic_graph_authority_human_confirmed");
  if (status === "disputed") return t("pdf_corpus.semantic_graph_authority_disputed");
  return t("pdf_corpus.semantic_graph_authority_unreviewed");
}
