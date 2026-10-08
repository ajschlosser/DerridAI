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
import { esc } from "./html";
import { invalidateCorpusCache } from "./corpusCache";
import { cloneAuditValue } from "./recordValues";
import { createRecordSubsets } from "./recordSubsets";
import { showAppModal } from "./disabledControls";
import { recordDialogs } from "./sharedRecordDialogs";
import { label } from "./sharedRecordHelpers";
import { activeFile, download, downloadBlob, fileJsonl } from "./sharedRecordScopes";
import { canUse } from "./sharedSession";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { navigateTo } from "./sharedNavigation";
import { persistFileNow } from "./sharedWorkspacePersistence";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Record-file commands for the Records view (subset files, merge, export) over the shared state, so Vue code no longer
// reaches them through the runtime. The runtime keeps no copy.
export const {
  subsetSources,
  subsetSourceRecords,
  subsetFields,
  defaultSubsetName,
  createSubsetFile,
} = createRecordSubsets({
  state: state as unknown as Parameters<typeof createRecordSubsets>[0]["state"],
  cloneAuditValue: cloneAuditValue as <T>(value: T) => T,
  downloadBlob,
  invalidateCorpusCache,
  label,
  navigateTo,
  persistFileNow,
  uid: () => crypto.randomUUID(),
});

export function triggerMerge() {
  return canUse("manageCorpus")
    ? recordDialogs.openMergeDialog()
    : toast(tr("runtime.toast.cannot_merge_files"), { tone: "warning" });
}

export function triggerExport() {
  return canUse("manageCorpus")
    ? exportMenu()
    : toast(tr("runtime.toast.cannot_export"), { tone: "warning" });
}

function exportMenu(): void {
  const dialog = document.createElement("dialog");
  dialog.innerHTML = `<div class="dh"><h2 style="margin:0;font-size:16px">${esc(tr("export.title"))}</h2><button class="btn" data-close>${esc(tr("ui.close"))}</button></div><div class="db"><div class="tools"><button class="btn" data-export="current">${esc(tr("export.current"))}</button><button class="btn" data-export="changed">${esc(tr("export.changed"))}</button><button class="btn" data-export="all">${esc(tr("export.all"))}</button><button class="btn" data-export="aggregate">${esc(tr("export.aggregate"))}</button><button class="btn" data-export="both">${esc(tr("export.changed_aggregate"))}</button></div></div>`;
  document.body.appendChild(dialog);
  showAppModal(dialog);
  const close = () => {
    dialog.close();
    dialog.remove();
  };
  (dialog.querySelector("[data-close]") as HTMLElement).onclick = close;
  dialog.querySelectorAll<HTMLElement>("[data-export]").forEach((button) => {
    button.onclick = () => {
      exportFiles(button.dataset.export || "");
      close();
    };
  });
}

function exportFiles(kind: string) {
  const current = activeFile();
  const changed = state.files.filter((f: Loose) => f.dirty.size);
  if (kind === "current" && current) download(current.name, fileJsonl(current));
  if (kind === "changed")
    changed.forEach((f: Loose, i: number) =>
      setTimeout(() => download(f.name, fileJsonl(f)), i * 160),
    );
  if (kind === "all")
    state.files.forEach((f: Loose, i: number) =>
      setTimeout(() => download(f.name, fileJsonl(f)), i * 160),
    );
  if (kind === "aggregate" || kind === "both")
    download(
      "derridai-aggregate.jsonl",
      state.files
        .flatMap((f: Loose) => f.records)
        .map((r: Loose) => JSON.stringify(r))
        .join("\n") + "\n",
    );
  if (kind === "both")
    changed.forEach((f: Loose, i: number) =>
      setTimeout(() => download(f.name, fileJsonl(f)), 250 + i * 160),
    );
}
