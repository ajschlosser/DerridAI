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

const mocks = vi.hoisted(() => ({
  canUse: vi.fn(() => true),
  toast: vi.fn(),
  openMergeDialog: vi.fn(),
  download: vi.fn(),
  state: {
    activeFileId: "f1",
    files: [
      { id: "f1", name: "a.jsonl", dirty: new Set(["r1"]), records: [{ record_id: "r1" }] },
      { id: "f2", name: "b.jsonl", dirty: new Set(), records: [{ record_id: "r2" }] },
    ],
  },
}));

vi.mock("../../src/composables/notifications", () => ({ toast: mocks.toast }));
vi.mock("../../src/domain/disabledControls", () => ({ showAppModal: vi.fn() }));
vi.mock("../../src/domain/sharedRecordDialogs", () => ({
  recordDialogs: { openMergeDialog: mocks.openMergeDialog },
}));
vi.mock("../../src/domain/sharedRecordHelpers", () => ({ label: (field: string) => field }));
vi.mock("../../src/domain/sharedRecordScopes", () => ({
  activeFile: () => mocks.state.files[0],
  download: mocks.download,
  downloadBlob: vi.fn(),
  fileJsonl: (file: { name: string }) => `jsonl:${file.name}`,
}));
vi.mock("../../src/domain/sharedSession", () => ({ canUse: mocks.canUse }));
vi.mock("../../src/domain/sharedTranslate", () => ({ tr: (key: string) => key }));
vi.mock("../../src/domain/sharedUrlState", () => ({ state: mocks.state }));
vi.mock("../../src/domain/sharedNavigation", () => ({ navigateTo: vi.fn() }));
vi.mock("../../src/domain/sharedWorkspacePersistence", () => ({ persistFileNow: vi.fn() }));

import { triggerExport, triggerMerge } from "../../src/domain/sharedRecordFileCommands";

describe("shared record file commands", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.canUse.mockReturnValue(true);
    document.body.innerHTML = "";
  });

  it("opens the merge dialog only with corpus management", () => {
    triggerMerge();
    expect(mocks.openMergeDialog).toHaveBeenCalledOnce();
    mocks.canUse.mockReturnValue(false);
    triggerMerge();
    expect(mocks.openMergeDialog).toHaveBeenCalledOnce();
    expect(mocks.toast).toHaveBeenCalledWith("runtime.toast.cannot_merge_files", {
      tone: "warning",
    });
  });

  it("refuses the export menu without corpus management", () => {
    mocks.canUse.mockReturnValue(false);
    triggerExport();
    expect(document.querySelector("dialog")).toBeNull();
    expect(mocks.toast).toHaveBeenCalledWith("runtime.toast.cannot_export", { tone: "warning" });
  });

  it("exports the aggregate of every loaded record and closes the menu", () => {
    HTMLDialogElement.prototype.close = vi.fn();
    triggerExport();
    const button = document.querySelector<HTMLElement>('[data-export="aggregate"]');
    button?.click();
    expect(mocks.download).toHaveBeenCalledWith(
      "derridai-aggregate.jsonl",
      '{"record_id":"r1"}\n{"record_id":"r2"}\n',
    );
    expect(document.querySelector("dialog")).toBeNull();
  });
});
