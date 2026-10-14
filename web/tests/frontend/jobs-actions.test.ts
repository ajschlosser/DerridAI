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

import { afterEach, describe, expect, it, vi } from "vitest";
import * as facade from "../../src/domain/jobsActions";
import { jobsActionNames, registerJobsActions } from "../../src/domain/jobsActions";

describe("jobs actions facade", () => {
  afterEach(() => registerJobsActions(null));

  it("fails explicitly when called before the workspace registers", () => {
    expect(() => facade.cancelBackgroundJob("j1")).toThrow(/not ready: cancelBackgroundJob/);
  });

  it("forwards arguments and results to whichever workspace registered last", () => {
    const first = vi.fn(() => "first");
    const second = vi.fn(() => "second");
    registerJobsActions({ cancelBackgroundJob: first });
    const forwarder = facade.cancelBackgroundJob; // captured before the second registration
    registerJobsActions({ cancelBackgroundJob: second });
    expect(forwarder("j1", { force: true })).toBe("second");
    expect(second).toHaveBeenCalledWith("j1", { force: true });
    expect(first).not.toHaveBeenCalled();
  });

  it("exports a forwarder for every declared action", () => {
    for (const name of jobsActionNames)
      expect(typeof (facade as Record<string, unknown>)[name]).toBe("function");
  });

  it("is what the real jobs workspace registers", async () => {
    const { createJobsWorkspace } = await import("../../src/domain/jobsWorkspace");
    const noop = () => undefined;
    const deps = new Proxy(
      { state: { jobs: [], ragConfig: {} } },
      { get: (t, k) => (k in t ? (t as never)[k] : noop) },
    );
    const workspace = createJobsWorkspace(deps as never);
    expect(Object.keys(workspace)).toEqual(expect.arrayContaining([...jobsActionNames]));
    registerJobsActions({ ...workspace, cancelBackgroundJob: () => "via-workspace" });
    expect(facade.cancelBackgroundJob()).toBe("via-workspace");
  });
});
