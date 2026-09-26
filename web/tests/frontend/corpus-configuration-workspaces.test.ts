/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusExecutionSettings from "../../src/components/CorpusExecutionSettings.vue";
import CorpusHandsFreeSettings from "../../src/components/CorpusHandsFreeSettings.vue";
import CorpusMetadataConfiguration from "../../src/components/corpus-builder/CorpusMetadataConfiguration.vue";
import CorpusAdvancedConfiguration from "../../src/components/corpus-builder/CorpusAdvancedConfiguration.vue";

const schemaChoices = [
  {
    id: "default",
    name: "DerridAI default",
    description: "Default scholarly metadata",
    builtin: true,
    field_count: 8,
    groups: ["discourse"],
    hash: "hash",
  },
];

describe("Corpus Builder configuration workspaces", () => {
  it("owns both metadata schema and run-guidance surfaces in one tabpanel", async () => {
    const wrapper = mount(CorpusMetadataConfiguration, {
      props: {
        schemaId: "default",
        runGuidance: {},
        schemaChoices,
        chosenSchema: schemaChoices[0],
        runGuidanceFields: [
          { name: "speaker", label: "Speaker", group: "Discourse" },
        ],
        disabled: false,
      },
    });

    const panel = wrapper.get("#corpus-config-panel-metadata");
    expect(panel.attributes("role")).toBe("tabpanel");
    expect(panel.attributes("aria-labelledby")).toBe("corpus-config-tab-metadata");
    expect(
      Array.from(panel.element.children).filter((element) => element.tagName === "DETAILS"),
    ).toHaveLength(2);

    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("manageSchemas")).toHaveLength(1);

    await wrapper.get("select").setValue("default");
    expect(wrapper.emitted("update:schemaId")?.at(-1)).toEqual(["default"]);
  });

  it("owns hands-free and execution settings in one advanced tabpanel", () => {
    const wrapper = mount(CorpusAdvancedConfiguration, {
      props: {
        handsFree: {
          enabled: false,
          passes: 1,
          min_confidence: 0.8,
          unresolved: "best_guess",
          accept_records: true,
          publish: false,
        },
        generation: {},
        stageLimits: {},
        stageTimeouts: {},
        maxConcurrentRequests: 1,
        useProfileDefaults: true,
        disabled: false,
      },
    });

    const panel = wrapper.get("#corpus-config-panel-advanced");
    expect(panel.attributes("role")).toBe("tabpanel");
    expect(panel.attributes("aria-labelledby")).toBe("corpus-config-tab-advanced");
    expect(wrapper.findComponent(CorpusHandsFreeSettings).exists()).toBe(true);
    expect(wrapper.findComponent(CorpusExecutionSettings).exists()).toBe(true);
  });

  it("forwards execution-setting changes without moving provider policy into the view", () => {
    const wrapper = mount(CorpusAdvancedConfiguration, {
      props: {
        handsFree: {
          enabled: false,
          passes: 1,
          min_confidence: 0.8,
          unresolved: "best_guess",
          accept_records: true,
          publish: false,
        },
        generation: { num_ctx: 8192 },
        stageLimits: { segmentation_window_tokens: 5000 },
        stageTimeouts: { segmentation: 300 },
        maxConcurrentRequests: 2,
        useProfileDefaults: false,
        disabled: false,
      },
    });

    wrapper.findComponent(CorpusExecutionSettings).vm.$emit("update:generation", {
      num_ctx: 16384,
    });

    expect(wrapper.emitted("update:generation")?.at(-1)).toEqual([{ num_ctx: 16384 }]);
  });
});
