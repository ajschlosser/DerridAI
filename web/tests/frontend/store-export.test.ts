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
  api: vi.fn(),
  toast: vi.fn(),
  download: vi.fn(),
  navigateTo: vi.fn(),
  persistFileNow: vi.fn(async () => undefined),
  invalidateCorpusCache: vi.fn(),
  persistPrefs: vi.fn(),
  persistCorpusPreferences: vi.fn(),
  state: { activeStore: "derrida", files: [] as Record<string, unknown>[], activeFileId: null },
}));

vi.mock("../../src/composables/notifications", () => ({ toast: mocks.toast }));
vi.mock("../../src/domain/legacyApi", () => ({ api: mocks.api }));
vi.mock("../../src/domain/corpusCache", () => ({
  invalidateCorpusCache: mocks.invalidateCorpusCache,
}));
vi.mock("../../src/domain/sharedRecordScopes", () => ({ download: mocks.download }));
vi.mock("../../src/domain/sharedNavigation", () => ({ navigateTo: mocks.navigateTo }));
vi.mock("../../src/domain/sharedTranslate", () => ({
  tr: (key: string) => key,
  trf: (key: string) => key,
}));
vi.mock("../../src/domain/sharedUrlState", () => ({ state: mocks.state }));
vi.mock("../../src/domain/sharedWorkspacePersistence", () => ({
  persistFileNow: mocks.persistFileNow,
}));
vi.mock("../../src/domain/sharedWorkspaceStorage", () => ({
  persistCorpusPreferences: mocks.persistCorpusPreferences,
}));

import { exportStoreJsonl } from "../../src/domain/storeExport";
import { registerOperationProgress } from "../../src/domain/operationProgressHooks";

describe("exportStoreJsonl", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.state.files = [];
    mocks.state.activeFileId = null;
    registerOperationProgress(null);
  });

  it("warns when no collection is selected", async () => {
    mocks.state.activeStore = "";
    await exportStoreJsonl();
    expect(mocks.toast).toHaveBeenCalledWith("records.toast.select_collection", {
      tone: "warning",
    });
    expect(mocks.api).not.toHaveBeenCalled();
    mocks.state.activeStore = "derrida";
  });

  it("downloads the exported records as JSONL named for the collection and work", async () => {
    mocks.api.mockResolvedValue({ records: [{ record_id: "a" }, { record_id: "b" }] });
    await exportStoreJsonl({ work: "Of Grammatology", downloadFile: true });
    expect(mocks.api).toHaveBeenCalledWith("/api/stores/derrida/export?work=Of+Grammatology");
    expect(mocks.download).toHaveBeenCalledWith(
      "derrida-Of-Grammatology.jsonl",
      '{"record_id":"a"}\n{"record_id":"b"}\n',
    );
  });

  it("replaces a clean earlier copy when reloading the same collection as a tab", async () => {
    mocks.api.mockResolvedValue({ records: [{ record_id: "a" }] });
    mocks.state.files = [
      { id: "old", name: "derrida.jsonl", imported_from_chroma: "derrida", dirty: new Set() },
    ];
    await exportStoreJsonl({ loadTab: true });
    expect(mocks.state.files).toHaveLength(1);
    expect(mocks.state.files[0].id).toBe("old");
    expect(mocks.state.activeFileId).toBe("old");
    expect(mocks.navigateTo).toHaveBeenCalledWith("list", { fileId: "old" });
  });

  it("keeps a dirty earlier copy and adds the reloaded one", async () => {
    mocks.api.mockResolvedValue({ records: [] });
    mocks.state.files = [
      { id: "old", name: "derrida.jsonl", imported_from_chroma: "derrida", dirty: new Set(["x"]) },
    ];
    await exportStoreJsonl({ loadTab: true, navigate: false });
    expect(mocks.state.files).toHaveLength(2);
    expect(mocks.navigateTo).not.toHaveBeenCalled();
  });

  it("reports a failed export and returns null", async () => {
    mocks.api.mockRejectedValue(new Error("down"));
    await expect(exportStoreJsonl({ downloadFile: true })).resolves.toBeNull();
    expect(mocks.toast).toHaveBeenCalledWith("runtime.toast.chroma_export_failed", {
      tone: "danger",
    });
  });

  it("drives the registered progress card", async () => {
    const hooks = { show: vi.fn(() => "op"), update: vi.fn(), hide: vi.fn() };
    registerOperationProgress(hooks);
    mocks.api.mockResolvedValue({ records: [] });
    await exportStoreJsonl({ downloadFile: true });
    expect(hooks.show).toHaveBeenCalledWith("Exporting derrida", 1);
    expect(hooks.update).toHaveBeenCalledWith("op", 1, 1, "0 records exported");
  });
});
