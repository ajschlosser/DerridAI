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

import { isResearcher } from "./sharedSession";
import { navigateTo } from "./sharedNavigation";
import { slimSemanticSource } from "./semanticMap";
import { selectedRecord } from "./sharedRecordScopes";
import { researcherDbRecords } from "./sharedStoreRecords";
import { state } from "./sharedUrlState";

/* eslint-disable-next-line @typescript-eslint/no-explicit-any */
type Any = any;

export function listSemanticMapSources() {
  const seen = new Set<string>();
  const records: Any[] = [];
  const push = (record: Any) => {
    const slim = slimSemanticSource(record);
    if (!slim) return;
    const key =
      slim.id ||
      [slim.work, slim.concepts.join("|"), slim.topics.join("|"), slim.persons.join("|")].join("~");
    if (seen.has(key)) return;
    seen.add(key);
    records.push(slim);
  };
  const current: Any = selectedRecord();
  if (current) push(current);
  if (!isResearcher()) {
    // Respect the bounded semantic-map source limit while walking local files;
    // do not allocate a flattened copy of the entire corpus first.
    for (const file of state.files || []) {
      for (const record of file.records || []) {
        push(record);
        if (records.length >= 400) break;
      }
      if (records.length >= 400) break;
    }
  }
  const pools = isResearcher()
    ? [researcherDbRecords(), state.storeRecords || []]
    : [state.storeRecords || [], researcherDbRecords()];
  for (const pool of pools) {
    for (const record of pool || []) {
      push(record);
      if (records.length >= 400) break;
    }
    if (records.length >= 400) break;
  }
  const focus = current || {};
  return { records, focusId: String(focus.record_id || focus._chroma_id || "") };
}

/** Open a Record reached from a derived semantic-map node when it is in a local file. */
export function openSemanticRecord(recordId: unknown) {
  const wanted = String(recordId || "");
  if (!wanted) return false;
  for (const file of ((state as Any).files || []) as Any[]) {
    const index = (file.records || []).findIndex(
      (record: Any) => String(record.record_id || record._chroma_id || "") === wanted,
    );
    if (index >= 0) {
      navigateTo("record", { fileId: file.id, index });
      return true;
    }
  }
  navigateTo("global");
  return false;
}
