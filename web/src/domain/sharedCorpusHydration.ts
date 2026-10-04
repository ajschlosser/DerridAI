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

import { createCorpusWorkspaceHydration } from "./corpusWorkspaceHydration";
import { isResearcher } from "./sharedSession";
import { refreshStores } from "./sharedStores";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { recordStores } from "./storeAvailability";
import { exportStoreJsonl } from "./storeExport";

// Loads the corpus into the workspace on demand (from the first collection when no file is open), over the shared
// state, so the Records view no longer reaches it through `runtime.js`.
export const ensureCorpusWorkspaceLoaded = createCorpusWorkspaceHydration({
  isResearcher,
  hasFiles: () => Boolean(state.files.length),
  hasStores: () => Boolean(state.stores.length),
  refreshStores,
  recordStores,
  activeStore: () => state.activeStore,
  setActiveStore: (name: string) => {
    state.activeStore = name;
  },
  exportStore: (name: string) =>
    exportStoreJsonl({ store: name, loadTab: true, navigate: false, silent: true }),
  exportFailure: () => tr("records.hydration_export_failed"),
});
