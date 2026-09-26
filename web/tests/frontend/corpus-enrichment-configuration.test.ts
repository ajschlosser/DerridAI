/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusEnrichmentConfiguration from "../../src/components/corpus-builder/CorpusEnrichmentConfiguration.vue";

const profiles = [
  {
    id: "local",
    name: "Local Ollama",
    type: "ollama" as const,
    model: "gemma4:e2b",
    available: true,
    max_concurrent_requests: 1,
  },
  {
    id: "remote",
    name: "Remote compatible",
    type: "openai" as const,
    model: "research-model",
    available: true,
    max_concurrent_requests: 8,
  },
];

function mountWorkspace(overrides: Record<string, unknown> = {}) {
  return mount(CorpusEnrichmentConfiguration, {
    props: {
      selectedProviderId: "local",
      selectedReviewProviderId: "",
      providerProfiles: profiles,
      defaultProfileId: "local",
      selectedProviderLabel: "Local Ollama",
      selectedProfileModel: "gemma4:e2b",
      enrichmentMode: "fast",
      semanticIndexing: true,
      autoCleanText: true,
      llmTouchupDuringEnrichment: false,
      noiseUnusableThreshold: 45,
      llmAssessTextNoise: false,
      manualProvider: "ollama",
      manualModel: "",
      manualBaseUrl: "",
      manualApiKey: "",
      disabled: false,
      ...overrides,
    },
  });
}

describe("Corpus Builder enrichment configuration", () => {
  it("owns the enrichment tabpanel semantics after extraction", () => {
    const wrapper = mountWorkspace();
    const panel = wrapper.get("#corpus-config-panel-enrichment");

    expect(panel.attributes("role")).toBe("tabpanel");
    expect(panel.attributes("aria-labelledby")).toBe("corpus-config-tab-enrichment");
  });

  it("emits enrichment strategy changes without owning build state", async () => {
    const wrapper = mountWorkspace();

    await wrapper.get('input[type="radio"][value="deep"]').setValue();

    expect(wrapper.emitted("update:enrichmentMode")?.at(-1)).toEqual(["deep"]);
  });

  it("emits the escalation provider selection", async () => {
    const wrapper = mountWorkspace();

    await wrapper.get("#pdf-corpus-review-provider").setValue("remote");

    expect(wrapper.emitted("update:selectedReviewProviderId")?.at(-1)).toEqual(["remote"]);
  });

  it("keeps manual provider controls available when no profile is selected", async () => {
    const wrapper = mountWorkspace({
      selectedProviderId: "",
      selectedProviderLabel: "Ollama",
      selectedProfileModel: "",
    });

    const disclosure = wrapper.get(".advanced-config");
    await disclosure.trigger("toggle");
    await wrapper.get("#pdf-corpus-model").setValue("nomic-embed-text");

    expect(wrapper.emitted("update:manualModel")?.at(-1)).toEqual(["nomic-embed-text"]);
  });
});
