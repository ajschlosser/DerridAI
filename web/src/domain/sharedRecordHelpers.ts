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

import { allRows, corpusCache } from "./corpusCache";
import { createFieldFormatting } from "./fieldFormatting";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";

// Field formatting and small record helpers over the shared state, usable without the legacy runtime. The runtime
// uses these same functions.
export const { label, display, normalizeRagGrade, parseBulkFieldValue, parseWorkMetadataValue } =
  createFieldFormatting({ tr });

export function pages(r: Record<string, unknown>) {
  if (r.page_start == null && r.page_end == null) return "—";
  return r.page_end != null && r.page_end !== r.page_start
    ? `${display(r.page_start)}–${display(r.page_end)}`
    : display(r.page_start);
}

export function recordFields(): string[] {
  if (corpusCache.fields) return corpusCache.fields;
  const set = new Set<string>();
  allRows().forEach((x: { record: Record<string, unknown> }) =>
    Object.keys(x.record).forEach((k) => set.add(k)),
  );
  corpusCache.fields = [...set].sort();
  return corpusCache.fields;
}

export function dbSearchWhere() {
  return Object.fromEntries(
    Object.entries(state.dbSearchWhere || {}).filter(
      ([, value]) => String(value ?? "").trim() !== "",
    ),
  );
}
