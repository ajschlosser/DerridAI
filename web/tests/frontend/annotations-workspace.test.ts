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
import { createAnnotationsWorkspace } from "../../src/domain/annotationsWorkspace";
import { createRuntimeState } from "../../src/runtime/runtimeState";
import { annotationsState, createAnnotationsState } from "../../src/state/workspaceState";

vi.mock("../../src/composables/notifications", () => ({ toast: vi.fn() }));

// The modern Annotations Playwright workflow covers rendered interactions; these pin commands and snapshot shape.
function setup(overrides: Record<string, unknown> = {}) {
  // The annotations fields are shared module state, so start each test from the defaults.
  Object.assign(annotationsState, createAnnotationsState());
  const state = createRuntimeState() as unknown as Record<string, any>;
  const calls: string[] = [];
  const spies: Record<string, ReturnType<typeof vi.fn>> = {};
  const deps = new Proxy(
    {
      state,
      tr: (_key: string, fallback: string) => fallback,
      label: (key: string) => key,
      ...overrides,
    } as Record<string, unknown>,
    {
      get: (target, name: string) => {
        if (name in target) return target[name];
        spies[name] ??= vi.fn(() => {
          if (name === "persistPrefs" || name === "syncUrl" || name === "navigateTo")
            calls.push(name);
        });
        return spies[name];
      },
    },
  );
  const workspace = createAnnotationsWorkspace(deps as never) as Record<
    string,
    (...args: unknown[]) => unknown
  >;
  return { state, calls, spies, workspace };
}

describe("annotations workspace", () => {
  it("sets the search text and the view, saving and syncing the URL", () => {
    const { state, calls, workspace } = setup();
    workspace.setAnnotationsWorkspaceQuery("remains");
    workspace.setAnnotationsWorkspaceView("recent");
    workspace.setAnnotationsWorkspaceView("anything else");
    expect(state.annotationSearch).toBe("remains");
    expect(state.annotationView).toBe("works");
    expect(calls).toEqual([
      "persistPrefs",
      "syncUrl",
      "persistPrefs",
      "syncUrl",
      "persistPrefs",
      "syncUrl",
    ]);
  });

  it("opens a work's overview", () => {
    const { state, spies, workspace } = setup();
    workspace.openAnnotationsWorkspaceWork("Glas");
    expect(state.workOverview).toBe("Glas");
    expect(spies.navigateTo).toHaveBeenCalledWith("works");
  });

  it("groups filtered annotations by work, newest first overall", () => {
    const note = (id: string, createdAt: string) => ({ id, note: id, created_at: createdAt });
    const file = { id: "f", name: "a.jsonl" };
    const rows = [
      {
        file,
        index: 0,
        record: {
          work: "Glas",
          record_id: "g1",
          annotations: [note("n3", "2026-02-02"), note("n2", "2026-02-03")],
        },
      },
      {
        file,
        index: 1,
        record: {
          work: "Of Grammatology",
          record_id: "o1",
          annotations: [note("n1", "2026-02-01")],
        },
      },
    ];
    const { workspace } = setup({
      allRows: () => rows,
      isResearcher: () => false,
      canUse: () => true,
      annotationMatches: () => true,
      memoCorpus: (_key: string, build: () => unknown[]) => build(),
    });
    const snapshot = workspace.getAnnotationsWorkspaceSnapshot() as {
      total: number;
      annotations: Array<{ id: string }>;
      groups: Array<{ work: string; records: number }>;
    };
    expect(snapshot.total).toBe(3);
    expect(snapshot.annotations.map((a) => a.id)).toEqual(["n2", "n3", "n1"]);
    expect(snapshot.groups.map((g) => [g.work, g.records])).toEqual([
      ["Glas", 1],
      ["Of Grammatology", 1],
    ]);
  });

  it("removes a local annotation using the workspace item's stored file id", async () => {
    const file = {
      id: "f",
      name: "a.jsonl",
      records: [{ record_id: "r1", annotations: [{ id: "n1", note: "Remove me" }] }],
      dirty: new Set<number>(),
    };
    const reviewKey = vi.fn((fileRef: { id: string }, index: number) => `${fileRef.id}::${index}`);
    const applyRecordChanges = vi.fn(
      (
        target: typeof file,
        index: number,
        changes: { annotations: Array<{ id: string; note: string }> },
      ) => {
        target.records[index] = { ...target.records[index], ...changes };
        return 1;
      },
    );
    const persistFileNow = vi.fn(async () => undefined);
    const { workspace } = setup({
      reviewKey,
      reviewItemFromKey: (key: string) =>
        key === "f::0" ? { file, index: 0, record: file.records[0] } : null,
      applyRecordChanges,
      persistFileNow,
      api: vi.fn(async () => ({ annotations: [] })),
      isResearcher: () => false,
      hasCapability: () => true,
    });

    await workspace.removeAnnotationsWorkspaceItem({
      removable: true,
      server: false,
      local_file_id: "f",
      local_index: 0,
      local_annotation_index: 0,
      shared_annotation_id: null,
    });

    expect(reviewKey).toHaveBeenCalledWith({ id: "f" }, 0);
    expect(applyRecordChanges).toHaveBeenCalledWith(
      file,
      0,
      { annotations: [] },
      { source: "annotation-delete" },
    );
    expect(file.records[0].annotations).toEqual([]);
    expect(persistFileNow).toHaveBeenCalledWith(file);
  });
});
