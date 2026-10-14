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

const db = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn() }));
vi.mock("../../src/domain/sharedWorkspaceStorage", () => ({ workspaceDb: db }));

import { loadCompareDraft, saveCompareDraft } from "../../src/features/compare/compareDraft";

describe("Compare draft repository", () => {
  beforeEach(() => vi.clearAllMocks());

  it("restores a normalized Compare-only record", async () => {
    db.get.mockResolvedValue({
      key: "compare-draft",
      sourceA: "scratch",
      sourceB: "library",
      keyA: "",
      keyB: "f::1",
      pasteA: "{}",
      pasteB: "",
      filter: "all",
    });

    await expect(loadCompareDraft()).resolves.toEqual({
      sourceA: "scratch",
      sourceB: "library",
      keyA: "",
      keyB: "f::1",
      pasteA: "{}",
      pasteB: "",
      filter: "all",
    });
    expect(db.get).toHaveBeenCalledWith("prefs", "compare-draft");
  });

  it("writes only the Compare draft record", async () => {
    const draft = {
      sourceA: "scratch" as const,
      sourceB: "library" as const,
      keyA: "",
      keyB: "f::1",
      pasteA: "{}",
      pasteB: "",
      filter: "changed" as const,
    };
    await saveCompareDraft(draft);
    expect(db.put).toHaveBeenCalledWith("prefs", { key: "compare-draft", ...draft });
  });
});
