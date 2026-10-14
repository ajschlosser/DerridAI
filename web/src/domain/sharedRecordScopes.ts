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

import { toast } from "../composables/notifications";
import { allRows, memoCorpus } from "./corpusCache";
import { reviewKey } from "./evidenceSelection";
import { selectedReviewItems } from "./reviewItems";
import { applyRecordChanges, commitRecordFiles } from "./sharedRecordEditing";
import { renderView } from "./sharedNavigation";
import { trf } from "./sharedTranslate";
import { selectedIndex, state } from "./sharedUrlState";
import { shell } from "./sharedWorkspaceStorage";
import { stripLigaturesAndArtifacts } from "./textCleanup";

/* eslint-disable @typescript-eslint/no-explicit-any */
// Active file, scoped row sets, OCR cleanup and file download helpers over the shared state, usable without the legacy
// runtime. The runtime uses these same functions.
export const activeFile = (): any =>
  state.files.find((f: any) => f.id === state.activeFileId) || null;
export const selectedRecord = (): any => {
  const f = activeFile();
  return f?.records[selectedIndex(f)] || null;
};

export function needsReviewItems(rows: any[] | null = null) {
  if (rows === null) {
    return memoCorpus("needs-review-items", () =>
      allRows()
        .filter((row: any) => row.record.needs_review === true)
        .map((row: any) => ({ ...row, key: reviewKey(row.file, row.index) })),
    );
  }
  return rows
    .filter((row: any) => row.record.needs_review === true)
    .map((row: any) => ({ ...row, key: reviewKey(row.file, row.index) }));
}

export function bulkEditRowsForScope(scope: string) {
  if (scope === "selected") return selectedReviewItems(state);
  if (scope === "active") {
    const file = activeFile();
    return file
      ? file.records.map((record: any, index: number) => ({
          file,
          record,
          index,
          key: reviewKey(file, index),
        }))
      : [];
  }
  if (scope === "work") {
    const selected = selectedRecord();
    const work = selected?.work;
    return work ? allRows().filter((row: any) => row.record.work === work) : [];
  }
  return allRows();
}

export function cleanRows(rows: any[]) {
  const batchId = crypto.randomUUID();
  let recordsChanged = 0,
    fieldsChanged = 0;
  const touchedFiles = new Set<any>();
  for (const row of rows) {
    const current = row.file.records[row.index];
    const cleaned = stripLigaturesAndArtifacts(current?.text);
    if (!cleaned.changed) continue;
    const n = applyRecordChanges(
      row.file,
      row.index,
      { text: cleaned.text },
      { source: "ocr_cleanup", batchId, deferCommit: true },
    );
    if (n) {
      recordsChanged++;
      fieldsChanged += n;
      touchedFiles.add(row.file);
    }
  }
  commitRecordFiles(touchedFiles);
  shell();
  renderView();
  toast(trf("dynamic.cleaned_records", { records: recordsChanged, changes: fieldsChanged }), {
    tone: "success",
  });
}

export function downloadBlob(blob: Blob, name: string) {
  const u = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = u;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 500);
}

export function download(name: string, text: string) {
  downloadBlob(new Blob([text], { type: "application/x-ndjson" }), name);
}

export function fileJsonl(f: any) {
  return f.records.map((r: any) => JSON.stringify(r)).join("\n") + "\n";
}
