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

// Late-bound forwarders to the operation dock's progress cards. The dock is still built by the runtime (it takes
// runtime-owned DOM helpers), so shared modules that show progress call these; the runtime registers the dock's
// functions once it exists. Before that, progress is purely cosmetic and these do nothing.
/* eslint-disable @typescript-eslint/no-explicit-any */
type Fn = (...args: any[]) => any;
type Hooks = { show: Fn; update: Fn; hide: Fn };
let hooks: Hooks | null = null;

export function registerOperationProgress(next: Hooks | null) {
  hooks = next;
}
export const showOperationProgress = (title: string, total: number): unknown =>
  hooks?.show(title, total) ?? null;
export const updateOperationProgress = (op: unknown, ...rest: unknown[]): unknown =>
  hooks?.update(op, ...rest);
export const hideOperationProgress = (op: unknown): unknown => hooks?.hide(op);
