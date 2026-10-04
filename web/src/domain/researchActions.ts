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

// Late-binding facade over the Research workspace the runtime still builds (it is wired to the runtime's navigation,
// shell refresh and evidence selection). `ResearchView` imports these forwarders instead of the runtime, and the
// runtime registers the implementations once. Calling one before registration is an error, not a silent no-op.
/* eslint-disable @typescript-eslint/no-explicit-any */
type Fn = (...args: any[]) => any;

export const researchActionNames = [
  "getResearchWorkspaceSnapshot",
  "updateResearchConfig",
  "removeResearchEvidence",
  "clearResearchEvidence",
  "discoverResearchModels",
  "refreshResearchJobs",
  "cancelResearchJob",
  "deleteResearchJob",
  "startResearchRun",
  "gradeResearchJob",
  "prepareResearchRerun",
] as const;
export type ResearchActionName = (typeof researchActionNames)[number];
export type ResearchActions = Record<ResearchActionName, Fn>;

let registered: Partial<ResearchActions> | null = null;

/** Called by the runtime with its implementations; pass null to clear (tests). Extra members are ignored. */
export function registerResearchActions(actions: Partial<ResearchActions> | null) {
  registered = actions;
}

function forward(name: ResearchActionName): Fn {
  return (...args) => {
    const action = registered?.[name];
    if (!action)
      throw new Error(`Research workspace is not ready: ${name} was called before it registered`);
    return action(...args);
  };
}

export const getResearchWorkspaceSnapshot = forward("getResearchWorkspaceSnapshot");
export const updateResearchConfig = forward("updateResearchConfig");
export const removeResearchEvidence = forward("removeResearchEvidence");
export const clearResearchEvidence = forward("clearResearchEvidence");
export const discoverResearchModels = forward("discoverResearchModels");
export const refreshResearchJobs = forward("refreshResearchJobs");
export const cancelResearchJob = forward("cancelResearchJob");
export const deleteResearchJob = forward("deleteResearchJob");
export const startResearchRun = forward("startResearchRun");
export const gradeResearchJob = forward("gradeResearchJob");
export const prepareResearchRerun = forward("prepareResearchRerun");
