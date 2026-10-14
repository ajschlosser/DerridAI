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
import { unmountOperationsPanel } from "./operationsPanelHost";

let nativeShellRefreshEpoch = 0;

function refreshNativeShellAfterPaint() {
  const epoch = ++nativeShellRefreshEpoch;
  const refresh = () => {
    if (epoch === nativeShellRefreshEpoch) refreshShell();
  };

  if (typeof globalThis.requestAnimationFrame !== "function") {
    globalThis.setTimeout(refresh, 0);
    return;
  }

  // Router afterEach hooks run before Vue has necessarily painted the committed
  // destination. One rAF still runs before that paint; the second schedules the
  // compatibility shell refresh for the following frame so shell projection work
  // cannot keep the previous page visible.
  globalThis.requestAnimationFrame(() => {
    globalThis.requestAnimationFrame(refresh);
  });
}

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

/**
 * Reconcile compatibility state after a location change without blocking a
 * native Vue route's first paint.
 */
export function repaintAfterLocationChange() {
  if (!document.querySelector("#main")) {
    // The router is authoritative for native pages. Applying URL state has
    // already updated the compatibility model; do not serialize the legacy
    // workspace preference record on every route change. Defer the one shell
    // compatibility refresh until after the destination has painted.
    unmountOperationsPanel();
    refreshNativeShellAfterPaint();
    return;
  }

  // Legacy surfaces still own their compatibility render lifecycle.
  persistPrefs();
  refreshShell();
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
