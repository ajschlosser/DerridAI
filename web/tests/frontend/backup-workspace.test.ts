/* Copyright 2026 Aaron John Schlosser, PhD. */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "../../src/composables/notifications";
import { openMessageDialog } from "../../src/composables/messageDialog";
import { createBackupWorkspace } from "../../src/domain/backupWorkspace";
import { englishDefault } from "../../src/i18n/englishDefault";

vi.mock("../../src/composables/notifications", () => ({ toast: vi.fn() }));
vi.mock("../../src/composables/messageDialog", () => ({ openMessageDialog: vi.fn() }));
const openMessageModal = vi.mocked(openMessageDialog);
beforeEach(() => {
  vi.mocked(toast).mockReset();
  openMessageModal.mockReset();
  openMessageModal.mockResolvedValue(false);
});

// The confirm, created, failed and restored views are covered by the legacy baseline's backup and restore scenarios
// (recorded before this logic moved); these pin the guards.
function setup(state: Record<string, unknown> = {}, profiles: unknown[] = []) {
  const deps = new Proxy(
    {
      state: { jobs: [], files: [], ...state },
      providerProfiles: () => profiles,
      tr: (key: string, fallback = "") => fallback || englishDefault(key) || key,
    },
    { get: (target: Record<string, unknown>, name: string) => target[name] ?? vi.fn() },
  );
  return { workspace: createBackupWorkspace(deps as never) };
}

describe("backup workspace", () => {
  it("knows whether a backup would contain provider credentials", () => {
    expect(setup({}, [{ api_key: "k" }]).workspace.backupContainsCredentials()).toBe(true);
    expect(setup({}, [{ api_key: "" }]).workspace.backupContainsCredentials()).toBe(false);
  });

  it("refuses to restore while operations are active", async () => {
    const { workspace } = setup({ jobs: [{ status: "running" }] });
    await workspace.restoreFullBackup(new File(["x"], "b.zip"));
    expect(toast).toHaveBeenCalledWith(
      "Cancel or wait for all background operations before restoring a backup.",
      { tone: "warning" },
    );
    expect(openMessageModal).not.toHaveBeenCalled();
  });

  it("does nothing without a file, and stops when the confirmation is declined", async () => {
    const { workspace } = setup();
    await workspace.restoreFullBackup(undefined);
    await workspace.restoreFullBackup(new File(["x"], "b.zip"));
    expect(openMessageModal).toHaveBeenCalledTimes(1);
    expect(toast).not.toHaveBeenCalled();
  });
});
