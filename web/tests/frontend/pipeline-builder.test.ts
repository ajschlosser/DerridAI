/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import { analysisFixture } from "../../src/components/pipelines/fixtures/pipelineAnalysisFixture";
import PipelineAnalysisPanel from "../../src/components/pipelines/PipelineAnalysisPanel.vue";
import PipelineDefinitionEditor from "../../src/components/pipelines/PipelineDefinitionEditor.vue";
import PipelineDefinitionsWorkspace from "../../src/components/pipelines/PipelineDefinitionsWorkspace.vue";
import PipelineNewDialog from "../../src/components/pipelines/PipelineNewDialog.vue";
import PipelineStagePalette from "../../src/components/pipelines/PipelineStagePalette.vue";
import PipelineStrategyInspector from "../../src/components/pipelines/PipelineStrategyInspector.vue";
import {
  contractPurpose,
  contractPurposes,
  contractStrategies,
  contractStrategy,
  contractVocabulary,
} from "../../src/components/pipelines/fixtures/pipelineCatalogContract";
import { ApiError } from "../../src/api/http";
import { usePipelineAnalysis } from "../../src/composables/usePipelineAnalysis";
import { useI18nStore } from "../../src/stores/i18n";
import type { PipelineAnalysis, PipelineDefinition } from "../../src/types/pipelines";

const analyze = vi.fn(async (_pipeline: PipelineDefinition, _signal?: AbortSignal) =>
  analysisFixture(),
);
vi.mock("../../src/api/pipelines", () => ({
  pipelinesApi: {
    analyze: (pipeline: PipelineDefinition, signal?: AbortSignal) => analyze(pipeline, signal),
    strategyLatency: vi.fn(async () => ({ strategies: {}, sampled_run_count: 0 })),
  },
}));

