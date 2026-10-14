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

import { NavigationFailureType, isNavigationFailure, type Router } from "vue-router";

// The runtime asks the router to change the URL through this hook. A navigation the router refuses (guard,
// cancellation) is reported as a value, not an exception, so the runtime is rolled back to wherever the router
// actually is instead of being left disagreeing with it.
export type RuntimeUrlSyncOptions = { replace?: boolean };

export function createRuntimeUrlSyncHook(router: Router, resync: () => void) {
  return (href: string, options?: RuntimeUrlSyncOptions) => {
    const target = router.resolve(href).fullPath;
    if (router.currentRoute.value.fullPath === target) return;
    const navigation = options?.replace ? router.replace(target) : router.push(target);
    void navigation
      .then((failure) => {
        // `duplicated` is a no-op, and `cancelled` means a newer navigation superseded this one and will settle the
        // location itself; resyncing from the not-yet-updated URL would roll the runtime back mid-transition.
        if (isNavigationFailure(failure, NavigationFailureType.aborted)) {
          console.warn("DerridAI navigation was not applied; resyncing from the router", failure);
          resync();
        }
      })
      .catch((error) => {
        console.warn("DerridAI navigation failed; resyncing from the router", error);
        resync();
      });
  };
}
