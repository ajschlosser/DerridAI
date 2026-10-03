/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { queryClient } from "../../src/realtime/dataQuery";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { pipelinesApi } from "../../src/api/pipelines";
import { analysisFixture } from "../../src/components/pipelines/fixtures/pipelineAnalysisFixture";
import PipelineDefinitionNavigator from "../../src/components/pipelines/PipelineDefinitionNavigator.vue";
import PipelineExecutionsWorkspace from "../../src/components/pipelines/PipelineExecutionsWorkspace.vue";
import PipelineOperationsSummary from "../../src/components/pipelines/PipelineOperationsSummary.vue";
import PipelineStageEditor from "../../src/components/pipelines/PipelineStageEditor.vue";
import PipelineStageList from "../../src/components/pipelines/PipelineStageList.vue";
import PipelineStrategiesWorkspace from "../../src/components/pipelines/PipelineStrategiesWorkspace.vue";
import PipelineVersionEditorPanel from "../../src/components/pipelines/PipelineVersionEditorPanel.vue";
import PipelineWorkflowContract from "../../src/components/pipelines/PipelineWorkflowContract.vue";
import {
  contractPurpose,
  contractPurposes,
  contractStrategies,
  contractStrategy,
  contractVocabulary,
} from "../../src/components/pipelines/fixtures/pipelineCatalogContract";
import SystemDataPipelines from "../../src/components/system-data/SystemDataPipelines.vue";
import {
  groupPipelinesByWorkflow,
  pipelinePhaseSequence,
  strategyPickerGroups,
  strategyUsage,
} from "../../src/domain/pipelineWorkflows";
import { useI18nStore } from "../../src/stores/i18n";
import type {
  PipelineCatalog,
  PipelineDefinition,
  PipelineOperationalMetrics,
  PipelineRunTrace,
  PipelineStage,
} from "../../src/types/pipelines";

function stage(id: string, strategy: string, next: string[] = []): PipelineStage {
  return { id, strategy, enabled: true, config: {}, next };
}

function pipeline(
  pipelineId: string,
  purpose: string,
  stages: PipelineStage[],
  extra: Partial<PipelineDefinition> = {},
): PipelineDefinition {
  return {
    pipeline_id: pipelineId,
    version: 1,
    name: pipelineId,
    purpose,
    status: "active",
    entry_stage_ids: [stages[0]?.id || "a"],
    stages,
    built_in: true,
    validation: { valid: true, issues: [] },
    runtime_support: { supported: true, adapter: purpose },
    ...extra,
  };
}

const research = pipeline(
  "research.current",
  "research",
  [
    stage("query", "query.research_decompose", ["dense"]),
    stage("dense", "retrieve.chroma_similarity", ["rerank"]),
    stage("rerank", "rerank.cross_encoder", ["provenance"]),
    stage("provenance", "validate.provenance", ["pack"]),
    stage("pack", "pack.evidence_context", ["generate"]),
    stage("generate", "llm.generate_answer", ["cite"]),
    stage("cite", "validate.citation_binding", ["grade"]),
    stage("grade", "llm.grade_rag"),
  ],
  { name: "Research — current production chain" },
);
const reviewerEvidence = pipeline(
  "evidence.reviewer.current",
  "evidence_suggestion",
  [
    stage("query", "query.evidence_field", ["semantic"]),
    stage("semantic", "retrieve.source_cosine", ["support"]),
    stage("support", "validate.evidence_support", ["provenance"]),
    stage("provenance", "validate.provenance", ["select"]),
    stage("select", "select.top_k"),
  ],
  { name: "Evidence suggestion — reviewer support-gated", version: 2 },
);
const recovery = pipeline(
  "evidence.recovery.cascade",
  "evidence_recovery",
  [stage("lexical", "retrieve.lexical_bm25")],
  { name: "Evidence recovery — relevance cascade" },
);
const storeSearch = pipeline(
  "store_search.similarity",
  "vector_store_search",
  [stage("dense", "retrieve.chroma_similarity")],
  { name: "Vector Store search — similarity" },
);
const pipelines = [research, reviewerEvidence, recovery, storeSearch];

