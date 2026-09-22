/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { createWorkspacePersistence } from "../../src/domain/workspacePersistence";
import { createRuntimeState } from "../../src/runtime/runtimeState";

describe("workspace preference persistence", () => {
  it("removes callbacks before saving the structured-clone payload", async () => {
    const state = createRuntimeState();
    state.storageReady = true;
    state.appConfig.provider_profiles = [{ id: "profile", onChange: () => undefined }];
    state.selectedEvidence = { formatter: () => "formatted" };
    const idbPut = vi.fn(async () => undefined);
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
      toast: vi.fn(),
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
