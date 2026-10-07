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
import { createPrefsPersistence } from "../../src/domain/prefsPersistence";
import { createWorkspacePersistence } from "../../src/domain/workspacePersistence";
import { createRuntimeState } from "../../src/state/runtimeState";

describe("workspace preference persistence", () => {
  it("removes callbacks before saving the structured-clone payload", async () => {
    const state = createRuntimeState();
    state.storageReady = true;
    state.appConfig.provider_profiles = [{ id: "profile", onChange: () => undefined }] as never;
    state.selectedEvidence = { formatter: () => "formatted" };
    const idbPut = vi.fn(async (_store: string, _value: unknown) => undefined);
    const persistence = createPrefsPersistence({
      state,
      put: idbPut,
    });

    await persistence.flushWorkspacePrefs();

    const saved = idbPut.mock.calls[0]?.[1] as {
      appConfig: { provider_profiles: Array<Record<string, unknown>> };
      selectedEvidence: Record<string, unknown>;
    };
    expect(saved.appConfig.provider_profiles).toEqual([{ id: "profile" }]);
    expect(saved.selectedEvidence).toEqual({});
    expect(() => structuredClone(saved)).not.toThrow();
  });

  it("applies domain overlays before final validation and before storage becomes writable", async () => {
    const state = createRuntimeState();
    state.storageReady = false;
    const applyUiTheme = vi.fn();
    const ensureProviderProfiles = vi.fn();
    const restorePreferenceOverlays = vi.fn(async () => {
      expect(state.storageReady).toBe(false);
      state.appConfig = { ...state.appConfig, ui_color_theme: "blue" };
      state.ragConfig = {
        ...state.ragConfig,
        locales: ["de", "en"],
        history: Array.from({ length: 120 }, (_, index) => ({ index })),
      };
      state.pageSize = Number.NaN;
    });

    const persistence = createWorkspacePersistence({
      state,
      fileTimers: new Map(),
      applyUiTheme,
      ensureProviderProfiles,
      idbGet: vi.fn(async (_store: string, key: string) =>
        key === "workspace"
          ? {
              key: "workspace",
              appConfig: { ui_color_theme: "green" },
              ragConfig: { locales: ["fr"] },
              reviewSelection: [],
            }
          : null,
      ),
      idbGetAll: vi.fn(async () => []),
      idbPut: vi.fn(),
      invalidateCorpusCache: vi.fn(),
      restoreCurrentPdfAsset: vi.fn(async () => undefined),
      restorePreferenceOverlays,
      serializableFile: vi.fn(),
      trf: vi.fn((key: string) => key),
    });

    await persistence.restoreWorkspace();

    expect(restorePreferenceOverlays).toHaveBeenCalledTimes(1);
    expect(applyUiTheme).toHaveBeenLastCalledWith("blue");
    expect(state.ragConfig.locales).toEqual(["en"]);
    expect(state.ragConfig.history).toHaveLength(100);
    expect(state.pageSize).toBe(100);
    expect(ensureProviderProfiles).toHaveBeenCalledTimes(1);
    expect(state.storageReady).toBe(true);
  });
});
