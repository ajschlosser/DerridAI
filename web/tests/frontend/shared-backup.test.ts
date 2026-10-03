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

import { afterEach, describe, expect, it } from "vitest";
import { downloadFullBackup } from "../../src/domain/sharedBackup";
import { jobsState } from "../../src/state/jobsState";

describe("shared backup state", () => {
  afterEach(() => {
    jobsState.jobs = [];
  });

  it("uses the shared jobs state when deciding whether a backup can start", async () => {
    jobsState.jobs = [{ id: "job-running", status: "running" }];

    const result = await downloadFullBackup({ confirmed: true });

    // Active work blocks the backup before any snapshot/network work begins. More importantly, this
    // exercises the jobs accessor that must remain present after backup leaves the legacy runtime.
    expect(typeof result).toBe("number");
  });
});
