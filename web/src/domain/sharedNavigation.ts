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
import { canAccessView } from "./pageAccess";
import { createNavigation } from "./navigation";
import {
  activeFile,
  dbSearchWhere,
  selectedIndex,
  sharedUrlStateCodec,
  state,
} from "./sharedUrlState";
import { persistPrefs, shell } from "./sharedWorkspaceStorage";

// Navigation over the shared workspace state, usable without the legacy runtime. The runtime uses this same instance
// (one URL-sync hook, one snapshot), and installs `setRenderViewHook` for the part of a transition that still lives
// there: unmounting the legacy operations panel and normalising the URL after a view change.
let renderViewHook: () => void = () => {};
export function setRenderViewHook(hook: unknown) {
  renderViewHook = typeof hook === "function" ? (hook as () => void) : () => {};
}

export const {
  getUrlSyncHook,
  navSnapshot,
  setUrlSyncHook,
  currentTableUrlState,
  applyCompressedTableUrlState,
  urlFromState,
  syncUrl,
  applyUrlState,
  navigateTo,
} = createNavigation({
  codec: sharedUrlStateCodec,
  state,
  activeFile,
  canAccessPage: (view: string) => canAccessView(sessionState.userContext, view),
  dbSearchWhere,
  persistPrefs,
  renderView: () => renderViewHook(),
  selectedIndex,
  shell,
});
