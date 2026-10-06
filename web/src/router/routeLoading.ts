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

import { shallowRef } from "vue";
import type { RouteLocationNormalized, Router } from "vue-router";

/** Fallback feedback for router-level delays. App page modules now load after route commit. */
export function createRouteLoading(router: Router, delay = 180) {
  const destination = shallowRef<RouteLocationNormalized | null>(null);
  const failed = shallowRef<RouteLocationNormalized | null>(null);
  const visible = shallowRef(false);
  let timer: ReturnType<typeof setTimeout> | undefined;
  function clear() {
    clearTimeout(timer);
    destination.value = null;
    visible.value = false;
  }
  const stopBefore = router.beforeEach((to, from) => {
    clear();
    failed.value = null;
    if (to.path === from.path) return;
    destination.value = to;
    timer = setTimeout(() => {
      visible.value = destination.value === to;
    }, delay);
  });
  const stopAfter = router.afterEach((to) => {
    // A cancelled navigation may settle after its replacement has started.
    if (destination.value === to) clear();
  });
  const stopError = router.onError((_error, to) => {
    if (destination.value !== to) return;
    clear();
    failed.value = to;
  });
  async function retry() {
    const target = failed.value;
    if (target) await router.push(target.fullPath).catch(() => undefined);
  }
  function reload() {
    if (failed.value) window.location.assign(router.resolve(failed.value.fullPath).href);
  }
  function dispose() {
    clear();
    failed.value = null;
    stopBefore();
    stopAfter();
    stopError();
  }
  return { destination, failed, visible, retry, reload, dispose };
}
