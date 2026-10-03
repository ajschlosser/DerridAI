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

// Late-bound hooks for two runtime-owned effects that the shared modules trigger but cannot import: repainting the
// operations panel and telling the vector-store views the store list changed. The runtime registers them once its
// bridges exist; before that they are no-ops (nothing is painted yet, so there is nothing to refresh).
type Hook = () => unknown;
const hooks: { refreshOperationsPanelOnly: Hook | null; notifyVectorStoresChanged: Hook | null } = {
  refreshOperationsPanelOnly: null,
  notifyVectorStoresChanged: null,
};

export function registerOperationHooks(next: Partial<typeof hooks> | null) {
  hooks.refreshOperationsPanelOnly = next?.refreshOperationsPanelOnly ?? null;
  hooks.notifyVectorStoresChanged = next?.notifyVectorStoresChanged ?? null;
}
export const refreshOperationsPanelOnly = (): unknown => hooks.refreshOperationsPanelOnly?.();
export const notifyVectorStoresChanged = (): unknown => hooks.notifyVectorStoresChanged?.();
