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

import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

const runtime = vi.hoisted(() => ({
  getProviderProfilesForUi: vi.fn(() => [
    {
      id: "local",
      name: "Local",
      type: "ollama",
      model: "qwen",
      base_url: "http://localhost:11434",
      max_concurrent_requests: 3,
    },
  ]),
  getProviderRequestConfigForUi: vi.fn(() => ({
    provider: "ollama",
    model: "qwen",
    base_url: "http://localhost:11434",
    api_key: "",
    max_concurrent_requests: 3,
    ollama: { num_ctx: 8192, temperature: 0.1 },
  })),
  getDefaultProviderProfileId: vi.fn(() => "local"),
}));

vi.mock("../../src/domain/appBootstrap", () => runtime);
vi.mock("../../src/domain/sharedProviderProfiles", () => ({
  getProviderProfilesForUi: runtime.getProviderProfilesForUi,
  getDefaultProviderProfileId: runtime.getDefaultProviderProfileId,
  getProviderRequestConfigForUi: runtime.getProviderRequestConfigForUi,
}));

const systemApi = vi.hoisted(() => ({
  researcherProviders: vi.fn(),
  researcherProviderAvailability: vi.fn(),
  llmStatus: vi.fn(),
}));

vi.mock("../../src/api/system", async () => {
  const actual =
    await vi.importActual<typeof import("../../src/api/system")>("../../src/api/system");
  return { ...actual, systemApi };
});

import { useCorpusProviderConfiguration } from "../../src/features/corpus-builder/composables/useCorpusProviderConfiguration";

describe("Corpus Builder provider configuration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    systemApi.researcherProviders.mockResolvedValue({ profiles: [] });
    systemApi.llmStatus.mockResolvedValue({
      available: true,
      models: [{ name: "qwen" }],
    });
  });

  it("builds a provider request from one canonical configuration owner", async () => {
    const currentBuild = ref(null);
    const config = useCorpusProviderConfiguration(currentBuild);

    await config.refreshProviders();

    expect(config.selectedProviderId.value).toBe("local");
    expect(config.contextSafe.value).toBe(true);
    expect(config.providerPayload.value).toMatchObject({
      provider_profile_id: "local",
      provider: "ollama",
      model: "qwen",
      base_url: "http://localhost:11434",
      max_concurrent_requests: 1,
      use_profile_defaults: true,
      generation: { num_ctx: 8192, temperature: 0.1 },
      enrichment_mode: "fast",
      semantic_indexing: true,
      // spaCy covers every language; BookNLP only enhances English when configured.
      document_nlp_provider: "auto",
    });
  });

  it("rehydrates build-specific execution settings without replacing defaults wholesale", () => {
    const currentBuild = ref(null);
    const config = useCorpusProviderConfiguration(currentBuild);

    config.applyBuildRequest({
      provider_profile_id: "local",
      generation: { num_ctx: 4096 },
      use_profile_defaults: false,
      max_concurrent_requests: 7,
      stage_limits: { segmentation_num_predict: 777 },
      stage_timeouts: { segmentation: 123 },
      record_sizing: { preferred_record_chars: 2200 },
    });

    expect(config.useProfileDefaults.value).toBe(false);
    expect(config.maxConcurrentRequests.value).toBe(7);
    expect(config.stageLimits.value.segmentation_num_predict).toBe(777);
    expect(config.stageLimits.value.manifest_num_predict).toBe(1800);
    expect(config.stageTimeouts.value.segmentation).toBe(123);
    expect(config.recordSizing.value.preferred_record_chars).toBe(2200);
    expect(config.recordSizing.value.absolute_record_chars).toBe(6000);
    expect(config.generationOverrides.value).toEqual({ num_ctx: 4096 });
  });
});
