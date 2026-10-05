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
import { createWorkspacePersistence } from "../../src/domain/workspacePersistence";
import { createRuntimeState } from "../../src/state/runtimeState";

describe("workspace preference persistence", () => {
  it("removes callbacks before saving the structured-clone payload", async () => {
    const state = createRuntimeState();
    state.storageReady = true;
    state.appConfig.provider_profiles = [{ id: "profile", onChange: () => undefined }] as never;
    state.selectedEvidence = { formatter: () => "formatted" };
    const idbPut = vi.fn(async (_store: string, _value: unknown) => undefined);
    const persistence = createWorkspacePersistence({
      state,
      fileTimers: new Map(),
      applyUiTheme: vi.fn(),
      ensureProviderProfiles: vi.fn(),
      idbGet: vi.fn(),
      idbGetAll: vi.fn(),
      idbPut,
      invalidateCorpusCache: vi.fn(),
      restoreCurrentPdfAsset: vi.fn(),
      serializableFile: vi.fn(),
      trf: vi.fn((key: string) => key),
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
});
