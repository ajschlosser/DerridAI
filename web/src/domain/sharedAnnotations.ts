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

import { allRows, memoCorpus } from "./corpusCache";
import { createAnnotationsWorkspace } from "./annotationsWorkspace";
import { api } from "./legacyApi";
import { reviewKey } from "./evidenceSelection";
import { applyRecordChanges } from "./sharedRecordEditing";
import { dateKeys } from "./sharedCorpusAnalytics";
import { navigateTo, syncUrl } from "./sharedNavigation";
import { label } from "./sharedRecordHelpers";
import { canUse, hasCapability, isResearcher } from "./sharedSession";
import { refreshStores } from "./sharedStores";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { persistFileNow } from "./sharedWorkspacePersistence";
import {
  persistAnnotationsPreferences,
  persistRecordViewPreferences,
  persistVectorPreferences,
  persistWorksPreferences,
} from "./sharedWorkspaceStorage";
import { recordStores } from "./storeAvailability";
import { reviewItemFromKey } from "./reviewItems";

// The annotations workspace over the shared state, usable without the legacy runtime. The runtime uses this same
// instance.
export const annotationsWorkspace = createAnnotationsWorkspace({
  state,
  allRows,
  api,
  applyRecordChanges,
  canUse,
  dateKeys,
  hasCapability,
  isResearcher,
  label,
  memoCorpus,
  navigateTo,
  persistFileNow,
  persistAnnotationsPreferences,
  persistRecordViewPreferences,
  persistVectorPreferences,
  persistWorksPreferences,
  recordStores,
  refreshStores,
  reviewItemFromKey: (key: unknown) => reviewItemFromKey(state, key),
  reviewKey,
  syncUrl,
  tr,
});
