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

import { applyUiTheme } from "./legacyCompat";
import { invalidateCorpusCache } from "./corpusCache";
import { restoreCurrentPdfAsset } from "./pdfAssetPersistence";
import { serializableRecordsFile } from "./recordsFiles";
import { providerProfilesService } from "./sharedProviderProfiles";
import { trf } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { workspaceDb } from "./sharedWorkspaceStorage";
import { createWorkspacePersistence } from "./workspacePersistence";
import { applyDomainPreferenceRecord, DOMAIN_PREFERENCE_KEYS } from "./domainPreferencePersistence";

// Saving and restoring the browser-local workspace over the shared state and database, usable without the legacy
// runtime. The runtime uses this same instance. `fileTimers` is exported because deleting the workspace database must
// cancel the pending debounced file saves.
export const fileTimers = new Map<string, ReturnType<typeof setTimeout>>();

const workspacePersistence = createWorkspacePersistence({
  state,
  trf,
  fileTimers,
  applyUiTheme: (theme: unknown) => applyUiTheme(state, theme),
  ensureProviderProfiles: providerProfilesService.ensureProviderProfiles,
  idbGet: workspaceDb.get,
  idbGetAll: workspaceDb.getAll,
  idbPut: workspaceDb.put,
  invalidateCorpusCache,
  restoreCurrentPdfAsset,
  serializableFile: serializableRecordsFile,
});

export const { persistFileNow, persistFile } = workspacePersistence;

export async function restoreWorkspace() {
  await workspacePersistence.restoreWorkspace();
  try {
    const records = await Promise.all(
      Object.values(DOMAIN_PREFERENCE_KEYS).map((key) => workspaceDb.get("prefs", key)),
    );
    for (const record of records) applyDomainPreferenceRecord(state, record);
  } catch (error) {
    // Legacy workspace preferences have already restored successfully. A
    // domain-record read failure must not make the entire local workspace fail.
    console.warn("Could not restore domain preference records", error);
  }
}
