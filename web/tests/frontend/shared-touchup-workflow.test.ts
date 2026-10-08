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

const h = vi.hoisted(() => ({
  api: vi.fn(),
  applyRecordChanges: vi.fn((..._a: unknown[]) => 2),
  commitRecordFiles: vi.fn(),
  clearReviewSelection: vi.fn(),
  shell: vi.fn(),
  renderView: vi.fn(),
}));
vi.mock("../../src/domain/legacyApi", () => ({ api: (...a: unknown[]) => h.api(...a) }));
vi.mock("../../src/domain/jobsActions", () => ({ submitBackgroundLlmJob: vi.fn() }));
vi.mock("../../src/domain/sharedNavigation", () => ({ renderView: () => h.renderView() }));
vi.mock("../../src/domain/sharedWorkspaceStorage", () => ({ shell: () => h.shell() }));
vi.mock("../../src/domain/sharedRecordEditing", () => ({
  applyRecordChanges: (...a: unknown[]) => h.applyRecordChanges(...a),
  commitRecordFiles: (...a: unknown[]) => h.commitRecordFiles(...a),
}));
vi.mock("../../src/domain/sharedSearchSupport", () => ({
  evidenceSelection: { clearReviewSelection: () => h.clearReviewSelection() },
}));
vi.mock("../../src/domain/sharedProviderProfiles", () => ({
  providerProfilesService: {
    providerProfiles: () => [{ id: "p1", type: "ollama", api_key: "secret" }],
    providerProfile: (id: string) => (id === "p1" ? { id: "p1", type: "ollama" } : null),
    defaultProviderProfile: () => ({ id: "p1" }),
  },
}));

import {
  touchupApplyResults,
  touchupProviderStatus,
  touchupWorkspaceInfo,
} from "../../src/domain/sharedTouchupWorkflow";
import { state } from "../../src/domain/sharedUrlState";

describe("shared touchup workflow", () => {
  beforeEach(() => {
    Object.values(h).forEach((m) => m.mockClear());
    state.appConfig.default_review_preset = "text";
  });

  it("never hands provider API keys to the workspace and defaults to the text preset", () => {
    const info = touchupWorkspaceInfo([{ key: "k", file: { records: [{ text: "x" }] }, index: 0 }]);
    expect(info.profiles.every((p: { api_key?: string }) => p.api_key === undefined)).toBe(true);
    expect(info.providerProfileId).toBe("p1");
  });

  it("reports an unconfigured provider instead of calling the API", async () => {
    const status = await touchupProviderStatus("missing");
    expect(status.available).toBe(false);
    expect(h.api).not.toHaveBeenCalled();
  });

  it("applies only approved fields and clears the review selection", () => {
    const record = { needs_review: true };
    const item = { key: "k", file: { records: [record] }, index: 0 };
    const out = touchupApplyResults(
      [item],
      { k: { proposal: { changes: { speaker: "A", stance: "B" }, model: "m" } } },
      { k: ["speaker"] },
    );
    expect(h.applyRecordChanges).toHaveBeenCalledWith(
      item.file,
      0,
      { speaker: "A", needs_review: false },
      expect.objectContaining({ source: "llm_review", model: "m" }),
    );
    expect(out).toEqual({ appliedFields: 2, reviewedRecords: 1 });
    expect(h.clearReviewSelection).toHaveBeenCalled();
  });
});
