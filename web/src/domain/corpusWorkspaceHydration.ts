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

export type CorpusHydrationResult =
  | { status: "ready" | "skipped" }
  | { status: "error"; error: unknown };
type Store = { name: string; count?: number };

/** One initial corpus hydration, shared by concurrent callers. Failed reads remain retryable. */
export function createCorpusWorkspaceHydration(deps: {
  isResearcher: () => boolean;
  hasFiles: () => boolean;
  hasStores: () => boolean;
  refreshStores: () => Promise<unknown>;
  recordStores: () => Store[];
  activeStore: () => string;
  setActiveStore: (name: string) => void;
  exportStore: (name: string) => Promise<unknown[] | null>;
  exportFailure: () => string;
}) {
  let complete = false;
  let inflight: Promise<CorpusHydrationResult> | null = null;
  async function hydrate(): Promise<CorpusHydrationResult> {
    try {
      if (!deps.hasStores()) await deps.refreshStores();
      // Importing a file while discovery runs wins over automatic corpus selection.
      if (deps.hasFiles()) return { status: "skipped" };
      const stores = deps.recordStores().filter((store) => Number(store.count || 0) > 0);
      const target =
        stores.find((store) => store.name === deps.activeStore()) ||
        [...stores].sort((a, b) => Number(b.count || 0) - Number(a.count || 0))[0];
      if (target) {
        deps.setActiveStore(target.name);
        if ((await deps.exportStore(target.name)) === null) throw new Error(deps.exportFailure());
      }
      complete = true;
      return { status: "ready" };
    } catch (error) {
      return { status: "error", error };
    }
  }
  return function ensureCorpusWorkspaceLoaded(): Promise<CorpusHydrationResult> {
    if (deps.isResearcher() || deps.hasFiles() || complete)
      return Promise.resolve({ status: "skipped" });
    if (!inflight)
      inflight = hydrate().finally(() => {
        inflight = null;
      });
    return inflight;
  };
}
