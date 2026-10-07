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

import { createWorkDialogs } from "./workDialogs";
import { corpusCache, invalidateCorpusCache } from "./corpusCache";
import { startJobPolling, syncJobProgressToasts } from "./jobsActions";
import { providerRequestConfig } from "./providerRequest";
import { cloneAuditValue } from "./recordValues";
import { clearFileDerivedState as clearFileDerivedStateOf } from "./fileDerivedState";
import { operationPresenters } from "./sharedOperationPresenters";
import { workIndex } from "./sharedCorpusAnalytics";
import { persistFileNow } from "./sharedWorkspacePersistence";
import { api } from "./legacyApi";
import { navigateTo, renderView } from "./sharedNavigation";
import { applyRecordChanges } from "./sharedRecordEditing";
import { display, label, parseWorkMetadataValue } from "./sharedRecordHelpers";
import { recordPresenters } from "./sharedRecordPresenters";
import { providerProfilesService } from "./sharedProviderProfiles";
import { refreshStores } from "./sharedStores";
import { tr, trf } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import {
  persistCorpusPreferences,
  persistJobPreferences,
  shell,
} from "./sharedWorkspaceStorage";
import { recordStores } from "./storeAvailability";
import { parseProposedMetadataValue, representativeWorkMetadata } from "./workMetadata";

// The work dialogs over the shared state, usable without the legacy runtime. The runtime destructures this same
// instance.
export const workDialogs = createWorkDialogs({
  state,
  api,
  applyRecordChanges,
  clearFileDerivedState: (fileId: string) => clearFileDerivedStateOf(state, fileId),
  cloneAuditValue,
  corpusCache,
  display,
  jobLabel: operationPresenters.jobLabel,
  invalidateCorpusCache,
  label,
  navigateTo,
  parseProposedMetadataValue,
  parseWorkMetadataValue,
  persistFileNow,
  persistCorpusPreferences,
  persistJobPreferences,
  providerProfile: providerProfilesService.providerProfile,
  providerProfiles: providerProfilesService.providerProfiles,
  providerRequestConfig,
  recordStores,
  refreshStores,
  renderView,
  representativeWorkMetadata,
  shell,
  startJobPolling,
  syncJobProgressToasts,
  tr,
  trf,
  uid: () => crypto.randomUUID(),
  uniqueWorkValues: recordPresenters.uniqueWorkValues,
  workIndex,
  workMetadataControlSpec: recordPresenters.workMetadataControlSpec,
});
