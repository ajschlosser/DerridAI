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

// Mounts the Vue Operations panel into a placeholder that the legacy Home dashboard renders.
// The dashboard replaces its HTML wholesale, so each mount first tears down the previous one.
import { createApp, type App } from "vue";
import { getActivePinia } from "pinia";
import OperationsPanel from "../components/OperationsPanel.vue";
import type { OperationsBridge } from "../domain/operationsPanel";

let app: App | null = null;

export function unmountOperationsPanel(): void {
  app?.unmount();
  app = null;
}

export function mountOperationsPanel(host: Element | null, bridge: OperationsBridge): void {
  unmountOperationsPanel();
  if (!host) return;
  const next = createApp(OperationsPanel, { bridge });
  const pinia = getActivePinia();
  if (pinia) next.use(pinia);
  next.mount(host);
  app = next;
}
