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

import { createWorksWorkspace } from "./worksWorkspace";
import { workIndex } from "./sharedCorpusAnalytics";
import { refreshPresenceForRows, upsertRows, workDbStatus } from "./sharedDbPresence";
import { navigateTo, syncUrl } from "./sharedNavigation";
import { annotationsWorkspace } from "./sharedAnnotations";
import { providerProfilesService } from "./sharedProviderProfiles";
import { setActiveStore } from "./listPaging";
import { display, label } from "./sharedRecordHelpers";
import { recordPresenters } from "./sharedRecordPresenters";
import { needsReviewItems } from "./sharedRecordScopes";
import { canUse, isResearcher } from "./sharedSession";
import { refreshStores } from "./sharedStores";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import {
  persistAnnotationsPreferences,
  persistSearchPreferences,
  persistVectorPreferences,
  persistWorksPreferences,
} from "./sharedWorkspaceStorage";
import { dbUnavailableReason, hasCorpusDb, recordStores } from "./storeAvailability";
import { refreshStoreWorks } from "./storeWorks";
import { openTouchup } from "./touchupLauncher";
import { searchByMetadata } from "./workspaceActions";
import { workDialogs } from "./sharedWorkDialogs";

// The Works workspace over the shared state, usable without the legacy runtime. The runtime and the Works service
// use this same instance.
export const worksWorkspace = createWorksWorkspace({
  state,
  allAnnotations: annotationsWorkspace.allAnnotations,
  canUse,
  dbUnavailableReason,
  describeResearcherWork: recordPresenters.describeResearcherWork,
  display,
  hasCorpusDb,
  isResearcher,
  label,
  navigateTo,
  needsReviewItems,
  openMixedWorkValuesDialog: workDialogs.openMixedWorkValuesDialog,
  openRemoveWorkModal: workDialogs.openRemoveWorkModal,
  openTouchup,
  openWorkMetadataEditor: workDialogs.openWorkMetadataEditor,
  openWorkMetadataLlmDialog: workDialogs.openWorkMetadataLlmDialog,
  persistAnnotationsPreferences,
  persistSearchPreferences,
  persistVectorPreferences,
  persistWorksPreferences,
  providerProfiles: providerProfilesService.providerProfiles,
  recordStores,
  refreshPresenceForRows,
  refreshServerAnnotations: annotationsWorkspace.refreshServerAnnotations,
  refreshStoreWorks,
  refreshStores,
  searchByMetadata,
  setActiveStore,
  syncUrl,
  tr,
  uid: () => crypto.randomUUID(),
  upsertRows,
  workDbStatus,
  workIndex,
  workInsightMetrics: recordPresenters.workInsightMetrics,
  worksBiblioValue: recordPresenters.worksBiblioValue,
});
