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

import { toast } from "../composables/notifications";
import { createVectorCollectionBridge } from "./vectorCollectionBridge";
import { api } from "./legacyApi";
import { decorateDisabledControls, showAppModal } from "./disabledControls";
import { esc, icon } from "./html";
import { workIndex } from "./sharedCorpusAnalytics";
import { upsertRows } from "./sharedDbPresence";
import { recordDialogs } from "./sharedRecordDialogs";
import { canUse } from "./sharedSession";
import { refreshStores } from "./sharedStores";
import { tr, trf } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { persistVectorPreferences } from "./sharedWorkspaceStorage";
import { recordStores } from "./storeAvailability";

// The vector collection wizard, store-change notification and upsert-queue trigger over the shared state, usable
// without the legacy runtime.
const { openUpsertQueue } = recordDialogs;

const vectorCollectionBridge = createVectorCollectionBridge({
  state,
  workIndex,
  recordStores,
  tr,
  trf,
  esc,
  icon,
  api,
  refreshStores,
  persistVectorPreferences,
  upsertRows,
  decorateDisabledControls,
  showAppModal,
});
export function notifyVectorStoresChanged() {
  return vectorCollectionBridge.notifyVectorStoresChanged();
}
export function openCollectionCreationWizard(options: Record<string, unknown> = {}) {
  return vectorCollectionBridge.openCollectionCreationWizard(options);
}

export function triggerUpsertQueue() {
  return canUse("manageCorpus")
    ? openUpsertQueue()
    : toast(tr("runtime.toast.cannot_manage_dbs"), { tone: "warning" });
}
