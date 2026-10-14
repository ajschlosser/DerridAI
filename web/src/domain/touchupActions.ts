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

// Late-binding facade over the touch-up workflow the runtime still builds (`touchupWorkspaceInfo` and friends). The
// touch-up dialog is a Vue component; it imports these forwarders instead of the runtime, and the runtime registers
// the implementations once. Calling an action before registration is an error rather than a silent no-op.
/* eslint-disable @typescript-eslint/no-explicit-any */
type Fn = (...args: any[]) => any;

export const touchupActionNames = [
  "touchupWorkspaceInfo",
  "touchupProviderStatus",
  "touchupRequestConfig",
  "touchupRequest",
  "touchupSubmitBackground",
  "touchupApplyResults",
] as const;
export type TouchupActionName = (typeof touchupActionNames)[number];
export type TouchupActions = Record<TouchupActionName, Fn>;

let registered: Partial<TouchupActions> | null = null;

/** Called by the runtime with its implementations; pass null to clear (tests). Extra members are ignored. */
export function registerTouchupActions(actions: Partial<TouchupActions> | null) {
  registered = actions;
}

function forward(name: TouchupActionName): Fn {
  return (...args) => {
    const action = registered?.[name];
    if (!action)
      throw new Error(`Touch-up workflow is not ready: ${name} was called before it registered`);
    return action(...args);
  };
}

export const touchupWorkspaceInfo = forward("touchupWorkspaceInfo");
export const touchupProviderStatus = forward("touchupProviderStatus");
export const touchupRequestConfig = forward("touchupRequestConfig");
export const touchupRequest = forward("touchupRequest");
export const touchupSubmitBackground = forward("touchupSubmitBackground");
export const touchupApplyResults = forward("touchupApplyResults");
