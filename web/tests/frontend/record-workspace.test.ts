/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createRecordWorkspace } from "../../src/domain/recordWorkspace";
import { createRuntimeState } from "../../src/runtime/runtimeState";

// The rendered Record view is covered by the legacy baseline's record scenarios (recorded before this logic moved);
// these pin the commands that do not need a full workspace to run.
function setup(overrides: Record<string, unknown> = {}) {
  const state = createRuntimeState() as unknown as Record<string, any>;
  const calls: string[] = [];
  const deps = new Proxy(
    { state, tr: (_key: string, fallback: string) => fallback, ...overrides } as Record<
      string,
      unknown
    >,
    {
      get: (target, name: string) => {
        if (name in target) return target[name];
        return vi.fn(() => {
          if (name === "persistPrefs" || name === "syncUrl") calls.push(name);
        });
      },
    },
  );
  const workspace = createRecordWorkspace(deps as never) as Record<
    string,
    (...args: unknown[]) => unknown
  >;
  return { state, calls, workspace };
}

describe("record workspace commands", () => {
  it("sets the find text, saves and syncs the URL", () => {
    const { state, calls, workspace } = setup();
    expect(workspace.setRecordWorkspaceFind("outside")).toBe("outside");
    expect(state.recordFind).toBe("outside");
    expect(calls).toEqual(["persistPrefs", "syncUrl"]);
    expect(workspace.setRecordWorkspaceFind(null)).toBe("");
  });

  it("refuses to save changes for a researcher or a role that cannot edit", async () => {
    await expect(
      setup({ isResearcher: () => true, canUse: () => true }).workspace.saveCurrentRecordChanges({
        text: "x",
      }),
    ).rejects.toThrow("Your role cannot edit local records.");
    await expect(
      setup({ isResearcher: () => false, canUse: () => false }).workspace.saveCurrentRecordChanges({
        text: "x",
      }),
    ).rejects.toThrow("Your role cannot edit local records.");
  });

  it("needs a loaded record to save changes", async () => {
    const { workspace } = setup({
      isResearcher: () => false,
      canUse: () => true,
      activeFile: () => null,
    });
    await expect(workspace.saveCurrentRecordChanges({ text: "x" })).rejects.toThrow(
      "No record selected",
    );
  });
});
