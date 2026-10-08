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

import { beforeEach, describe, expect, it, vi } from "vitest";

const put = vi.fn();
vi.mock("../../src/domain/sharedWorkspaceStorage", () => ({
  workspaceDb: { get: vi.fn(), getAll: vi.fn(), put: (...a: unknown[]) => put(...a) },
  persistPrefs: vi.fn(),
  persistSettingsPreferences: vi.fn(),
}));
const toast = vi.fn();
vi.mock("../../src/composables/notifications", () => ({ toast: (...a: unknown[]) => toast(...a) }));

import { corpusCache } from "../../src/domain/corpusCache";
import {
  cancelPendingFileWrites,
  fileTimers,
  flushPendingFileWrites,
  persistFile,
  persistFileNow,
} from "../../src/domain/sharedWorkspacePersistence";

const file = () => ({
  id: "f1",
  name: "a.jsonl",
  records: [],
  errors: [],
  dirty: new Set<number>(),
});

describe("shared workspace persistence", () => {
  beforeEach(() => {
    put.mockReset();
    toast.mockReset();
    vi.useRealTimers();
  });

  it("writes the serialisable file without invalidating corpus projections", async () => {
    const sentinel = [] as never[];
    corpusCache.rows = sentinel;
    const beforeVersion = corpusCache.version;

    await persistFileNow(file());

    expect(put).toHaveBeenCalledTimes(1);
    expect(put.mock.calls[0][0]).toBe("files");
    expect(put.mock.calls[0][1]).toMatchObject({ id: "f1" });
    expect(corpusCache.rows).toBe(sentinel);
    expect(corpusCache.version).toBe(beforeVersion);
  });

  it("reports a failed save instead of swallowing it", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    put.mockRejectedValue(new Error("quota"));
    await persistFileNow(file());
    expect(toast).toHaveBeenCalledWith(expect.any(String), { tone: "danger" });
  });

  it("flushes pending file writes once and cancels their timers", async () => {
    vi.useFakeTimers();
    const f = file();
    persistFile(f);
    expect(fileTimers.has("f1")).toBe(true);

    await flushPendingFileWrites();

    expect(fileTimers.has("f1")).toBe(false);
    expect(put).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(300);
    expect(put).toHaveBeenCalledTimes(1);
  });

  it("can cancel pending file writes during an account transition", async () => {
    vi.useFakeTimers();
    persistFile(file());
    cancelPendingFileWrites();

    await vi.advanceTimersByTimeAsync(300);

    expect(fileTimers.size).toBe(0);
    expect(put).not.toHaveBeenCalled();
  });

  it("debounces persistFile and tracks the timer for cancellation", () => {
    vi.useFakeTimers();
    const f = file();
    persistFile(f);
    persistFile(f);
    expect(fileTimers.has("f1")).toBe(true);
    vi.advanceTimersByTime(300);
    expect(fileTimers.has("f1")).toBe(false);
    expect(put).toHaveBeenCalledTimes(1);
  });
});
