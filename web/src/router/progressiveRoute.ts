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

import { defineComponent, h, type Component } from "vue";
import ProgressiveRouteView from "../components/shell/ProgressiveRouteView.vue";

export type ProgressiveRouteModule = { default: Component } | Component;
export type ProgressiveRouteLoader = () => Promise<ProgressiveRouteModule>;

const routeLoaders = new WeakMap<object, ProgressiveRouteLoader>();

function memoizeRouteLoader(loader: ProgressiveRouteLoader): ProgressiveRouteLoader {
  let pending: Promise<ProgressiveRouteModule> | null = null;
  return () => {
    if (!pending) {
      pending = loader().catch((error) => {
        // A transient chunk/network failure must remain retryable.
        pending = null;
        throw error;
      });
    }
    return pending;
  };
}

/**
 * Keep Vue Router's route component synchronous while the real page module loads
 * inside it. Vue Router otherwise waits for a lazy route import before committing
 * the URL/current route, which makes navigation itself feel blocked by chunk I/O.
 */
export function progressiveRouteComponent(loader: ProgressiveRouteLoader): Component {
  const load = memoizeRouteLoader(loader);
  const component = defineComponent({
    name: "ProgressiveRouteEntry",
    inheritAttrs: false,
    setup(_props, { attrs }) {
      return () => h(ProgressiveRouteView, { ...attrs, loader: load });
    },
  });
  routeLoaders.set(component, load);
  return component;
}

/** Resolve the page-module loader owned by one progressive route entry. */
export function progressiveRouteLoaderFor(component: unknown): ProgressiveRouteLoader | undefined {
  return typeof component === "object" && component !== null
    ? routeLoaders.get(component)
    : undefined;
}