function text(wrapper: { text: () => string }) {
  return wrapper.text().replace(/\s+/g, " ");
}

beforeEach(() => {
  queryClient.clear();
  queryClient.setDefaultOptions({ queries: { retry: false } });
  setActivePinia(createPinia());
  useI18nStore().dictionary = {};
  vi.restoreAllMocks();
  vi.spyOn(pipelinesApi, "strategyLatency").mockResolvedValue({
    strategies: {},
    sampled_run_count: 0,
  });
});

describe("pipeline workflow domain helpers", () => {
  it("groups pipelines under server categories and keeps unregistered purposes visible", () => {
    const legacy = pipeline("legacy.one", "legacy_experiment", [stage("a", "select.top_k")]);
    const { groups, unclassified } = groupPipelinesByWorkflow(
      [...pipelines, legacy],
      contractPurposes,
      contractVocabulary,
    );
    expect(groups.map((group) => group.category.id)).toEqual(["research", "evidence", "search"]);
    expect(groups[1].pipelines.map((item) => item.purpose)).toEqual([
      "evidence_suggestion",
      "evidence_recovery",
    ]);
    expect(unclassified).toEqual([legacy]);
  });

  it("finds which workflows use a strategy without a frontend semantic table", () => {
    const usage = strategyUsage(
      "retrieve.chroma_similarity",
      pipelines,
      contractPurposes,
      contractVocabulary,
    );
    expect(usage.pipelines.map((item) => item.pipeline_id)).toEqual([
      "research.current",
      "store_search.similarity",
    ]);
    expect(usage.categories).toEqual(["research", "search"]);
  });

  it("splits the picker by the purpose adapter's compatibility", () => {
    const groups = strategyPickerGroups(contractStrategies, contractPurpose("evidence_suggestion"));
    const ids = (key: keyof typeof groups) => groups[key].map((item) => item.strategy_id);
    expect(ids("supported")).toContain("validate.evidence_support");
    expect(ids("output_contract")).toContain("llm.generate_answer");
    expect(ids("supported")).toContain("select.mmr");
  });

  it("reads phases from the actual graph, repeating validation after generation", () => {
    expect(pipelinePhaseSequence(research, contractStrategies)).toEqual([
      "prepare",
      "find",
      "rank",
      "validate",
      "select",
      "generate",
      "validate",
      "evaluate",
    ]);
    expect(pipelinePhaseSequence(reviewerEvidence, contractStrategies)).toEqual([
      "prepare",
      "find",
      "validate",
      "select",
    ]);
  });
});

describe("workflow navigator", () => {
  function mountNavigator(workflow = "") {
    return mount(PipelineDefinitionNavigator, {
      props: {
        pipelines,
        assignments: [],
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
        selectedKey: "",
        workflow,
      },
    });
  }

  it("offers Used for categories from catalog metadata with counts", async () => {
    const wrapper = mountNavigator();
    const select = wrapper.findAll("select")[0];
    const options = select.findAll("option");
    expect(options.map((item) => item.attributes("value"))).toEqual([
      "",
      ...contractVocabulary.categories.map((term) => term.id),
    ]);
    const evidence = options.find((item) => item.attributes("value") === "evidence")!;
    expect(text(evidence)).toContain("Evidence (2)");
    await select.setValue("evidence");
    expect(wrapper.emitted("update:workflow")).toEqual([["evidence"]]);
  });

  it("filters to one workflow while keeping precise purposes distinguishable", () => {
    const wrapper = mountNavigator("evidence");
    const choices = wrapper.findAll(".pipeline-choice").map((item) => text(item));
    expect(choices).toHaveLength(2);
    expect(choices[0]).toContain("Reviewer evidence suggestion");
    expect(choices[1]).toContain("Evidence recovery");
    expect(text(wrapper)).not.toContain("Research — current production chain");
  });

  it("searches by localized purpose label through the filters prop", async () => {
    const wrapper = mountNavigator();
    await wrapper.get('input[type="search"]').setValue("vector store");
    expect(wrapper.emitted("update:filters")).toEqual([[{ query: "vector store", status: "" }]]);
    await wrapper.setProps({ filters: { query: "vector store", status: "" } });
    expect(wrapper.findAll(".pipeline-choice")).toHaveLength(1);
  });

  it("groups immutable versions under one pipeline and selects exact versions", async () => {
    const research = pipelines.find((item) => item.purpose === "research")!;
    const wrapper = mount(PipelineDefinitionNavigator, {
      props: {
        pipelines: [
          research,
          { ...structuredClone(research), version: research.version + 1, status: "draft" },
        ],
        assignments: [],
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
        selectedKey: "",
      },
    });
    expect(wrapper.findAll(".pipeline-choice")).toHaveLength(1);
    expect(text(wrapper)).toContain("1 pipelines · 2 versions");
    expect(wrapper.find(".version-list").exists()).toBe(false);
    await wrapper.get(".version-toggle").trigger("click");
    const versions = wrapper.findAll(".version-choice");
    expect(versions.map((item) => text(item))).toEqual([
      expect.stringContaining(`v${research.version + 1}`),
      expect.stringContaining(`v${research.version}`),
    ]);
    await versions[0].trigger("click");
    expect(wrapper.emitted("select")).toEqual([
      [`${research.pipeline_id}@${research.version + 1}`],
    ]);
    // Selecting the group opens the highest active executable version, not the draft.
    await wrapper.get(".pipeline-choice").trigger("click");
    expect(wrapper.emitted("select")!.at(-1)).toEqual([
      `${research.pipeline_id}@${research.version}`,
    ]);
  });
});

