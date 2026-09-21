/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createBackupWorkspace } from "../../src/domain/backupWorkspace";

// The confirm, created, failed and restored views are covered by the legacy baseline's backup and restore scenarios
// (recorded before this logic moved); these pin the guards.
function setup(state: Record<string, unknown> = {}, profiles: unknown[] = []) {
  const toast = vi.fn();
  const openMessageModal = vi.fn(async () => false);
  const deps = new Proxy(
    {
      state: { jobs: [], files: [], ...state },
      toast,
      openMessageModal,
      providerProfiles: () => profiles,
    },
    { get: (target: Record<string, unknown>, name: string) => target[name] ?? vi.fn() },
  );
  return { toast, openMessageModal, workspace: createBackupWorkspace(deps as never) };
}

describe("backup workspace", () => {
  it("knows whether a backup would contain provider credentials", () => {
    expect(setup({}, [{ api_key: "k" }]).workspace.backupContainsCredentials()).toBe(true);
    expect(setup({}, [{ api_key: "" }]).workspace.backupContainsCredentials()).toBe(false);
  });

  it("refuses to restore while operations are active", async () => {
    const { toast, openMessageModal, workspace } = setup({ jobs: [{ status: "running" }] });
    await workspace.restoreFullBackup(new File(["x"], "b.zip"));
    expect(toast).toHaveBeenCalledWith(
      "Cancel or wait for all background operations before restoring a backup.",
    );
    expect(openMessageModal).not.toHaveBeenCalled();
  });

  it("does nothing without a file, and stops when the confirmation is declined", async () => {
    const { toast, openMessageModal, workspace } = setup();
    await workspace.restoreFullBackup(undefined);
    await workspace.restoreFullBackup(new File(["x"], "b.zip"));
    expect(openMessageModal).toHaveBeenCalledTimes(1);
    expect(toast).not.toHaveBeenCalled();
  });
});