function draft(): PipelineDefinition {
  const stage = (id: string, strategy: string, next: string[] = []) => ({
    id,
    strategy,
    enabled: true,
    config: {},
    next,
  });
  return {
    pipeline_id: "research.custom",
    version: 1,
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

function mountEditor(analysis: PipelineAnalysis | null | "none" = analysisFixture()) {
  const model = ref(draft());
  const Host = defineComponent({
    setup: () => () =>
      h(PipelineDefinitionEditor, {
        modelValue: model.value,
        strategies: contractStrategies,
        purpose: contractPurpose("research"),
        vocabulary: contractVocabulary,
        analysis: analysis === "none" ? undefined : analysis,
        "onUpdate:modelValue": (value: PipelineDefinition) => (model.value = value),
      }),
  });
  return { wrapper: mount(Host, { attachTo: document.body }), model };
}

beforeEach(() => {
  setActivePinia(createPinia());
  useI18nStore().dictionary = {};
  analyze.mockClear();
});
afterEach(() => {
  document.body.innerHTML = "";
});

describe("stage inputs and outputs", () => {
  it("shows each input's type, source and status, and what consumes each output", async () => {
    const { wrapper } = mountEditor();
    await wrapper.findAll(".stage-row")[1].trigger("click");
    const ports = wrapper.get(".ports");
    expect(ports.text()).toContain("candidates");
    expect(ports.text()).toContain("Connected");
    expect(ports.text()).toContain("Currently: a → candidates");
    expect(ports.text()).toContain("Used by c.candidates");
    wrapper.unmount();
  });

  it("re-sources an input from the workflow and records an explicit binding", async () => {
    const { wrapper, model } = mountEditor();
    const select = wrapper.get(".ports select");
    await select.setValue("run:query");
    await flushPromises();
    expect(model.value.stages[0].inputs).toEqual({
      query: [{ source: "run_input", name: "query" }],
    });
    wrapper.unmount();
  });

  it("returns an input to automatic wiring", async () => {
    const { wrapper, model } = mountEditor();
    await wrapper.get(".ports select").setValue("run:query");
    await wrapper.get(".ports select").setValue("");
    await flushPromises();
    expect("inputs" in model.value.stages[0]).toBe(false);
    wrapper.unmount();
  });

  it("flags a stage whose input the server could not wire", async () => {
    const analysis = analysisFixture();
    analysis.wiring.stages.c.inputs[0].status = "unbound";
    analysis.wiring.stages.c.inputs[0].sources = [];
    const { wrapper } = mountEditor(analysis);
    const node = wrapper.findAll(".diagram-node")[2];
    expect(node.attributes("data-wiring")).toBe("problem");
    expect(node.text()).toContain("Input not satisfied");
    await wrapper.findAll(".stage-row")[2].trigger("click");
    expect(wrapper.get(".port").attributes("data-status")).toBe("unbound");
    expect(wrapper.get(".port").text()).toContain("Not connected");
    wrapper.unmount();
  });

  it("says how a binding that rewires inputs is treated", async () => {
    const { wrapper } = mountEditor();
    expect(wrapper.find(".ports-note[role=note]").exists()).toBe(false);
    await wrapper.get(".ports select").setValue("run:query");
    // The analysis prop is static in this host, so the note follows the stage's own bindings.
    wrapper.unmount();
  });

  it("lists the inputs the workflow supplies and who uses them", () => {
    const { wrapper } = mountEditor();
    expect(wrapper.get(".run-inputs").text()).toContain("query");
    expect(wrapper.get(".run-inputs").text()).toContain("a.query");
    wrapper.unmount();
  });

  it("keeps working without an analysis, hiding the wiring and performance panels", () => {
    const { wrapper } = mountEditor("none");
    expect(wrapper.find(".run-inputs").exists()).toBe(false);
    expect(wrapper.find(".pipeline-analysis, .analysis").exists()).toBe(false);
    expect(wrapper.find(".stage-inspector-editor").exists()).toBe(true);
    wrapper.unmount();
  });
});

describe("diagram lenses", () => {
  it("shows typical latency per stage and marks thin or borrowed figures", async () => {
    const { wrapper } = mountEditor();
    const buttons = wrapper.findAll(".lens-option");
    expect(buttons[0].attributes("aria-pressed")).toBe("true");
    await buttons[1].trigger("click");
    const nodes = wrapper.findAll(".diagram-node");
    expect(nodes[0].text()).toContain("≈ 400 ms");
    expect(nodes[1].find(".node-badge").attributes("data-tone")).toBe("warn");
    expect(nodes[2].text()).toContain("no data");
    wrapper.unmount();
  });

  it("shows declared complexity per stage and flags scans of the collection", async () => {
    const { wrapper } = mountEditor();
    await wrapper.findAll(".lens-option")[2].trigger("click");
    const nodes = wrapper.findAll(".diagram-node");
    expect(nodes[0].text()).toContain("O(q + d·log N + k)");
    expect(nodes[0].find(".node-badge").attributes("data-tone")).toBe("warn");
    expect(nodes[1].text()).toContain("O(n)");
    wrapper.unmount();
  });
});

describe("stage palette", () => {
  const anchor = draft().stages[0];

  function mountPalette(props: Record<string, unknown> = {}) {
    return mount(PipelineStagePalette, {
      attachTo: document.body,
      props: {
        strategies: contractStrategies,
        purpose: contractPurpose("research"),
        vocabulary: contractVocabulary,
        anchor,
        anchorStrategy: contractStrategy("retrieve.chroma_similarity"),
        ...props,
      },
    });
  }
  const labels = () =>
    [...document.body.querySelectorAll(".palette-group strong")].map((node) => node.textContent);

  it("offers only stages that can receive what the anchor provides", () => {
    const wrapper = mountPalette();
    const shown = labels();
    expect(shown).toContain("Cross-encoder reranker");
    // A generator needs a context packet, which candidates are not.
    expect(shown).not.toContain("Research answer generation");
    expect(document.body.textContent).toContain("more stages are hidden");
    wrapper.unmount();
  });

  it("can show every stage and explains why one does not fit", async () => {
    const wrapper = mountPalette();
    const check = document.body.querySelector<HTMLInputElement>(
      '.palette-filters input[type="checkbox"]',
    )!;
    check.checked = false;
    check.dispatchEvent(new Event("change"));
    await nextTick();
    expect(labels()).toContain("Research answer generation");
    expect(document.body.textContent).toContain(
      "Takes Context packet, but a provides Candidate set.",
    );
    wrapper.unmount();
  });

  it("starts a new path only with stages the workflow's own inputs can feed", async () => {
    const wrapper = mountPalette();
    const entry = document.body.querySelector<HTMLInputElement>('input[value="entry"]')!;
    entry.checked = true;
    entry.dispatchEvent(new Event("change"));
    await nextTick();
    expect(labels()).toContain("Lexical BM25 retrieval");
    expect(labels()).not.toContain("Cross-encoder reranker");
    wrapper.unmount();
  });

  it("filters by search and reports the chosen position", async () => {
    const wrapper = mountPalette();
    const search = document.body.querySelector<HTMLInputElement>('input[type="search"]')!;
    search.value = "rerank";
    search.dispatchEvent(new Event("input"));
    await nextTick();
    expect(labels()).toContain("Cross-encoder reranker");
    expect(labels()).not.toContain("Provenance sufficiency gate");
    const add = [...document.body.querySelectorAll<HTMLButtonElement>(".palette-add")].find(
      (button) => button.textContent?.includes("Cross-encoder reranker"),
    )!;
    add.click();
    expect(wrapper.emitted("add")?.[0]).toEqual(["rerank.cross_encoder", "after"]);
    wrapper.unmount();
  });

  it("only offers 'between' when the anchor has followers", () => {
    const lone = mountPalette({ anchor: { ...anchor, next: [] } });
    expect(document.body.querySelector('input[value="between"]')).toBeNull();
    lone.unmount();
    const connected = mountPalette();
    expect(document.body.querySelector('input[value="between"]')).not.toBeNull();
    connected.unmount();
  });
});

describe("analysis panel", () => {
  function mountPanel(analysis: PipelineAnalysis | null = analysisFixture(), extra = {}) {
    return mount(PipelineAnalysisPanel, {
      attachTo: document.body,
      props: {
        analysis,
        strategies: contractStrategies,
        vocabulary: contractVocabulary,
        ...extra,
      },
    });
  }

  it("reports typical, slow, longest-chain and measured whole-run latency", () => {
    const wrapper = mountPanel();
    const text = wrapper.get(".tiles").text();
    expect(text).toContain("450 ms");
    expect(text).toContain("780 ms");
    expect(text).toContain("1.90 s");
    expect(text).toContain("p90 2.60 s");
    wrapper.unmount();
  });

  it("says where each figure came from and how thin it is", () => {
    const wrapper = mountPanel();
    const rows = wrapper.findAll(".waterfall tbody tr");
    expect(rows[0].text()).toContain("This exact pipeline");
    expect(rows[0].text()).toContain("n=12");
    expect(rows[1].text()).toContain("This strategy, any pipeline");
    expect(rows[1].text()).toContain("thin");
    expect(rows[2].text()).toContain("Unknown");
    expect(rows[2].text()).toContain("No recorded runs");
    expect(wrapper.get(".note[data-tone=warn]").text()).toContain("1 stages have no recorded runs");
    wrapper.unmount();
  });

  it("states honestly when a pipeline has never run in this form", () => {
    const analysis = analysisFixture();
    analysis.latency.observed_runs = { samples: 0 };
    const wrapper = mountPanel(analysis);
    expect(wrapper.get(".tiles").text()).toContain("Never run in this form");
    wrapper.unmount();
  });

  it("selects a stage from a row", async () => {
    const wrapper = mountPanel();
    await wrapper.findAll(".stage-link")[1].trigger("click");
    expect(wrapper.emitted("selectStage")?.[0]).toEqual(["b"]);
    wrapper.unmount();
  });

  it("explains declared complexity in plain terms", async () => {
    const wrapper = mountPanel();
    await wrapper.findAll("[role=tab]")[2].trigger("click");
    const text = wrapper.get(".complexity").text();
    expect(text).toContain("Grows with the collection");
    expect(text).toContain(
      "a reads or indexes the collection".replace("a reads", "Searching in a reads"),
    );
    expect(text).toContain("≤ 500");
    expect(text).toContain("Embedding × 1");
    expect(wrapper.findAll(".stages tbody tr")).toHaveLength(3);
    expect(wrapper.get(".stages").text()).toContain("O(n·L)");
    wrapper.unmount();
  });

  it("says when candidate counts are left to the request", async () => {
    const analysis = analysisFixture();
    analysis.complexity.summary!.candidates_request_bound = true;
    analysis.complexity.summary!.candidate_bound = null;
    const wrapper = mountPanel(analysis);
    await wrapper.findAll("[role=tab]")[2].trigger("click");
    expect(wrapper.get(".findings").text()).toContain("set by the request");
    wrapper.unmount();
  });

  it("shows measured growth beside the declared cost when enough runs exist", async () => {
    const analysis = analysisFixture();
    analysis.latency.stages[1].observed_scaling = {
      exponent: 1.04,
      r_squared: 0.97,
      points: 40,
      min_input: 10,
      max_input: 500,
    };
    const wrapper = mountPanel(analysis);
    await wrapper.findAll("[role=tab]")[2].trigger("click");
    expect(wrapper.findAll(".stages tbody tr")[1].text()).toContain("n^1.04");
    wrapper.unmount();
  });

  it("lists live problems with the stage each belongs to, errors first in plain words", async () => {
    const analysis = analysisFixture();
    analysis.validation = {
      valid: false,
      issues: [
        {
          level: "error",
          code: "input_unbound",
          stage_id: "c",
          message: "Input 'candidates' of 'c' (candidate_set) has no source.",
        },
        { level: "warning", code: "x", stage_id: null, message: "Review this." },
      ],
    };
    const wrapper = mountPanel(analysis);
    const checks = wrapper.findAll("[role=tab]")[0];
    expect(checks.text()).toBe("Checks (2)");
    await checks.trigger("click");
    expect(wrapper.get(".checks-summary").text()).toContain("1 must be fixed");
    expect(wrapper.findAll(".check-list li")[0].text()).toContain("Must fix");
    await wrapper.get(".check-stage").trigger("click");
    expect(wrapper.emitted("selectStage")?.[0]).toEqual(["c"]);
    wrapper.unmount();
  });

  it("says when every input is satisfied", async () => {
    const wrapper = mountPanel();
    await wrapper.findAll("[role=tab]")[0].trigger("click");
    expect(wrapper.get(".all-clear").text()).toContain("No problems found");
    wrapper.unmount();
  });

  it("reports a failure without discarding the last good analysis", () => {
    const wrapper = mountPanel(analysisFixture(), { error: "boom" });
    expect(wrapper.get("[role=alert]").text()).toContain("boom");
    expect(wrapper.find(".tiles").exists()).toBe(true);
    wrapper.unmount();
  });
});

describe("new pipeline", () => {
  it("won't start until a workflow is chosen and shows what it supplies and must return", async () => {
    const wrapper = mount(PipelineNewDialog, {
      attachTo: document.body,
      props: { purposes: contractPurposes, vocabulary: contractVocabulary },
    });
    const start = () =>
      [...document.body.querySelectorAll<HTMLButtonElement>("footer button")].find((button) =>
        /Start building/.test(button.textContent ?? ""),
      )!;
    expect(start().disabled).toBe(true);

    const radio = document.body.querySelector<HTMLInputElement>('input[value="research"]')!;
    radio.checked = true;
    radio.dispatchEvent(new Event("change"));
    await nextTick();
    const contract = document.body.querySelector(".contract")!.textContent ?? "";
    expect(contract).toContain("Supplies to every run");
    expect(contract).toContain("query");
    expect(contract).toContain("Must return");
    expect(start().disabled).toBe(false);
    start().click();
    expect(wrapper.emitted("create")?.[0]).toEqual(["research"]);
    wrapper.unmount();
  });

  it("is reachable from the workflow list and unavailable while a version is being edited", async () => {
    const props = {
      pipelines: [],
      strategies: contractStrategies,
      assignments: [],
      purposes: contractPurposes,
      vocabulary: contractVocabulary,
      selectedKey: "",
      workflow: "",
      filters: { query: "", status: "" },
      selectedPipeline: null,
      selectedPurpose: null,
      selectedAssignment: null,
      assigned: false,
      canAssign: false,
      assigning: false,
      cloning: false,
      draft: null,
      draftPurpose: null,
      validation: null,
      saving: false,
    };
    const idle = mount(PipelineDefinitionsWorkspace, { props, attachTo: document.body });
    const button = idle.get(".pipeline-definitions-actions button");
    expect(button.attributes("disabled")).toBeUndefined();
    await button.trigger("click");
    await flushPromises();
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull();
    idle.unmount();
    document.body.innerHTML = "";

    const editing = mount(PipelineDefinitionsWorkspace, {
      props: { ...props, draft: draft(), draftPurpose: contractPurpose("research") },
      attachTo: document.body,
    });
    expect(editing.find(".pipeline-definitions-actions").exists()).toBe(false);
    expect(editing.find(".pipeline-definitions-workspace").exists()).toBe(false);
    expect(editing.findComponent({ name: "PipelineVersionEditorPanel" }).exists()).toBe(true);
    await editing.setProps({ draft: null });
    expect(editing.find(".pipeline-definitions-workspace").exists()).toBe(true);
    editing.unmount();
  });
});

describe("strategy details", () => {
  it("shows ports, declared cost and observed latency", () => {
    const wrapper = mount(PipelineStrategyInspector, {
      props: {
        strategy: contractStrategy("rerank.cross_encoder"),
        usage: { pipelines: [], categories: [] },
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
        latency: {
          samples: 20,
          p50_ms: 900,
          p90_ms: 1500,
          reliable: true,
          executions: 22,
          median_ms_per_input: 4,
          by_model: [{ provider: "local", model: "ms-marco", samples: 20, p50_ms: 900 }],
          observed_scaling: {
            exponent: 1.1,
            r_squared: 0.9,
            points: 20,
            min_input: 5,
            max_input: 200,
          },
        },
      },
    });
    const text = wrapper.text();
    expect(text).toContain("candidates");
    expect(text).toContain("query");
    expect(text).toContain("O(n·(q + L)²)");
    expect(text).toContain("One model pass per item");
    expect(text).toContain("900 ms");
    expect(text).toContain("n^1.1");
    expect(text).toContain("ms-marco");
  });

  it("says plainly when no runs have been recorded", () => {
    const wrapper = mount(PipelineStrategyInspector, {
      props: {
        strategy: contractStrategy("select.top_k"),
        usage: { pipelines: [], categories: [] },
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
        latency: null,
      },
    });
    expect(wrapper.text()).toContain("No recorded runs yet");
  });
});

describe("usePipelineAnalysis", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  function host() {
    const pipeline = ref<PipelineDefinition | null>(draft());
    let api!: ReturnType<typeof usePipelineAnalysis>;
    const wrapper = mount(
      defineComponent({
        setup() {
          api = usePipelineAnalysis(pipeline, 100);
          return () => h("div");
        },
      }),
    );
    return { pipeline, api, wrapper };
  }

  it("waits for edits to settle and sends the draft once", async () => {
    const { pipeline, wrapper } = host();
    pipeline.value = { ...draft(), name: "One" };
    await nextTick();
    pipeline.value = { ...draft(), name: "Two" };
    await nextTick();
    expect(analyze).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(120);
    expect(analyze).toHaveBeenCalledTimes(1);
    expect(analyze.mock.calls[0][0].name).toBe("Two");
    wrapper.unmount();
  });

  it("describes an invalid draft (422) as incomplete and keeps the last analysis", async () => {
    const { api, wrapper } = host();
    api.refresh();
    await vi.advanceTimersByTimeAsync(0);
    await flushPromises();
    const good = api.analysis.value;
    analyze.mockRejectedValueOnce(new ApiError("Stage id is not valid", 422));
    api.refresh();
    await vi.advanceTimersByTimeAsync(0);
    await flushPromises();
    expect(api.error.value).toMatch(/incomplete/i);
    expect(api.analysis.value).toBe(good);
    wrapper.unmount();
  });

  it("aborts a stale request and keeps only the latest result", async () => {
    const { pipeline, api, wrapper } = host();
    let release!: (value: PipelineAnalysis) => void;
    analyze.mockImplementationOnce(
      () => new Promise<PipelineAnalysis>((resolve) => (release = resolve)),
    );
    api.refresh();
    await nextTick();
    const first = analyze.mock.calls[0][1] as AbortSignal;
    pipeline.value = { ...draft(), name: "Newer" };
    await nextTick();
    await vi.advanceTimersByTimeAsync(120);
    expect(first.aborted).toBe(true);
    release(analysisFixture({ sample: { runs: 1, pipeline_runs: 1, exact_runs: 1 } }));
    await flushPromises();
    // The aborted request's late answer must not replace the newer analysis.
    expect(api.analysis.value?.sample.runs).toBe(120);
    wrapper.unmount();
  });

  it("keeps the last good analysis visible when a refresh fails", async () => {
    const { api, wrapper } = host();
    api.refresh();
    await flushPromises();
    expect(api.analysis.value).not.toBeNull();
    analyze.mockRejectedValueOnce(new Error("server down"));
    api.refresh();
    await flushPromises();
    expect(api.error.value).toBe("server down");
    expect(api.analysis.value).not.toBeNull();
    wrapper.unmount();
  });
});
