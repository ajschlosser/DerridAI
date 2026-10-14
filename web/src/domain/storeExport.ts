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
import { api } from "./legacyApi";
import { invalidateCorpusCache } from "./corpusCache";
import {
  hideOperationProgress,
  showOperationProgress,
  updateOperationProgress,
} from "./operationProgressHooks";
import { cloneAuditValue } from "./recordValues";
import { download } from "./sharedRecordScopes";
import { navigateTo } from "./sharedNavigation";
import { tr, trf } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { persistFileNow } from "./sharedWorkspacePersistence";
import { persistCorpusPreferences } from "./sharedWorkspaceStorage";

/* eslint-disable @typescript-eslint/no-explicit-any */
type Loose = Record<string, any>;
type ExportStoreOptions = {
  store?: string;
  work?: string | null;
  downloadFile?: boolean;
  loadTab?: boolean;
  navigate?: boolean;
  silent?: boolean;
};

// Exports a Chroma collection (or one work of it) as JSONL: downloads it and/or loads it as a clean workspace file
// tagged `imported_from_chroma`. Over the shared state, so Vue code and the runtime use the same function.
export async function exportStoreJsonl({
  store = state.activeStore,
  work = null,
  downloadFile = false,
  loadTab = false,
  navigate = true,
  silent = false,
}: ExportStoreOptions = {}) {
  if (!store)
    return silent ? null : toast(tr("records.toast.select_collection"), { tone: "warning" });
  const params = new URLSearchParams();
  if (work) params.set("work", work);
  const op = silent ? null : showOperationProgress(`Exporting ${store}`, 1);
  try {
    if (op)
      updateOperationProgress(
        op,
        0,
        1,
        work ? `Reading work: ${work}` : "Reading complete collection…",
      );
    const payload = await api(
      `/api/stores/${encodeURIComponent(store)}/export${params.toString() ? `?${params}` : ""}`,
    );
    const records = payload.records || [];
    const suffix = work
      ? `-${String(work)
          .replace(/[^a-z0-9]+/gi, "-")
          .replace(/^-|-$/g, "")}`
      : "";
    const name = `${store}${suffix}.jsonl`;
    const jsonl =
      records.map((record: Loose) => JSON.stringify(record)).join("\n") +
      (records.length ? "\n" : "");
    if (downloadFile) download(name, jsonl);
    if (loadTab) {
      const file = {
        id: crypto.randomUUID(),
        name,
        records: records.map((record: Loose) => cloneAuditValue(record)),
        errors: [],
        dirty: new Set(),
        imported_at: new Date().toISOString(),
        imported_from_chroma: store,
      };
      // Reloading the same collection/work replaces its clean earlier copy instead of duplicating every record.
      const previous = state.files.findIndex(
        (item: Loose) =>
          item.imported_from_chroma === store &&
          item.name === name &&
          !(item.dirty && item.dirty.size),
      );
      if (previous >= 0) {
        file.id = state.files[previous].id;
        state.files.splice(previous, 1, file);
      } else state.files.push(file);
      invalidateCorpusCache(file.id, true);
      await persistFileNow(file);
      state.activeFileId = file.id;
      persistCorpusPreferences();
      if (navigate) navigateTo("list", { fileId: file.id });
    }
    if (op) {
      updateOperationProgress(op, 1, 1, `${records.length.toLocaleString()} records exported`);
      setTimeout(() => hideOperationProgress(op), 600);
    }
    if (!loadTab && !silent)
      toast(
        trf("dynamic.exported_records", {
          count: records.length.toLocaleString(),
          collection: store,
        }),
        { tone: "success" },
      );
    return records;
  } catch (error: any) {
    if (op) {
      updateOperationProgress(op, 0, 1, `Failed: ${error.message}`);
      setTimeout(() => hideOperationProgress(op), 1800);
    }
    if (!silent)
      toast(trf("runtime.toast.chroma_export_failed", { detail: error.message }), {
        tone: "danger",
      });
    return null;
  }
}
