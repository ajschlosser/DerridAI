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

// Late-binding facade over the jobs workspace. The operation dock, the operations panel, the job dialogs and the
// database-presence upsert all call job actions, while the jobs workspace itself calls back into the dock and panel.
// Registering the workspace here, and importing these forwarders instead of the workspace, lets each side be built as
// its own module without a construction-order cycle. Like `jobsPause`, the workspace registers itself.
/* eslint-disable @typescript-eslint/no-explicit-any */
type Fn = (...args: any[]) => any;

export const jobsActionNames = [
  "refreshJobs",
  "startRealtime",
  "startJobPolling",
  "pruneClientJobState",
  "removeFinishedJob",
  "clearFinishedOperations",
  "syncUpsertJobReceipts",
  "cancelBackgroundJob",
  "submitBackgroundLlmJob",
  "registerExternalJob",
  "maybeDesktopNotify",
  "syncJobProgressToasts",
] as const;
export type JobsActionName = (typeof jobsActionNames)[number];
export type JobsActions = Record<JobsActionName, Fn>;

let registered: Partial<JobsActions> | null = null;

/** Called by the jobs workspace with its actions; pass null to clear (tests). Extra members are ignored. */
export function registerJobsActions(actions: Partial<JobsActions> | null) {
  registered = actions;
}

function forward(name: JobsActionName): Fn {
  return (...args) => {
    const action = registered?.[name];
    if (!action)
      throw new Error(`Jobs workspace is not ready: ${name} was called before it registered`);
    return action(...args);
  };
}

export const refreshJobs = forward("refreshJobs");
export const startRealtime = forward("startRealtime");
export const startJobPolling = forward("startJobPolling");
export const pruneClientJobState = forward("pruneClientJobState");
export const removeFinishedJob = forward("removeFinishedJob");
export const clearFinishedOperations = forward("clearFinishedOperations");
export const syncUpsertJobReceipts = forward("syncUpsertJobReceipts");
export const cancelBackgroundJob = forward("cancelBackgroundJob");
export const submitBackgroundLlmJob = forward("submitBackgroundLlmJob");
export const registerExternalJob = forward("registerExternalJob");
export const maybeDesktopNotify = forward("maybeDesktopNotify");
export const syncJobProgressToasts = forward("syncJobProgressToasts");
