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

import { describe, expect, it } from "vitest";
import {
  dockCollapsedSummary,
  isActiveJobStatus,
  isTerminalJobStatus,
  jobIdsToPruneFromDock,
  jobProgressPercent,
  shouldMountOperationDock,
  statusBadgeTone,
} from "../../src/domain/operationsDock";

describe("operation dock visibility", () => {
  it("unmounts when nothing is visible and mounts as soon as a card exists", () => {
    expect(shouldMountOperationDock(0)).toBe(false);
    expect(shouldMountOperationDock(1)).toBe(true);
    expect(shouldMountOperationDock(4)).toBe(true);
  });

  it("prunes dock cards whose jobs were cleared from the live list", () => {
    expect(jobIdsToPruneFromDock(["keep", "gone", "also-gone"], ["keep", "new-active"])).toEqual([
      "gone",
      "also-gone",
    ]);
    expect(jobIdsToPruneFromDock(["running"], ["running"])).toEqual([]);
    expect(jobIdsToPruneFromDock([], ["running"])).toEqual([]);
  });
});

describe("job status helpers", () => {
  it("treats queued, running, and cancelling as live work", () => {
    expect(isActiveJobStatus("queued")).toBe(true);
    expect(isActiveJobStatus("running")).toBe(true);
    expect(isActiveJobStatus("cancelling")).toBe(true);
    expect(isActiveJobStatus("completed")).toBe(false);
    expect(isActiveJobStatus("failed")).toBe(false);
  });

  it("treats finished and blocked jobs as dismissable", () => {
    expect(isTerminalJobStatus("completed")).toBe(true);
    expect(isTerminalJobStatus("cancelled")).toBe(true);
    expect(isTerminalJobStatus("failed")).toBe(true);
    expect(isTerminalJobStatus("blocked")).toBe(true);
    expect(isTerminalJobStatus("running")).toBe(false);
  });

  it("maps status to a badge tone without inventing success for failures", () => {
    expect(statusBadgeTone("running")).toBe("info");
    expect(statusBadgeTone("completed")).toBe("success");
    expect(statusBadgeTone("failed")).toBe("danger");
    expect(statusBadgeTone("blocked")).toBe("warning");
    expect(statusBadgeTone("queued")).toBe("neutral");
  });

  it("clamps progress to a trustworthy 0–100 percent", () => {
    expect(jobProgressPercent({ completed: 5, total: 10 })).toBe(50);
    expect(jobProgressPercent({ completed: 0, total: 0 })).toBe(0);
    expect(jobProgressPercent({ completed: 12, total: 10 })).toBe(100);
  });
});

describe("collapsed dock copy", () => {
  it("names a single running job and its percent", () => {
    expect(
      dockCollapsedSummary({
        activeCount: 1,
        failedCount: 0,
        finishedCount: 0,
        primaryLabel: "PDF corpus build",
        primaryPercent: 43,
      }),
    ).toEqual({
      key: "operations.pill_primary_progress",
      fallback: "{label} · {percent}%",
      values: { label: "PDF corpus build", percent: 43 },
      tone: "info",
      percent: 43,
    });
  });

  it("counts concurrent work and surfaces failures", () => {
    expect(dockCollapsedSummary({ activeCount: 2, failedCount: 0, finishedCount: 1 }).key).toBe(
      "operations.pill_running_other",
    );
    expect(
      dockCollapsedSummary({ activeCount: 1, failedCount: 2, finishedCount: 0 }),
    ).toMatchObject({
      key: "operations.pill_running_failed",
      values: { running: 1, failed: 2 },
      tone: "danger",
    });
    expect(dockCollapsedSummary({ activeCount: 0, failedCount: 1, finishedCount: 0 }).tone).toBe(
      "danger",
    );
    expect(dockCollapsedSummary({ activeCount: 0, failedCount: 0, finishedCount: 2 }).key).toBe(
      "operations.pill_finished_other",
    );
  });
});
