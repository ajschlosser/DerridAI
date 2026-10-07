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

import { createRecordWorkspace } from "./recordWorkspace";
import { copyJsonToClipboard } from "./clipboardCopy";
import { reviewKey } from "./evidenceSelection";
import { api } from "./legacyApi";
import { cleanRecord } from "./recordCleanup";
import { sharedPdfLinking } from "./sharedPdfLinking";
import { annotationsWorkspace } from "./sharedAnnotations";
import { upsertRows } from "./sharedDbPresence";
import { navigateTo, syncUrl } from "./sharedNavigation";
import { recordDialogs } from "./sharedRecordDialogs";
import { applyRecordChanges } from "./sharedRecordEditing";
import { recordPresenters } from "./sharedRecordPresenters";
import { activeFile, selectedRecord } from "./sharedRecordScopes";
import { evidenceSelection } from "./sharedSearchSupport";
import { canAccessPage, canUse, hasCapability, isResearcher } from "./sharedSession";
import { refreshStores } from "./sharedStores";
import { loadStorePage, researcherDbRecords } from "./sharedStoreRecords";
import { tr } from "./sharedTranslate";
import { selectedIndex, state } from "./sharedUrlState";
import {
  persistListPreferences,
  persistRecordViewPreferences,
  shell,
} from "./sharedWorkspaceStorage";
import { hasCorpusDb } from "./storeAvailability";
import { openTouchup } from "./touchupLauncher";
import { searchByMetadata } from "./workspaceActions";

// The Record workspace over the shared state, usable without the legacy runtime. The runtime and the Record view use
// this same instance.
export const sharedRecordWorkspace = createRecordWorkspace({
  state,
  activeFile,
  api,
  applyRecordChanges,
  canAccessPage,
  canUse,
  cleanRecord,
  copyJsonToClipboard,
  dbEvidenceKey: evidenceSelection.dbEvidenceKey,
  evidenceIsSelected: evidenceSelection.evidenceIsSelected,
  hasCapability,
  hasCorpusDb,
  isResearcher,
  linkPdfPage: sharedPdfLinking.linkPdfPage,
  loadStorePage,
  loadedPdfPagesForRecord: sharedPdfLinking.loadedPdfPagesForRecord,
  navigateTo,
  normalizedRecordAnnotation: recordPresenters.normalizedRecordAnnotation,
  openLoadedPdfPage: sharedPdfLinking.openLoadedPdfPage,
  openPdfExplorerWorkspace: sharedPdfLinking.openPdfExplorerWorkspace,
  openRecordHistoryBrowser: recordDialogs.openRecordHistoryBrowser,
  openTouchup,
  pdfDisplayTitle: sharedPdfLinking.pdfDisplayTitle,
  persistPrefs,
  refreshServerAnnotations: annotationsWorkspace.refreshServerAnnotations,
  refreshStores,
  researcherDbRecords,
  reviewKey,
  searchByMetadata,
  selectedIndex,
  selectedRecord,
  setReviewSelected: evidenceSelection.setReviewSelected,
  shell,
  syncUrl,
  toggleDbEvidence: evidenceSelection.toggleDbEvidence,
  toggleWorkspaceEvidence: evidenceSelection.toggleWorkspaceEvidence,
  tr,
  uid: () => crypto.randomUUID(),
  unlinkAllPdfLinks: sharedPdfLinking.unlinkAllPdfLinks,
  unlinkPdfLink: sharedPdfLinking.unlinkPdfLink,
  upsertRows,
  workspaceEvidenceKey: evidenceSelection.workspaceEvidenceKey,
});
