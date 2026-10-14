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

import type { Router } from "vue-router";

// The router owns the URL; compatibility workspace state follows it. This keeps the
// view and URL-encoded state (table state in `ts=`, file, record, store) aligned
// with every settled router navigation without introducing a second navigation authority.
export type RuntimeLocationSyncDeps = {
  isStarted: () => boolean;
  viewForPath: (path: string) => string | undefined;
  currentView: () => string;
  /** Re-derive compatibility workspace state from the browser location and repaint. */
  sync: () => void;
};

export function createRuntimeLocationSync(router: Router, deps: RuntimeLocationSyncDeps) {
  let popped = false;
  // History navigation (browser back/forward) can change only URL state within one
  // view, so it always resyncs. Other navigations resync only when they land on a
  // different compatibility view.
  const stopListening = router.options.history.listen((_to, _from, info) => {
    popped = info.type === "pop";
  });
  const stopAfterEach = router.afterEach((to, _from, failure) => {
    const wasPop = popped;
    popped = false;
    if (failure || !deps.isStarted()) return;
    const view = deps.viewForPath(to.path);
    if (wasPop || (view && view !== deps.currentView())) deps.sync();
  });
  return {
    dispose() {
      stopListening();
      stopAfterEach();
    },
  };
}
