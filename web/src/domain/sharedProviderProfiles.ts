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

import { sessionState } from "../state/workspaceState";
import { api } from "./legacyApi";
import { createProviderProfiles } from "./providerProfilesService";
import { createProviderWarmup } from "./providerWarmup";
import { providerRequestConfig } from "./providerRequest";
import { state } from "./sharedUrlState";
import { persistPrefs } from "./sharedWorkspaceStorage";

// Provider profiles and warm-up over the shared workspace state, usable without the legacy runtime. The runtime uses
// these same instances. The two services need each other (profiles start warm-ups, warm-ups read profiles), so the
// warm-up is looked up when it is called.
export const providerProfilesService = createProviderProfiles({
  state,
  api,
  isResearcher: () =>
    Boolean(sessionState.userContext && sessionState.userContext.role !== "admin"),
  persistPrefs,
  uid: () => crypto.randomUUID(),
  warmupProviderProfile: (...args: Parameters<typeof warmupProviderProfile>) =>
    warmupProviderProfile(...args),
});

export const { warmupProviderProfile } = createProviderWarmup({
  state,
  api,
  providerDisplayName: providerProfilesService.providerDisplayName,
  providerProfile: providerProfilesService.providerProfile,
  providerRequestConfig,
});

export const { getProviderProfilesForUi, getDefaultProviderProfileId } = providerProfilesService;
