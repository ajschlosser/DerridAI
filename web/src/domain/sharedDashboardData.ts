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
import { createDashboardData } from "./dashboardData";
import { annotationsWorkspace } from "./sharedAnnotations";
import { isResearcher } from "./sharedSession";
import { responseCacheStore } from "./sharedStores";
import { researcherDbRecords } from "./sharedStoreRecords";
import { state } from "./sharedUrlState";
import { api } from "./legacyApi";
import { recordStores } from "./storeAvailability";

// The home dashboard's counts and record preview over the shared state. The runtime uses this same instance.
export const dashboardData = createDashboardData({
  state,
  allRows,
  api,
  isResearcher,
  memoCorpus,
  openAnnotationsWorkspaceRecord: annotationsWorkspace.openAnnotationsWorkspaceRecord,
  recordStores,
  researcherDbRecords,
  responseCacheStore,
});
