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
import { persistPrefs, refreshShell, shell } from "./sharedWorkspaceStorage";
import { unmountOperationsPanel } from "../runtime/operationsPanelHost";

// Navigation over the shared workspace state, usable without the legacy runtime. The runtime uses this same instance
// (one URL-sync hook, one snapshot). `renderView` is the tail of every view transition: unmount the legacy operations
// panel, guard access and normalise the URL.
export function renderView() {
  // Native Vue routes do not mount `#main`; compatibility rendering must not overwrite them with a URL sync.
  if (!document.querySelector("#main")) {
    unmountOperationsPanel();
    refreshShell();
    return null;
  }
  if (state.view !== "home") unmountOperationsPanel();
  if (!canAccessView(sessionState.userContext, state.view)) state.view = "home";
  syncUrl({ replace: true });
  return null;
}

/** Persist and repaint after the shared URL state has been applied (by the runtime or by the router). */
export function repaintAfterLocationChange() {
  persistPrefs();
  shell();
  renderView();
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
  renderView,
  selectedIndex,
  shell,
});
