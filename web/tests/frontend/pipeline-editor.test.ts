/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";

import PipelineDefinitionEditor from "../../src/components/pipelines/PipelineDefinitionEditor.vue";
import PipelineVersionEditorPanel from "../../src/components/pipelines/PipelineVersionEditorPanel.vue";
import {
  contractPurpose,
  contractStrategies,
  contractVocabulary,
} from "../../src/components/pipelines/fixtures/pipelineCatalogContract";
import { useI18nStore } from "../../src/stores/i18n";
import type {
  PipelineDefinition,
  PipelineStage,
  PipelineValidationResponse,
} from "../../src/types/pipelines";

const stage = (id: string, strategy: string, next: string[] = []): PipelineStage => ({
  id,
  strategy,
  enabled: true,
  config: {},
  next,
  on_empty: null,
  on_unavailable: null,
  on_timeout: null,
  on_error: null,
});

function draft(): PipelineDefinition {
  return {
    pipeline_id: "research.custom",
    version: 2,
    name: "Custom",
    purpose: "research",
    status: "draft",
    entry_stage_ids: ["a"],
    stages: [
      stage("a", "retrieve.chroma_similarity", ["b"]),
      stage("b", "validate.provenance", ["c"]),
      stage("c", "pack.evidence_context"),
    ],
  };
}

function mountEditor(initial = draft()) {
  const model = ref(initial);
  const Host = defineComponent({
    setup: () => () =>
      h(PipelineDefinitionEditor, {
        modelValue: model.value,
        strategies: contractStrategies,
        purpose: contractPurpose("research"),
        vocabulary: contractVocabulary,
        "onUpdate:modelValue": (value: PipelineDefinition) => (model.value = value),
      }),
  });
  const wrapper = mount(Host, { attachTo: document.body });
  return { wrapper, model };
}

const inspectorTitle = (wrapper: ReturnType<typeof mountEditor>["wrapper"]) =>
  wrapper.get(".stage-inspector-editor h4").text();

