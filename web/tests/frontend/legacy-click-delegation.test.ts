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

const openJobResults = vi.fn();
const copyCitation = vi.fn();
const copyJsonToClipboard = vi.fn();
const toggleWorkspaceEvidence = vi.fn();
const renderView = vi.fn();
const toast = vi.fn();
vi.mock("../../src/domain/operationsPanelHooks", () => ({
  openJobResults: (...a: unknown[]) => openJobResults(...a),
}));
vi.mock("../../src/domain/clipboardCopy", () => ({
  copyCitation: (...a: unknown[]) => copyCitation(...a),
  copyJsonToClipboard: (...a: unknown[]) => copyJsonToClipboard(...a),
}));
vi.mock("../../src/domain/sharedNavigation", () => ({ renderView: () => renderView() }));
vi.mock("../../src/domain/sharedSearchSupport", () => ({
  evidenceSelection: {
    toggleWorkspaceEvidence: (...a: unknown[]) => toggleWorkspaceEvidence(...a),
  },
}));
vi.mock("../../src/composables/notifications", () => ({ toast: (...a: unknown[]) => toast(...a) }));
vi.mock("../../src/composables/messageDialog", () => ({ openMessageDialog: vi.fn() }));
vi.mock("../../src/domain/sharedTranslate", () => ({ tr: (key: string) => key }));
vi.mock("../../src/domain/sharedUrlState", () => ({
  state: {
    files: [{ id: "f1", records: [{ record_id: "r1" }] }],
    storeRecords: [{ _chroma_id: "c1", record_id: "r2" }],
    storeSearchResults: [],
  },
}));

import "../../src/domain/legacyClickDelegation";

function click(html: string, selector: string) {
  document.body.innerHTML = html;
  document.querySelector(selector)!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
}

describe("legacy click delegation", () => {
  beforeEach(() => {
    [
      openJobResults,
      copyCitation,
      copyJsonToClipboard,
      toggleWorkspaceEvidence,
      renderView,
      toast,
    ].forEach((m) => m.mockReset());
    openJobResults.mockResolvedValue(undefined);
  });

  it("opens a job result and disables the button while it loads", () => {
    click('<button id="b" data-job-result="j1">Open</button>', "#b");
    expect(openJobResults).toHaveBeenCalledWith("j1");
    expect((document.querySelector("#b") as HTMLButtonElement).disabled).toBe(true);
  });

  it("copies a loaded record and reports a vanished one", () => {
    click('<button id="b" data-copy-row-key="f1::0"></button>', "#b");
    expect(copyJsonToClipboard).toHaveBeenCalledWith({ record_id: "r1" }, "r1");
    click('<button id="b" data-copy-row-key="f1::9"></button>', "#b");
    expect(toast).toHaveBeenCalledWith("runtime.toast.source_record_gone", { tone: "danger" });
  });

  it("cites a record, toggles evidence and copies a store record without its chroma id", () => {
    click('<button id="b" data-cite-row-key="f1::0" data-cite-kind="full"></button>', "#b");
    expect(copyCitation).toHaveBeenCalledWith({ record_id: "r1" }, "full");
    click('<button id="b" data-toggle-workspace-evidence="f1::0"></button>', "#b");
    expect(toggleWorkspaceEvidence).toHaveBeenCalledWith(expect.objectContaining({ id: "f1" }), 0);
    expect(renderView).toHaveBeenCalled();
    click('<button id="b" data-copy-store-record="c1"></button>', "#b");
    expect(copyJsonToClipboard).toHaveBeenLastCalledWith({ record_id: "r2" }, "r2");
  });
});