describe("workflow contract panel", () => {
  function mountContract(purposeId: string, subject: PipelineDefinition) {
    return mount(PipelineWorkflowContract, {
      props: {
        pipeline: subject,
        purpose: contractPurpose(purposeId),
        vocabulary: contractVocabulary,
      },
    });
  }

  it("states evidence input, output, authority and guarantees", () => {
    const wrapper = mountContract("evidence_suggestion", reviewerEvidence);
    const content = text(wrapper);
    expect(content).toContain("What this pipeline does");
    expect(content).toContain("Used forEvidenceReviewer evidence suggestion");
    expect(content).toContain("Record review → Evidence suggestions");
    expect(content).toContain("Advisory source candidates.");
    expect(content).toContain("Relevance ranking alone never makes a candidate evidence");
    expect(content).toContain("Direct support");
    expect(content).toContain("Source provenance");
  });

  it("says a Research pipeline generates a cited response", () => {
    const content = text(mountContract("research", research));
    expect(content).toContain("Research workspace");
    expect(content).toContain("generated research response");
  });

  it("says Vector Store search does not establish evidence", () => {
    const content = text(mountContract("vector_store_search", storeSearch));
    expect(content).toContain("Search results do not establish evidence");
  });

  it("resolves copy through server locale keys", () => {
    useI18nStore().dictionary = {
      [contractPurpose("research").authority_key]: "⟦autorité⟧",
      "pipelines.contract_title": "⟦titre⟧",
    };
    const content = text(mountContract("research", research));
    expect(content).toContain("⟦autorité⟧");
    expect(content).toContain("⟦titre⟧");
  });
});

