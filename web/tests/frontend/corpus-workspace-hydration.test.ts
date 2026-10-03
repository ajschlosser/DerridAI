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

import { describe, expect, it, vi } from "vitest";
import { createCorpusWorkspaceHydration } from "../../src/domain/corpusWorkspaceHydration";
function setup() {
  const deps = {
    isResearcher: () => false,
    hasFiles: () => false,
    hasStores: () => false,
    refreshStores: vi.fn(async () => undefined),
    recordStores: () => [
      { name: "small", count: 2 },
      { name: "large", count: 10 },
    ],
    activeStore: () => "",
    setActiveStore: vi.fn(),
    exportStore: vi.fn(async () => [] as unknown[] | null),
    exportFailure: () => "Export unavailable",
  };
  return { deps, hydrate: createCorpusWorkspaceHydration(deps) };
}
describe("initial Records hydration", () => {
  it("selects the active nonempty store, falling back to the largest store", async () => {
    const { deps, hydrate } = setup();
    await hydrate();
    expect(deps.exportStore).toHaveBeenCalledWith("large");
    const active = setup();
    active.deps.activeStore = () => "small";
    await active.hydrate();
    expect(active.deps.exportStore).toHaveBeenCalledWith("small");
  });
  it("deduplicates concurrent discovery and skips a completed revisit", async () => {
    const { deps, hydrate } = setup();
    let release!: () => void;
    deps.refreshStores.mockReturnValue(
      new Promise<undefined>((resolve) => {
        release = () => resolve(undefined);
      }),
    );
    const first = hydrate();
    const second = hydrate();
    expect(first).toBe(second);
    release();
    await first;
    await hydrate();
    expect(deps.refreshStores).toHaveBeenCalledTimes(1);
    expect(deps.exportStore).toHaveBeenCalledTimes(1);
  });
  it("returns a failed discovery and permits an explicit retry", async () => {
    const { deps, hydrate } = setup();
    deps.refreshStores.mockRejectedValueOnce(new Error("Discovery failed"));
    expect((await hydrate()).status).toBe("error");
    expect((await hydrate()).status).toBe("ready");
    expect(deps.refreshStores).toHaveBeenCalledTimes(2);
  });
  it("treats a null export as unavailable, preserves successful empty exports, and retries", async () => {
    const { deps, hydrate } = setup();
    deps.exportStore.mockResolvedValueOnce(null);
    expect(await hydrate()).toEqual({ status: "error", error: new Error("Export unavailable") });
    expect((await hydrate()).status).toBe("ready");
  });
  it("does no reads for a researcher or loaded files", async () => {
    const researcher = setup();
    researcher.deps.isResearcher = () => true;
    expect((await researcher.hydrate()).status).toBe("skipped");
    expect(researcher.deps.refreshStores).not.toHaveBeenCalled();
    const loaded = setup();
    loaded.deps.hasFiles = () => true;
    expect((await loaded.hydrate()).status).toBe("skipped");
    expect(loaded.deps.exportStore).not.toHaveBeenCalled();
  });
  it("keeps a file imported during discovery instead of loading a competing collection", async () => {
    const { deps, hydrate } = setup();
    let loaded = false;
    deps.hasFiles = () => loaded;
    deps.refreshStores.mockImplementation(async () => {
      loaded = true;
    });
    expect((await hydrate()).status).toBe("skipped");
    expect(deps.exportStore).not.toHaveBeenCalled();
  });
});
