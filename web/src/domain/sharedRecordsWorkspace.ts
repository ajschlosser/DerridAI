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

import { createRecordsWorkspace } from "./recordsWorkspace";
import { copyCitation, copyJsonToClipboard } from "./clipboardCopy";
import { pageInfo, setActiveStore, setListFilterValue } from "./listPaging";
import { toggleSort } from "./recordTableHelpers";
import { reviewKey } from "./evidenceSelection";
import { selectedReviewItems } from "./reviewItems";
import { recordDialogs } from "./sharedRecordDialogs";
import { label } from "./sharedRecordHelpers";
import { recordPresenters } from "./sharedRecordPresenters";
import { activeFile, needsReviewItems } from "./sharedRecordScopes";
import { evidenceSelection, searchFacets } from "./sharedSearchSupport";
import { canUse, hasCapability } from "./sharedSession";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { navigateTo, syncUrl, urlFromState } from "./sharedNavigation";
import {
  persistListPreferences,
  persistReviewPreferences,
  refreshShell,
} from "./sharedWorkspaceStorage";
import {
  recordDbStatus,
  refreshPresenceForRows,
  rowsFromReviewSelection,
  upsertRows,
} from "./sharedDbPresence";
import { dbUnavailableReason, hasCorpusDb, recordStores } from "./storeAvailability";
import { getTableColumns, tableAvailableFields } from "./tableColumns";
import { openTouchup } from "./touchupLauncher";

// The Records workspace over the shared state, usable without the legacy runtime. The runtime and `useRecordsWorkspace`
// use this same instance.
export const recordsWorkspace = createRecordsWorkspace({
  state,
  activeFile,
  canUse,
  clearReviewSelection: evidenceSelection.clearReviewSelection,
  copyCitation,
  copyJsonToClipboard,
  dbUnavailableReason,
  evidenceIsSelected: evidenceSelection.evidenceIsSelected,
  getTableColumns,
  hasCapability,
  hasCorpusDb,
  label,
  navigateTo,
  needsReviewItems,
  openBulkFieldEditor: recordDialogs.openBulkFieldEditor,
  openOcrCleanupDialog: recordDialogs.openOcrCleanupDialog,
  openTouchup,
  pageInfo,
  persistListPreferences,
  persistReviewPreferences,
  recordDbStatus,
  recordStores,
  recordsListCell: recordPresenters.recordsListCell,
  refreshPresenceForRows,
  reviewKey,
  rowMatchesListFilters: searchFacets.rowMatchesListFilters,
  rowsFromReviewSelection,
  selectedReviewItems: () => selectedReviewItems(state),
  setActiveStore,
  setListFilterValue,
  setReviewSelected: evidenceSelection.setReviewSelected,
  refreshShell,
  syncUrl,
  tableAvailableFields,
  toggleSort,
  toggleWorkspaceEvidence: evidenceSelection.toggleWorkspaceEvidence,
  tr,
  upsertRows,
  urlFromState,
  workspaceEvidenceSelectionKey: evidenceSelection.workspaceEvidenceSelectionKey,
});