describe("strategies workspace", () => {
  const noFilters = {
    query: "",
    family: "",
    computation: "",
    capability: "",
    effect: "",
    workflow: "",
  };
  function mountCatalog(selectedStrategyId = "") {
    const wrapper = mount(PipelineStrategiesWorkspace, {
      props: {
        strategies: contractStrategies,
        pipelines,
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
        selectedStrategyId,
        filters: noFilters,
      },
    });
    return wrapper;
  }
  async function filter(wrapper: ReturnType<typeof mountCatalog>, patch: object) {
    await wrapper.setProps({ filters: { ...noFilters, ...patch } });
  }
  const rowIds = (wrapper: ReturnType<typeof mountCatalog>) =>
    wrapper.findAll("tbody tr").map((row) => row.attributes("data-strategy"));

  it("finds semantic strategies with family, types, requirements, effect and usage", async () => {
    const wrapper = mountCatalog("retrieve.chroma_similarity");
    await filter(wrapper, { query: "semantic" });
    expect(rowIds(wrapper)).toContain("retrieve.chroma_similarity");
    expect(rowIds(wrapper)).toContain("retrieve.source_cosine");
    expect(rowIds(wrapper)).not.toContain("validate.evidence_support");
    const chroma = text(wrapper.get('tr[data-strategy="retrieve.chroma_similarity"]'));
    expect(chroma).toContain("Candidate generation");
    expect(chroma).toContain("Produces candidates — not evidence");
    const inspector = text(wrapper.get(".strategy-inspector"));
    expect(inspector).toMatch(/Query →\s*(to)?\s*Candidate set/);
    expect(inspector).toContain("RequiresEmbedding model, Chroma");
    expect(inspector).toContain("Produces candidates — not evidence");
    expect(inspector).toContain("Used byResearch, Search");
  });

  it("separates a cross-encoder's relevance from direct support", async () => {
    const wrapper = mountCatalog();
    expect(text(wrapper.get('tr[data-strategy="rerank.cross_encoder"]'))).toContain(
      "Relevance ranking only — does not establish support",
    );
    expect(text(wrapper.get('tr[data-strategy="validate.evidence_support"]'))).toContain(
      "Evidence eligibility gate",
    );
  });

  it("keeps the strategy catalog scannable with four grouped columns", () => {
    const wrapper = mountCatalog();
    expect(
      wrapper
        .findAll(".strategy-table thead th")
        .map((column) => column.attributes("data-column")),
    ).toEqual(["strategy", "family", "flow", "usage"]);

    const row = wrapper.get('tr[data-strategy="retrieve.chroma_similarity"]');
    expect(row.findAll("[data-column]")).toHaveLength(4);
    expect(row.find("[data-column=\"strategy\"] .strategy-effect").exists()).toBe(true);
    expect(row.find("[data-column=\"family\"] .computation-label").exists()).toBe(true);
    expect(row.findAll("[data-column=\"flow\"] .type-chip")).toHaveLength(2);
  });

  it("selects a row from the keyboard-focusable control and emits the strategy", async () => {
    const wrapper = mountCatalog();
    await wrapper.get('tr[data-strategy="validate.evidence_support"] .row-select').trigger("click");
    expect(wrapper.emitted("selectStrategy")).toEqual([["validate.evidence_support"]]);
  });

  it("filters by scholarly effect and opens a pipeline that uses a strategy", async () => {
    const wrapper = mountCatalog();
    await filter(wrapper, { effect: "eligibility_gate" });
    expect(rowIds(wrapper)).toEqual(["validate.evidence_support"]);
    await wrapper.get(".strategy-inspector .link-button").trigger("click");
    expect(wrapper.emitted("openPipeline")).toEqual([["evidence.reviewer.current@2"]]);
  });

  it("counts active advanced filters on the Filters control", async () => {
    const wrapper = mountCatalog();
    expect(wrapper.text()).toContain("Filters");
    await filter(wrapper, { computation: "deterministic", workflow: "evidence" });
    expect(wrapper.text()).toContain("Filters (2)");
  });

  it("shows an explicit empty state", async () => {
    const wrapper = mountCatalog();
    await filter(wrapper, { query: "no-such-operation" });
    expect(text(wrapper)).toContain("No strategies match these filters.");
  });
});

describe("stage semantics", () => {
  it("tells reviewers that evidence-candidate stages are not evidence", () => {
    const wrapper = mount(PipelineStageList, {
      props: {
        pipeline: reviewerEvidence,
        strategies: contractStrategies,
        vocabulary: contractVocabulary,
      },
    });
    const effects = wrapper.findAll(".stage-effect").map((item) => text(item));
    expect(effects[1]).toContain("Produces candidates — not evidence");
    expect(effects[2]).toContain("Evidence eligibility gate");
    expect(effects[3]).toContain("Provenance gate");
  });
});

