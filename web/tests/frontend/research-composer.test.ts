import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ResearchComposer from "../../src/components/research/ResearchComposer.vue";
import { useI18nStore } from "../../src/stores/i18n";

const baseProps = {
  prompt: "",
  instructions: "",
  sourceCollection: "derrida_primary",
  providerProfileId: "phi4",
  responseLanguage: "auto",
  preset: "balanced",
  evidenceCount: 0,
  promptMetadata: {
    evidence: ["speaker", "position_holder", "stance", "discourse_role"],
    context: ["quoted_author"],
    record: [],
  },
  stores: [{ name: "derrida_primary", count: 12 }],
  profiles: [{ id: "phi4", name: "Phi-4", type: "ollama" as const, model: "phi4:14b" }],
  history: [],
  canRun: true,
  canConfigure: true,
  canManageRuns: true,
};

describe("ResearchComposer prompt metadata setup", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().dictionary = {
      "research.prompt_metadata": "Prompt metadata",
      "research.configure_prompt_metadata": "Configure prompt metadata",
      "research.metadata_with_evidence": "Evidence",
      "research.metadata_as_context": "Context",
      "research.metadata_with_record": "Record",
    };
  });

  it("surfaces prompt metadata before a run and opens its configuration directly", async () => {
    const wrapper = mount(ResearchComposer, { props: baseProps });

    const control = wrapper.get(".research-context-action");
    expect(control.text()).toContain("Prompt metadata");
    expect(control.text()).toContain("Evidence 4");
    expect(control.text()).toContain("Context 1");
    expect(control.text()).toContain("Record 0");

    await wrapper.get(".research-context-action-button").trigger("click");
    expect(wrapper.emitted("promptMetadata")).toHaveLength(1);

    wrapper.unmount();
  });
});
