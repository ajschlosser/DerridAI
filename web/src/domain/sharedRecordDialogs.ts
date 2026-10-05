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

import { allRows } from "./corpusCache";
import { api } from "./legacyApi";
import { createRecordDialogs } from "./recordDialogs";
import { recordHistoryVersions } from "./recordHistory";
import { formatTimestamp, localRecordKey } from "./recordTableHelpers";
import { cloneAuditValue, sameValue } from "./recordValues";
import { jsonPretty } from "./reviewPresentation";
import { selectedReviewItems } from "./reviewItems";
import { navigateTo, renderView } from "./sharedNavigation";
import {
  recordDbStatus,
  pendingChangesForRow,
  pendingUpsertRows,
  refreshPresenceForRows,
  removeFromUpsertQueue,
  upsertRows,
} from "./sharedDbPresence";
import {
  applyRecordChanges,
  clearRecordUpdates,
  historyVersionChanges,
  restoreRecordHistoryVersion,
} from "./sharedRecordEditing";
import { label, parseBulkFieldValue, recordFields } from "./sharedRecordHelpers";
import {
  activeFile,
  bulkEditRowsForScope,
  cleanRows,
  download,
  fileJsonl,
  needsReviewItems,
  selectedRecord,
} from "./sharedRecordScopes";
import { tr, trf } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { fileTimers, persistFileNow } from "./sharedWorkspacePersistence";
import { persistPrefs, shell, workspaceDb } from "./sharedWorkspaceStorage";
import { dbUnavailableReason, hasCorpusDb } from "./storeAvailability";

// The record dialogs (merge, bulk field edit, OCR cleanup, record editor, history, upsert queue) over the shared
// state, usable without the legacy runtime. The runtime uses this same instance.
export const recordDialogs = createRecordDialogs({
  state,
  activeFile,
  allRows,
  api,
  applyRecordChanges,
  bulkEditRowsForScope,
  cleanRows,
  clearRecordUpdates,
  cloneAuditValue,
  dbUnavailableReason,
  download,
  fileJsonl,
  fileTimers,
  formatTimestamp,
  hasCorpusDb,
  historyVersionChanges,
  idbDelete: workspaceDb.remove,
  jsonPretty,
  label,
  localRecordKey,
  navigateTo,
  needsReviewItems,
  parseBulkFieldValue,
  pendingChangesForRow,
  pendingUpsertRows,
  persistFileNow,
  persistPrefs,
  recordDbStatus,
  recordFields,
  recordHistoryVersions,
  refreshPresenceForRows,
  removeFromUpsertQueue,
  renderView,
  restoreRecordHistoryVersion,
  sameValue,
  selectedRecord,
  selectedReviewItems: () => selectedReviewItems(state),
  shell,
  tr,
  trf,
  uid: () => crypto.randomUUID(),
  upsertRows,
});