describe("purpose-aware editing", () => {
  function mountStageEditor(strategy: string, showAllStrategies = false) {
    return mount(PipelineStageEditor, {
      props: {
        stage: stage("s", strategy),
        stageIndex: 0,
        stages: [stage("s", strategy)],
        strategies: contractStrategies,
        entryStageIds: ["s"],
        purpose: contractPurpose("evidence_suggestion"),
        showAllStrategies,
      },
    });
  }

  it("offers supported operations first and hides others until asked", () => {
    const wrapper = mountStageEditor("validate.evidence_support");
    const groups = wrapper.findAll("optgroup");
    expect(groups.map((group) => group.attributes("data-fit"))).toEqual(["supported"]);
    expect(wrapper.find('option[value="llm.generate_answer"]').exists()).toBe(false);
    expect(wrapper.find(".stage-fit-note").exists()).toBe(false);
  });

  it("disables operations that would change the workflow's output and explains why", () => {
    const wrapper = mountStageEditor("llm.generate_answer", true);
    expect(wrapper.findAll("optgroup").map((group) => group.attributes("data-fit"))).toEqual([
      "supported",
      "inspect_only",
      "output_contract",
    ]);
    expect(wrapper.get('option[value="llm.grade_rag"]').attributes("disabled")).toBeDefined();
    const note = wrapper.get(".stage-fit-note");
    expect(text(note)).toContain(
      "Research answer generation produces Model output, but a Reviewer evidence suggestion pipeline must return Candidate set.",
    );
    expect(wrapper.get("select").attributes("aria-describedby")).toBe(note.attributes("id"));
  });

  it("marks an inspect-only strategy on the current stage", () => {
    const wrapper = mountStageEditor("select.source_diversity");
    expect(wrapper.find('option[value="select.source_diversity"]').exists()).toBe(true);
    expect(text(wrapper.get(".stage-fit-note"))).toContain(
      "is not run by the Reviewer evidence suggestion adapter",
    );
  });

  it("keeps the clone's purpose visible and fixed", () => {
    const wrapper = mount(PipelineVersionEditorPanel, {
      props: {
        modelValue: { ...reviewerEvidence, status: "draft", built_in: false },
        strategies: contractStrategies,
        purpose: contractPurpose("evidence_suggestion"),
        vocabulary: contractVocabulary,
        validation: null,
        saving: false,
      },
    });
    expect(text(wrapper.get(".detail-kicker"))).toBe("Evidence · Reviewer evidence suggestion");
    expect(text(wrapper)).toContain("Purpose is fixed for this version.");
  });
});

const evidenceRun: PipelineRunTrace = {
  run_id: "run-evidence",
  feature: "evidence_suggestion.reviewer",
  pipeline_id: "evidence.reviewer.current",
  pipeline_version: 2,
  resolved_pipeline: {},
  resolved_hash: "a".repeat(64),
  status: "completed",
  started_at: "2026-09-29T12:00:00Z",
  stages: [],
};