describe("graph-first pipeline editor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().dictionary = {};
  });

  it("edits one selected stage instead of stacking a card per stage", async () => {
    const { wrapper } = mountEditor();
    expect(wrapper.findAll(".stage-inspector-editor")).toHaveLength(1);
    expect(inspectorTitle(wrapper)).toBe("a");

    await wrapper.findAll(".stage-row")[1].trigger("click");
    expect(inspectorTitle(wrapper)).toBe("b");
    expect(wrapper.findAll(".stage-row")[1].attributes("aria-current")).toBe("true");
    wrapper.unmount();
  });

  it("selects a stage from the graph", async () => {
    const { wrapper } = mountEditor();
    await wrapper.findAll(".diagram-node")[2].trigger("click");
    expect(inspectorTitle(wrapper)).toBe("c");
    wrapper.unmount();
  });

  it("keeps the selection through a rename and updates connections", async () => {
    const { wrapper, model } = mountEditor();
    await wrapper.findAll(".stage-row")[1].trigger("click");
    await wrapper.get('.stage-inspector-editor input[autocomplete="off"]').setValue("gate");
    await flushPromises();
    expect(inspectorTitle(wrapper)).toBe("gate");
    expect(model.value.stages[0].next).toEqual(["gate"]);
    wrapper.unmount();
  });

  it("adds a unique stage from the palette, connects it, selects it and moves focus to it", async () => {
    const { wrapper, model } = mountEditor();
    await wrapper.get(".stage-navigator header button").trigger("click");
    await flushPromises();
    // The palette offers only stages that can receive what stage a provides.
    const dialog = document.body.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    const add = [...document.body.querySelectorAll<HTMLButtonElement>(".palette-add")].find(
      (button) => button.textContent?.includes("Provenance sufficiency gate"),
    );
    expect(add).toBeDefined();
    add!.click();
    await flushPromises();

    expect(model.value.stages).toHaveLength(4);
    const created = model.value.stages[3].id;
    expect(new Set(model.value.stages.map((item) => item.id)).size).toBe(4);
    expect(model.value.stages[0].next).toEqual(["b", created]);
    expect(inspectorTitle(wrapper)).toBe(created);
    expect(document.body.querySelector('[role="dialog"]')).toBeNull();
    expect(document.activeElement).toBe(wrapper.get(".stage-inspector-editor h4").element);
    wrapper.unmount();
  });

  it("removes the selected stage, selects its neighbour and cleans connections", async () => {
    const { wrapper, model } = mountEditor();
    await wrapper.findAll(".stage-row")[1].trigger("click");
    await wrapper.get(".stage-footer button").trigger("click");
    await flushPromises();
    expect(model.value.stages.map((item) => item.id)).toEqual(["a", "c"]);
    expect(model.value.stages[0].next).toEqual([]);
    expect(inspectorTitle(wrapper)).toBe("c");

    // Removing the last stage selects the previous one.
    await wrapper.get(".stage-footer button").trigger("click");
    await flushPromises();
    expect(inspectorTitle(wrapper)).toBe("a");
    expect(wrapper.get(".stage-footer button").attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("reorders stages from the row menu and the selection follows", async () => {
    const { wrapper, model } = mountEditor();
    await wrapper.findAll(".stage-row")[0].trigger("click");
    await wrapper.findAll(".stage-navigator .ui-menu-trigger")[0].trigger("click");
    await flushPromises();
    const items = wrapper.findAll('[role="menuitem"]');
    expect(items[0].attributes("aria-disabled")).toBe("true");
    await items[1].trigger("click");
    await flushPromises();
    expect(model.value.stages.map((item) => item.id)).toEqual(["b", "a", "c"]);
    expect(inspectorTitle(wrapper)).toBe("a");
    wrapper.unmount();
  });

  it("edits normal connections with a multi-target picker", async () => {
    const { wrapper, model } = mountEditor();
    await wrapper
      .get('.stage-inspector-editor [aria-label="Remove b from next stages"]')
      .trigger("click");
    expect(model.value.stages[0].next).toEqual([]);
    wrapper.unmount();
  });

  it("opens version details when identity is incomplete", async () => {
    const incomplete = draft();
    incomplete.name = "";
    const { wrapper } = mountEditor(incomplete);
    expect((wrapper.get(".version-details").element as HTMLDetailsElement).open).toBe(true);
    wrapper.unmount();

    const complete = mountEditor();
    expect((complete.wrapper.get(".version-details").element as HTMLDetailsElement).open).toBe(
      false,
    );
    complete.wrapper.unmount();
  });
});

describe("version editor command status", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().dictionary = {};
  });

  function mountPanel(validation: PipelineValidationResponse | null) {
    return mount(PipelineVersionEditorPanel, {
      props: {
        modelValue: draft(),
        strategies: contractStrategies,
        purpose: contractPurpose("research"),
        vocabulary: contractVocabulary,
        validation,
        saving: false,
      },
    });
  }
  const status = (wrapper: ReturnType<typeof mountPanel>) => wrapper.get(".command-status").text();

  it("reports validation state without a success card", async () => {
    expect(status(mountPanel(null))).toBe("Not validated");
    const ok = mountPanel({
      validation: { valid: true, issues: [] },
      runtime_supported: true,
    });
    expect(status(ok)).toBe("Valid · Executable");
    expect(ok.find(".validation-issues").exists()).toBe(false);

    const inspectOnly = mountPanel({
      validation: { valid: true, issues: [] },
      runtime_supported: false,
      runtime_error: "Adapter cannot run this graph.",
    });
    expect(status(inspectOnly)).toBe("Valid · Inspect only");
    expect(inspectOnly.get(".validation-issues").text()).toContain("Adapter cannot run");

    const invalid = mountPanel({
      validation: {
        valid: false,
        issues: [
          { level: "error", code: "x", message: "No entry stage.", stage_id: "a" },
          { level: "error", code: "y", message: "Unknown target." },
          { level: "warning", code: "z", message: "Heads up." },
        ],
      },
      runtime_supported: true,
    });
    expect(status(invalid)).toBe("2 changes required");
    expect(invalid.get(".validation-issues").text()).toContain("No entry stage.");
  });

  it("marks a result stale once the draft changes", async () => {
    const wrapper = mountPanel({
      validation: { valid: true, issues: [] },
      runtime_supported: true,
    });
    expect(status(wrapper)).toBe("Valid · Executable");
    const changed = draft();
    changed.name = "Renamed";
    await wrapper.setProps({ modelValue: changed });
    expect(status(wrapper)).toBe("Changed since last validation");
  });
});
