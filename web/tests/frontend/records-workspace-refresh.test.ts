/* Copyright 2026 Aaron John Schlosser, PhD. */
import { nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";

const runtime = vi.hoisted(() => ({
  getRecordsListSnapshot: vi.fn(() => ({ files: [], columns: [] })),
  state: { view: "" },
}));
vi.mock("../../src/runtime/runtime.js", () => ({ ...runtime }));

import { useRecordsWorkspace } from "../../src/composables/useRecordsWorkspace";
import { corpusState, touchCorpus } from "../../src/state/workspaceState";

describe("useRecordsWorkspace refreshes when the loaded corpus changes", () => {
  it("reads the snapshot again after the corpus changes, once it has been loaded", async () => {
    const records = useRecordsWorkspace();
    touchCorpus();
    await nextTick();
    // Nothing was loaded yet, so a change does not load anything on its own.
    expect(runtime.getRecordsListSnapshot).not.toHaveBeenCalled();

    records.load();
    expect(runtime.getRecordsListSnapshot).toHaveBeenCalledTimes(1);
    touchCorpus();
    await nextTick();
    expect(runtime.getRecordsListSnapshot).toHaveBeenCalledTimes(2);

    corpusState.activeFileId = "f2";
    await nextTick();
    expect(runtime.getRecordsListSnapshot).toHaveBeenCalledTimes(3);
    corpusState.activeFileId = null;
  });
});
