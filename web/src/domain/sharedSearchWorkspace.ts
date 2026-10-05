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

import { createSearchWorkspace } from "./searchWorkspace";
import { allRows } from "./corpusCache";
import { copyCitation } from "./clipboardCopy";
import { openDatabaseCreationFromResearch } from "./databaseCreationRequest";
import { api } from "./legacyApi";
import { reviewKey } from "./evidenceSelection";
import { reviewItemFromKey, selectedReviewItems } from "./reviewItems";
import { toggleSort } from "./recordTableHelpers";
import { recordDialogs } from "./sharedRecordDialogs";
import { dbSearchWhere, label } from "./sharedRecordHelpers";
import { evidenceSelection, searchFacets } from "./sharedSearchSupport";
import { canAccessPage, canUse, hasCapability, isResearcher } from "./sharedSession";
import { refreshStores } from "./sharedStores";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import {
  applyCompressedTableUrlState,
  navigateTo,
  syncUrl,
  urlFromState,
} from "./sharedNavigation";
import { persistPrefs, shell } from "./sharedWorkspaceStorage";
import { recordDbStatus, refreshPresenceForRows } from "./sharedDbPresence";
import { recordStores } from "./storeAvailability";
import { getTableColumns, tableAvailableFields } from "./tableColumns";
import { openTouchup } from "./touchupLauncher";

// The Search workspace over the shared state, usable without the legacy runtime. The runtime and `SearchView` use this
// same instance.
export const searchWorkspace = createSearchWorkspace({
  state,
  allRows,
  api,
  applyCompressedTableUrlState,
  buildSearchFacets: searchFacets.buildSearchFacets,
  canAccessPage,
  canUse,
  clearReviewSelection: evidenceSelection.clearReviewSelection,
  copyCitation,
  dbEvidenceKey: evidenceSelection.dbEvidenceKey,
  dbSearchFilterDescriptors: searchFacets.dbSearchFilterDescriptors,
  dbSearchWhere,
  evidenceIsSelected: evidenceSelection.evidenceIsSelected,
  getTableColumns,
  hasCapability,
  isResearcher,
  label,
  navigateTo,
  openBulkFieldEditor: recordDialogs.openBulkFieldEditor,
  openDatabaseCreationFromResearch,
  openStoreRecordEditor: recordDialogs.openStoreRecordEditor,
  openTouchup,
  persistPrefs,
  recordDbStatus,
  recordStores,
  refreshPresenceForRows,
  refreshStores,
  reviewItemFromKey: (key: unknown) => reviewItemFromKey(state, key),
  reviewKey,
  searchColumnOptions: searchFacets.searchColumnOptions,
  searchFilterDescriptor: searchFacets.searchFilterDescriptor,
  searchMatchReasons: searchFacets.searchMatchReasons,
  searchRecordMatchesFacets: searchFacets.searchRecordMatchesFacets,
  searchRowMatchesFacets: searchFacets.searchRowMatchesFacets,
  searchSimilarity: searchFacets.searchSimilarity,
  searchSuggestions: searchFacets.searchSuggestions,
  selectedEvidenceEntries: evidenceSelection.selectedEvidenceEntries,
  selectedReviewItems: () => selectedReviewItems(state),
  setReviewSelected: evidenceSelection.setReviewSelected,
  shell,
  syncUrl,
  tableAvailableFields,
  toggleDbEvidence: evidenceSelection.toggleDbEvidence,
  toggleSort,
  toggleWorkspaceEvidence: evidenceSelection.toggleWorkspaceEvidence,
  tr,
  uid: () => crypto.randomUUID(),
  urlFromState,
  workspaceEvidenceSelectionKey: evidenceSelection.workspaceEvidenceSelectionKey,
});
