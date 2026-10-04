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
import { getShellSnapshot, systemCardHtml } from "../../src/domain/shellSnapshot";
import { jobsState } from "../../src/state/jobsState";
import { state } from "../../src/domain/sharedUrlState";

describe("shell snapshot", () => {
  afterEach(() => {
    state.health = null;
    jobsState.jobs = [];
    state.view = "home";
  });

  it("counts only queued, running and cancelling jobs as active", () => {
    jobsState.jobs = [
      { id: "running", status: "running" },
      { id: "queued", status: "queued" },
      { id: "cancelling", status: "cancelling" },
      { id: "succeeded", status: "succeeded" },
    ];
    expect(getShellSnapshot().activeJobs).toBe(3);
  });

  it("reports the view and context for the current page", () => {
    state.view = "works";
    const snapshot = getShellSnapshot();
    expect(snapshot.view).toBe("works");
    expect(snapshot.context.title).toBe("Works");
  });

  it("shows Checking before health is known, then Online and Offline states", () => {
    state.health = null;
    expect(systemCardHtml()).toContain("Checking");
    state.health = { ok: true, chroma: { available: true } };
    expect(systemCardHtml()).toContain("Online");
    state.health = { ok: false };
    expect(systemCardHtml()).toContain("Offline");
  });
});
