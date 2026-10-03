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
import { canAccessView, userHasCapability } from "./pageAccess";

// Role and capability checks over the shared session state, usable without the legacy runtime. The runtime uses these
// same functions.
export function isResearcher(): boolean {
  return Boolean(sessionState.userContext && sessionState.userContext.role !== "admin");
}

export function hasCapability(capability: string): boolean {
  return userHasCapability(sessionState.userContext, capability);
}

export function canAccessPage(view: string): boolean {
  return canAccessView(sessionState.userContext, view);
}
