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

/**
 * Keep Vue Router's route component synchronous while the real page module loads
 * inside it. Vue Router otherwise waits for a lazy route import before committing
 * the URL/current route, which makes navigation itself feel blocked by chunk I/O.
 */
export function progressiveRouteComponent(loader: ProgressiveRouteLoader): Component {
  return defineComponent({
    name: "ProgressiveRouteEntry",
    inheritAttrs: false,
    setup(_props, { attrs }) {
      return () => h(ProgressiveRouteView, { ...attrs, loader });
    },
  });
}
