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

import { allRows, invalidateCorpusCache } from "./corpusCache";
import { createRecordEditing } from "./recordEditing";
import { cloneAuditValue, sameValue } from "./recordValues";
import { renderView } from "./sharedNavigation";
import { label } from "./sharedRecordHelpers";
import { tr, trf } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { persistFile } from "./sharedWorkspacePersistence";
import { shell } from "./sharedWorkspaceStorage";

// Record editing and history over the shared state, usable without the legacy runtime. The runtime uses this same
// instance.
export const {
  applyRecordChanges,
  clearRecordUpdates,
  clearAllUpdates,
  historyVersionChanges,
  restoreRecordHistoryVersion,
} = createRecordEditing({
  state,
  allRows,
  cloneAuditValue,
  invalidateCorpusCache,
  label,
  persistFile,
  renderView,
  sameValue,
  shell,
  tr,
  trf,
  uid: () => crypto.randomUUID(),
});
