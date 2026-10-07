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

import { createEvidenceSelection } from "./evidenceSelection";
import { createSearchFacets } from "./searchFacets";
import { filterOpsForField } from "./searchFilterSchema";
import { ragEvidenceRecordPayload } from "./recordPayloads";
import { recordDbStatus } from "./sharedDbPresence";
import { hasCapability } from "./sharedSession";
import { dbSearchWhere, display, label, pages, recordFields } from "./sharedRecordHelpers";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { persistReviewPreferences, refreshShell } from "./sharedWorkspaceStorage";
import { localRecordKey } from "./recordTableHelpers";
import { storeReceipt } from "./storeAvailability";
import { invalidateShellStatusProjection } from "./shellStatusProjection";

// Search facets and evidence selection over the shared state, usable without the legacy runtime. The runtime uses
// these same instances.
export const searchFacets = createSearchFacets({
  tr,
  label,
  display,
  pages,
  recordFields,
  uid: () => crypto.randomUUID(),
  dbSearchWhere,
  filterOpsForField,
  recordDbStatus,
  getSearchFacetFilters: () => state.searchFacetFilters,
});

export const evidenceSelection = createEvidenceSelection({
  state,
  invalidateShellStatus: invalidateShellStatusProjection,
  hasCapability,
  localRecordKey,
  persistPrefs: persistReviewPreferences,
  ragEvidenceRecordPayload,
  recordDbStatus,
  shellRefreshHook: refreshShell,
  storeReceipt,
  tr,
});
