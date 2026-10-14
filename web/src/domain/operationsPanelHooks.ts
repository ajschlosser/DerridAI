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

// Late-bound forwarders to the operations panel and the job-results dialog. Both are still built by the runtime
// (the bridge and the job dialogs take runtime-owned helpers), so Vue code calls these; the runtime registers the real
// functions once they exist. Before that they do nothing.
/* eslint-disable @typescript-eslint/no-explicit-any */
type Fn = (...args: any[]) => any;
type Hooks = {
  mountOperationsPanelHost: Fn;
  openJobResults: Fn;
  gradeRagResponse: Fn;
  prepareRagRerun: Fn;
};
let hooks: Partial<Hooks> | null = null;

/** Registers hooks; a partial registration adds to the ones already present, `null` clears them all. */
export function registerOperationsPanelHooks(next: Partial<Hooks> | null) {
  hooks = next ? { ...hooks, ...next } : null;
}
/** Mounts the Vue operations panel into the `#operationsPanelHost` placeholder, when it is on the page. */
export const mountOperationsPanelHost = (): unknown => hooks?.mountOperationsPanelHost?.();
export const openJobResults = (jobId: string): unknown => hooks?.openJobResults?.(jobId);
/** Opens the LLM grading launcher for a response (runtime-built job dialogs). */
export const gradeRagResponse = (request: unknown): unknown => hooks?.gradeRagResponse?.(request);
/** Loads a saved Research request back into the Research form (research workspace). */
export const prepareRagRerun = (request: unknown): unknown => hooks?.prepareRagRerun?.(request);
