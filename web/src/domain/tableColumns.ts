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

import { TABLE_DEFAULTS } from "./runtimeConstants";
import { allRows } from "./corpusCache";
import { label, recordFields } from "./sharedRecordHelpers";
import { state } from "./sharedUrlState";

// Which fields a table can show and which columns it currently shows, over the shared state.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function tableAvailableFields(rows: Any, extra: string[] = []): string[] {
  const cachedRows = allRows();
  if (rows === cachedRows) {
    const set = new Set([...extra, ...recordFields().filter((key) => key !== "updates")]);
    return [...set].sort((a, b) => label(a).localeCompare(label(b)));
  }
  const set = new Set(extra);
  for (const row of rows)
    for (const key of Object.keys(row.record || row || {})) if (key !== "updates") set.add(key);
  return [...set].sort((a, b) => label(a).localeCompare(label(b)));
}

export function getTableColumns(table: string, available: string[]): string[] {
  const defaults: string[] = (TABLE_DEFAULTS as Any)[table] || available.slice(0, 8);
  let cols: string[] = Array.isArray(state.tableColumns[table])
    ? state.tableColumns[table].filter((key: string) => available.includes(key))
    : [];
  if (!cols.length) cols = defaults.filter((key) => available.includes(key));
  if (!cols.length) cols = available.slice(0, 8);
  state.tableColumns[table] = cols;
  return cols;
}
