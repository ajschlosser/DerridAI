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

// Application lifecycle: importing and closing corpus files, warming up an LLM provider, and the health check run at
// start-up and after Chroma becomes available. Moved verbatim from the legacy runtime; the runtime's state object and
// helpers are passed in as dependencies.
import { apiRequest } from "../api/http";
import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "api"
  | "applyCompressedTableUrlState"
  | "clearFileDerivedState"
  | "decompressUrlState"
  | "defaultProviderProfile"
  | "ensureProviderProfiles"
  | "idbDelete"
  | "invalidateCorpusCache"
  | "isResearcher"
  | "parseJsonl"
  | "persistFileNow"
  | "persistPrefs"
  | "warmupProviderProfile"
  | "refreshProviderStatuses"
  | "refreshStoreWorks"
  | "refreshStores"
  | "renderView"
  | "shell"
  | "stableJsonlFileIdentity"
  | "syncUrl"
  | "tr"
  | "trf"
  | "updateSystemCard";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createAppLifecycle(deps: Deps) {
  const {
    state,
    api,
    applyCompressedTableUrlState,
    clearFileDerivedState,
    decompressUrlState,
    defaultProviderProfile,
    ensureProviderProfiles,
    idbDelete,
    invalidateCorpusCache,
    isResearcher,
    parseJsonl,
    persistFileNow,
    persistPrefs,
    warmupProviderProfile,
    refreshProviderStatuses,
    refreshStoreWorks,
    refreshStores,
    renderView,
    shell,
    stableJsonlFileIdentity,
    syncUrl,
    tr,
    trf,
    updateSystemCard,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  async function warmupConfiguredLlm() {
    return warmupProviderProfile(state.appConfig.default_provider_profile);
  }
  async function importFiles(fileList: Any) {
    if (isResearcher())
      return toast(tr("runtime.toast.researcher_cannot_load"), { tone: "warning" });
    const shareParams = new URLSearchParams(location.search);
    const requestedFileId = shareParams.get("file");
    const requestedUrlState = shareParams.get("ts");
    let first = null,
      total = 0,
      errors = 0,
      alreadyOpen = 0;
    for (const file of [...fileList]) {
      let text: string;
      let name: string = file.name;
      if (/\.zst$/i.test(file.name)) {
        // Archival ledgers (.jsonl.zst) are decoded and evidence-rehydrated by the API.
        try {
          const body = new FormData();
          body.append("file", file);
          const decoded = await apiRequest<{ text: string; filename: string }>(
            "/api/corpus/ledger/decode",
            { method: "POST", body },
          );
          text = decoded.text;
          name = decoded.filename || name.replace(/\.zst$/i, "");
        } catch (error: Any) {
          toast(error.message, { tone: "danger" });
          errors += 1;
          continue;
        }
      } else text = await file.text();
      const parsed = parseJsonl(text);
      if (!parsed.records.length) {
        errors += parsed.errors.length || 1;
        continue;
      }
      const identity = await stableJsonlFileIdentity(text);
      const existing = state.files.find((item: Any) => item.id === identity.id);
      if (existing) {
        first ||= existing.id;
        alreadyOpen += 1;
        total += existing.records.length;
        errors += existing.errors?.length || 0;
        continue;
      }
      const item = {
        ...identity,
        name,
        records: parsed.records,
        errors: parsed.errors,
        dirty: new Set(),
        imported_at: new Date().toISOString(),
      };
      state.files.push(item);
      persistFileNow(item);
      first ||= item.id;
      total += item.records.length;
      errors += item.errors.length;
    }
    if (requestedFileId && state.files.some((item: Any) => item.id === requestedFileId)) {
      state.activeFileId = requestedFileId;
      if (requestedUrlState)
        applyCompressedTableUrlState(decompressUrlState(requestedUrlState), state.view);
    } else if (first) state.activeFileId = first;
    // Always drop derived caches: a file that was already open may have been edited or emptied.
    invalidateCorpusCache();
    persistPrefs();
    shell();
    renderView();
    syncUrl({ replace: true });
    if (alreadyOpen && alreadyOpen === [...fileList].length && !errors) {
      toast(trf("dynamic.already_loaded", { count: total }), { tone: "warning" });
      return;
    }
    toast(
      errors
        ? trf("dynamic.loaded_records_issues", { count: total, issues: errors })
        : trf("dynamic.loaded_records", { count: total }),
      { tone: errors ? "warning" : "success" },
    );
  }
  async function closeFile(id: Any) {
    const f = state.files.find((x: Any) => x.id === id);
    if (!f) return;
    if (
      f.dirty.size &&
      !(await openMessageDialog({
        title: tr("files.close_modified_title"),
        message: trf("files.close_modified_message", { name: f.name }),
        tone: "danger",
        confirmLabel: tr("ui.close_file"),
        cancelLabel: tr("files.keep_open"),
      }))
    )
      return;
    const i = state.files.indexOf(f);
    state.files.splice(i, 1);
    delete state.searches[id];
    delete state.listFilters[id];
    delete state.pages[id];
    delete state.sorts[id];
    clearFileDerivedState(id);
    invalidateCorpusCache();
    idbDelete("files", id).catch((error: Any) =>
      console.error("Could not remove saved file", error),
    );
    if (state.activeFileId === id)
      state.activeFileId = state.files[Math.min(i, state.files.length - 1)]?.id || null;
    persistPrefs();
    shell();
    renderView();
  }
  async function checkHealth() {
    try {
      state.health = await api("/api/health");
      ensureProviderProfiles();
      await refreshProviderStatuses();
    } catch (error: Any) {
      state.health = { ok: false, error: error.message };
      state.providerStatuses = {};
      state.llmStatus = {
        provider: defaultProviderProfile()?.type || "ollama",
        available: false,
        models: [],
        error: error.message,
      };
    }
    updateSystemCard();
    if (state.health?.chroma?.available) {
      try {
        await refreshStores();
        if (isResearcher() && state.activeStore) await refreshStoreWorks(true);
        persistPrefs();
        const active = document.activeElement;
        const userIsEditing =
          active &&
          active !== document.body &&
          ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName);
        if (!userIsEditing) {
          shell();
          renderView();
        }
      } catch (error: Any) {
        console.warn("Initial Chroma collection refresh failed", error);
      }
    }
  }
  return { warmupConfiguredLlm, importFiles, closeFile, checkHealth };
}
