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

import { deleteAllDerridaiBrowserState as deleteAllDerridaiBrowserStateCompat } from "../services/workspaceDb";
import { bindJobsState } from "../state/jobsState";
import { bindWorkspaceGroups } from "../state/workspaceState";
import { createBackupWorkspace } from "./backupWorkspace";
import { cancelPendingPrefs } from "./prefsPersistence";
import { serializableRecordsFile } from "./recordsFiles";
import { providerProfilesService } from "./sharedProviderProfiles";
import { tr, trf } from "./sharedTranslate";
import { cancelPendingFileWrites, persistFileNow } from "./sharedWorkspacePersistence";
import {
  cancelPendingDomainPreferences,
  workspaceDb,
  workspacePrefs,
} from "./sharedWorkspaceStorage";

// Dropping the browser-local workspace, and full backup / restore, over the shared state and database, usable without
// the legacy runtime. Backup/restore needs both the workspace groups and background-job state because active jobs block
// destructive snapshot operations. These accessors point at the same shared stores the runtime uses.
const backupState = bindJobsState(bindWorkspaceGroups({}));

export async function deleteWorkspaceDatabase() {
  cancelPendingPrefs();
  cancelPendingDomainPreferences();
  cancelPendingFileWrites();
  await workspaceDb.drop();
}

export const deleteAllDerridaiBrowserState = () =>
  deleteAllDerridaiBrowserStateCompat(deleteWorkspaceDatabase);

export const { backupContainsCredentials, downloadFullBackup, restoreFullBackup } =
  createBackupWorkspace({
    state: backupState,
    deleteWorkspaceDatabase,
    idbPut: workspaceDb.put,
    persistFileNow,
    providerProfiles: providerProfilesService.providerProfiles,
    serializableFile: serializableRecordsFile,
    tr,
    trf,
    workspacePrefs,
  });
