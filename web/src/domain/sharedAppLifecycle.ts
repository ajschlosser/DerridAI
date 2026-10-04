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

import { createAppLifecycle } from "./appLifecycle";
import { api } from "./legacyApi";
import { renderView } from "./sharedNavigation";
import { providerProfilesService, warmupProviderProfile } from "./sharedProviderProfiles";
import { isResearcher } from "./sharedSession";
import { refreshStores } from "./sharedStores";
import { state } from "./sharedUrlState";
import { persistPrefs, shell } from "./sharedWorkspaceStorage";
import { systemCardHtml } from "./shellSnapshot";
import { refreshStoreWorks } from "./storeWorks";

function updateSystemCard() {
  const card = document.querySelector(".system-card");
  if (card) card.innerHTML = systemCardHtml();
}

// Start-up warm-up and the health check over the shared state, usable without the legacy runtime. The runtime uses
// this same instance.
export const { warmupConfiguredLlm, checkHealth } = createAppLifecycle({
  state,
  api,
  defaultProviderProfile: (...args: unknown[]) =>
    (providerProfilesService.defaultProviderProfile as (...a: unknown[]) => unknown)(...args),
  ensureProviderProfiles: (...args: unknown[]) =>
    (providerProfilesService.ensureProviderProfiles as (...a: unknown[]) => unknown)(...args),
  isResearcher,
  persistPrefs,
  warmupProviderProfile,
  refreshProviderStatuses: (...args: unknown[]) =>
    (providerProfilesService.refreshProviderStatuses as (...a: unknown[]) => unknown)(...args),
  refreshStoreWorks,
  refreshStores,
  // Looked up when called, so a test that mocks part of the navigation module can still import this one.
  renderView: () => renderView(),
  shell,
  updateSystemCard,
});
