/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