describe("executions workspace", () => {
  it("leads with the workflow and keeps the feature ID as technical detail", async () => {
    const wrapper = mount(PipelineExecutionsWorkspace, {
      props: {
        runs: [evidenceRun],
        pipelines,
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
        strategies: contractStrategies,
        selectedRunId: "run-evidence",
        focusedRun: null,
        total: 1,
        limit: 25,
        offset: 0,
        filters: { query: "", category: "", feature: "", pipelineId: "", status: "", owner: "" },
      },
    });
    const row = text(wrapper.get("tbody tr"));
    expect(text(wrapper.get(".run-workflow strong"))).toBe("Evidence");
    expect(text(wrapper.get(".run-workflow span"))).toBe("Reviewer evidence suggestion");
    expect(row).not.toContain("evidence_suggestion.reviewer");
    const summary = wrapper.get(".trace-summary");
    expect(text(summary.get(".trace-workflow"))).toBe("Evidence·Reviewer evidence suggestion");
    expect(text(wrapper.get(".trace-technical"))).toContain("evidence_suggestion.reviewer");

    const category = wrapper.findAll(".trace-filters select")[0];
    await category.setValue("evidence");
    const filtersButton = wrapper
      .findAll(".trace-filters button")
      .find((button) => button.text() === "Filters")!;
    await filtersButton.trigger("click");
    const purpose = wrapper.get(".filter-advanced select");
    const purposes = purpose.findAll("option").map((option) => option.attributes("value"));
    expect(purposes).toEqual([
      "",
      "evidence_suggestion.reviewer",
      "evidence_recovery",
      "precedent_evidence_remap",
      "corpus_reviewer_evidence_choice",
    ]);
    await wrapper.get(".trace-filters").trigger("submit");
    expect(wrapper.emitted("apply")?.[0]?.[0]).toMatchObject({ category: "evidence", feature: "" });
  });

  it("puts destructive actions behind menus instead of permanent buttons", async () => {
    const wrapper = mount(PipelineExecutionsWorkspace, {
      props: {
        runs: [evidenceRun],
        pipelines,
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
        strategies: contractStrategies,
        selectedRunId: "run-evidence",
        focusedRun: null,
        total: 1,
        limit: 25,
        offset: 0,
        filters: { query: "", category: "", feature: "", pipelineId: "", status: "", owner: "" },
      },
    });
    expect(wrapper.find(".row-delete").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Clear history");

    await wrapper.get(".run-actions .ui-menu-trigger").trigger("click");
    const items = wrapper.findAll('[role="menuitem"]');
    expect(items.map((item) => item.text())).toEqual([
      expect.stringContaining("Open configuration"),
      "Delete execution",
    ]);
    await items[1].trigger("click");
    expect(wrapper.emitted("deleteRun")).toEqual([["run-evidence"]]);

    const more = wrapper
      .findAll(".trace-filters .ui-menu-trigger")
      .find((button) => button.text().includes("More"))!;
    await more.trigger("click");
    await wrapper
      .findAll('[role="menuitem"]')
      .find((item) => item.text() === "Clear execution history")!
      .trigger("click");
    expect(wrapper.emitted("clearHistory")).toHaveLength(1);
  });
});

describe("operations", () => {
  it("summarizes workflows separately from strategies", () => {
    const metrics: PipelineOperationalMetrics = {
      sampled_run_count: 2,
      status_counts: { completed: 2 },
      fallback_run_count: 0,
      warning_run_count: 0,
      workflows: [
        {
          category: "evidence",
          features: ["evidence_suggestion.reviewer"],
          run_count: 2,
          failed_count: 0,
          fallback_run_count: 0,
          warning_run_count: 0,
          p95_elapsed_ms: 40,
        },
      ],
      features: [
        {
          feature: "evidence_suggestion.reviewer",
          run_count: 2,
          failed_count: 0,
          fallback_run_count: 0,
          warning_run_count: 0,
        },
      ],
      strategies: [
        {
          strategy_id: "rerank.cross_encoder",
          stage_ids: ["rerank"],
          executions: 2,
          fallback_count: 0,
          warning_count: 0,
          model_call_count: 2,
          issue_count: 0,
          status_counts: { completed: 2 },
        },
      ],
      sample_limit: 250,
    };
    const wrapper = mount(PipelineOperationsSummary, {
      props: {
        metrics,
        strategies: contractStrategies,
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
      },
    });
    const workflow = text(wrapper.get('[data-category="evidence"]'));
    expect(workflow).toContain("Evidence");
    expect(workflow).toContain("Reviewer evidence suggestion");
    expect(text(wrapper)).toContain("not the scholarly validity of retrieved evidence");
    expect(text(wrapper)).not.toContain("do not mean a workflow produces better scholarship");
    expect(text(wrapper)).toContain("Cross-encoder reranker");
  });
});

describe("Pipeline Studio routes", () => {
  const catalog: PipelineCatalog = {
    purposes: contractPurposes,
    vocabulary: contractVocabulary,
    strategies: contractStrategies,
    pipelines,
    assignments: [
      {
        feature: "evidence_suggestion.reviewer",
        pipeline_id: "evidence.reviewer.current",
        pipeline_version: 2,
        scope: "system",
        scope_id: null,
        override_allowed: true,
        source: "built_in",
      },
    ],
  };

  async function mountStudio(query: Record<string, string>) {
    vi.spyOn(pipelinesApi, "catalog").mockResolvedValue(structuredClone(catalog));
    vi.spyOn(pipelinesApi, "analyze").mockResolvedValue(analysisFixture());
    vi.spyOn(pipelinesApi, "runs").mockResolvedValue({
      runs: [structuredClone(evidenceRun)],
      limit: 25,
      offset: 0,
      total: 1,
    });
    vi.spyOn(pipelinesApi, "metrics").mockResolvedValue({
      sampled_run_count: 0,
      status_counts: {},
      fallback_run_count: 0,
      warning_run_count: 0,
      workflows: [],
      features: [],
      strategies: [],
      sample_limit: 250,
    });
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/pipelines", name: "pipelines", component: SystemDataPipelines }],
    });
    await router.push({ name: "pipelines", query });
    await router.isReady();
    const wrapper = mount(SystemDataPipelines, {
      global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();
    return { wrapper, router };
  }

  it("keeps the workflow filter and strategy selection in the URL", async () => {
    const { wrapper, router } = await mountStudio({ workflow: "evidence" });
    expect(wrapper.findAll(".pipeline-choice")).toHaveLength(2);
    await wrapper.findAll("select")[0].setValue("search");
    await flushPromises();
    expect(router.currentRoute.value.query.workflow).toBe("search");

    await wrapper.get("#pipeline-tab-strategies").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.section).toBe("strategies");
    expect(wrapper.get("#pipeline-tab-strategies").attributes("aria-selected")).toBe("true");
    await wrapper.get('tr[data-strategy="rerank.cross_encoder"] .row-select').trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.strategy).toBe("rerank.cross_encoder");
  });

  it("assigns through the purpose's consuming feature", async () => {
    const assign = vi.spyOn(pipelinesApi, "setAssignment").mockResolvedValue({
      assignment: catalog.assignments[0],
    });
    catalog.pipelines.push({
      ...structuredClone(reviewerEvidence),
      pipeline_id: "evidence.reviewer.current.custom",
      name: "Custom reviewer evidence",
      built_in: false,
    });
    const { wrapper } = await mountStudio({ pipeline: "evidence.reviewer.current.custom@2" });
    await wrapper
      .findAll(".detail-actions button")
      .find((item) => item.text().includes("Make active"))!
      .trigger("click");
    await flushPromises();
    catalog.pipelines.pop();
    expect(assign).toHaveBeenCalledWith(
      expect.objectContaining({
        feature: "evidence_suggestion.reviewer",
        pipeline_id: "evidence.reviewer.current.custom",
        override_allowed: true,
      }),
    );
  });

  it("sends the execution workflow filter to the server", async () => {
    await mountStudio({ section: "executions", run_workflow: "evidence" });
    expect(pipelinesApi.runs).toHaveBeenCalledWith(
      expect.objectContaining({ category: "evidence" }),
    );
  });

  it("shows loading before the catalog arrives", async () => {
    vi.spyOn(pipelinesApi, "catalog").mockReturnValue(new Promise(() => {}));
    vi.spyOn(pipelinesApi, "metrics").mockReturnValue(new Promise(() => {}));
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/pipelines", name: "pipelines", component: SystemDataPipelines }],
    });
    await router.push({ name: "pipelines" });
    const wrapper = mount(SystemDataPipelines, {
      global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();
    expect(wrapper.get('[role="status"]').text()).toContain("Loading");
  });

  it("reports a catalog error", async () => {
    vi.spyOn(pipelinesApi, "catalog").mockRejectedValue(new Error("catalog offline"));
    vi.spyOn(pipelinesApi, "metrics").mockResolvedValue({} as PipelineOperationalMetrics);
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/pipelines", name: "pipelines", component: SystemDataPipelines }],
    });
    await router.push({ name: "pipelines" });
    const wrapper = mount(SystemDataPipelines, {
      global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
    });
    await vi.waitFor(() =>
      expect(wrapper.get('[role="alert"]').text()).toContain("catalog offline"),
    );
  });
});

// Ensure the fixture helper rejects unknown IDs rather than inventing contracts.
describe("catalog contract fixture", () => {
  it("throws for an unknown strategy", () => {
    expect(() => contractStrategy("missing.strategy")).toThrow(/Unknown strategy/);
  });
});
