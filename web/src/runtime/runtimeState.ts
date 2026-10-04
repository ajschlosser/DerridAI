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

import { bindJobsState } from "../state/jobsState";
import { bindWorkspaceGroups } from "../state/workspaceState";

// Initial value of the legacy runtime's single mutable workspace state. Moved verbatim from
// the old runtime so the shape has one home; the runtime still owns the instance it creates.

export function createRuntimeState() {
  const state = {
    jobsPollTimer: null,
  };
  // Background-job and per-view workspace fields live in stores shared with Vue code; see state/jobsState.ts and
  // state/workspaceState.ts.
  const withJobs = bindJobsState(state);
  return bindWorkspaceGroups(withJobs);
}

export type RuntimeState = ReturnType<typeof createRuntimeState>;
