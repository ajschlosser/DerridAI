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

import { bindJobsState } from "../state/jobsState";
import { bindWorkspaceGroups } from "../state/workspaceState";
import { createDbPresenceUpsert } from "./dbPresenceUpsert";
import { allRows, corpusCache, recordFingerprint } from "./corpusCache";
import { api } from "./legacyApi";
import { notifyVectorStoresChanged, refreshOperationsPanelOnly } from "./operationHooks";
import { startJobPolling, syncJobProgressToasts } from "./jobsActions";
import { upsertRecordPayload } from "./recordPayloads";
import { upsertAuditDelta } from "./recordHistory";
import { formatTimestamp, localRecordKey } from "./recordTableHelpers";
import { reviewItemFromKey, selectedReviewItems } from "./reviewItems";
import { workIndex } from "./sharedCorpusAnalytics";
import { tr, trf } from "./sharedTranslate";
import { persistPrefs } from "./sharedWorkspaceStorage";
import {
  candidateChromaIds,
  corpusStoreExists,
  dbUnavailableReason,
  hasCorpusDb,
  storeReceipt,
} from "./storeAvailability";

// Database presence and the upsert queue over the shared state, usable without the legacy runtime. The runtime uses
// this same instance. Database upserts also inspect and append background jobs, so bind the jobs slice explicitly;
// bindWorkspaceGroups intentionally excludes it.
const state = bindJobsState(bindWorkspaceGroups({}));

export const {
  recordDbStatus,
  workDbStatus,
  refreshPresenceForRows,
  updateDbStatusElements,
  ignoredFingerprint,
  pendingUpsertRows,
  pendingChangesForRow,
  removeFromUpsertQueue,
  buildUpsertItems,
  upsertRows,
  rowsFromReviewSelection,
} = createDbPresenceUpsert({
  state,
  corpusCache,
  allRows,
  api,
  candidateChromaIds,
  corpusStoreExists,
  dbUnavailableReason,
  formatTimestamp,
  hasCorpusDb,
  localRecordKey,
  notifyVectorStoresChanged,
  persistPrefs,
  recordFingerprint,
  refreshOperationsPanelOnly,
  reviewItemFromKey: (key: unknown) => reviewItemFromKey(state, key),
  selectedReviewItems: () => selectedReviewItems(state),
  startJobPolling,
  storeReceipt,
  syncJobProgressToasts,
  tr,
  trf,
  upsertAuditDelta,
  upsertRecordPayload,
  workIndex,
});
