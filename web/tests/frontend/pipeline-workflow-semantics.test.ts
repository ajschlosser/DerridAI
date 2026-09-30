/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { pipelinesApi } from "../../src/api/pipelines";
import PipelineDefinitionBrowser from "../../src/components/pipelines/PipelineDefinitionBrowser.vue";
import PipelineExecutionHistory from "../../src/components/pipelines/PipelineExecutionHistory.vue";
import PipelineOperationsSummary from "../../src/components/pipelines/PipelineOperationsSummary.vue";
import PipelineStageEditor from "../../src/components/pipelines/PipelineStageEditor.vue";
import PipelineStageList from "../../src/components/pipelines/PipelineStageList.vue";
import PipelineStrategyCatalog from "../../src/components/pipelines/PipelineStrategyCatalog.vue";
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
  setActivePinia(createPinia());
  useI18nStore().dictionary = {};
  vi.restoreAllMocks();
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
    expect(ids("inspect_only")).toContain("select.mmr");
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

describe("workflow browser", () => {
  function mountBrowser(workflow = "") {
    return mount(PipelineDefinitionBrowser, {
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

  it("renders Used for categories from catalog metadata with counts", async () => {
    const wrapper = mountBrowser();
    const group = wrapper.get('[role="group"]');
    expect(group.attributes("aria-label")).toBe("Used for");
    const options = group.findAll("button");
    expect(options.map((item) => item.attributes("data-category") || "all")).toEqual([
      "all",
      ...contractVocabulary.categories.map((term) => term.id),
    ]);
    const evidence = group.get('[data-category="evidence"]');
    expect(text(evidence)).toContain("Evidence 2");
    expect(evidence.attributes("aria-pressed")).toBe("false");
    await evidence.trigger("click");
    expect(wrapper.emitted("update:workflow")).toEqual([["evidence"]]);
  });

  it("filters to one workflow while keeping precise purposes distinguishable", () => {
    const wrapper = mountBrowser("evidence");
    expect(wrapper.get('[data-category="evidence"]').attributes("aria-pressed")).toBe("true");
    const choices = wrapper.findAll(".pipeline-choice").map((item) => text(item));
    expect(choices).toHaveLength(2);
    expect(choices[0]).toContain("Reviewer evidence suggestion");
    expect(choices[1]).toContain("Evidence recovery");
    expect(text(wrapper)).not.toContain("Research — current production chain");
  });

  it("searches by localized purpose label", async () => {
    const wrapper = mountBrowser();
    await wrapper.get('input[type="search"]').setValue("vector store");
    expect(wrapper.findAll(".pipeline-choice")).toHaveLength(1);
  });
});

describe("workflow contract panel", () => {
  function mountContract(purposeId: string, subject: PipelineDefinition) {
    return mount(PipelineWorkflowContract, {
      props: {
        pipeline: subject,
        purpose: contractPurpose(purposeId),
        vocabulary: contractVocabulary,
        assignment: null,
        assigned: false,
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

describe("strategy catalog", () => {
  function mountCatalog() {
    return mount(PipelineStrategyCatalog, {
      props: {
        strategies: contractStrategies,
        pipelines,
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
      },
    });
  }

  it("finds semantic strategies with family, types, requirements, effect and usage", async () => {
    const wrapper = mountCatalog();
    await wrapper.get('input[type="search"]').setValue("semantic");
    const ids = wrapper.findAll(".strategy-card").map((card) => card.attributes("data-strategy"));
    expect(ids).toContain("retrieve.chroma_similarity");
    expect(ids).toContain("retrieve.source_cosine");
    expect(ids).not.toContain("validate.evidence_support");
    const chroma = text(wrapper.get('[data-strategy="retrieve.chroma_similarity"]'));
    expect(chroma).toContain("Candidate generation");
    expect(chroma).toMatch(/Query →\s*(to)?\s*Candidate set/);
    expect(chroma).toContain("RequiresEmbedding model, Chroma");
    expect(chroma).toContain("Advisory only");
    expect(chroma).toContain("Produces candidates — not evidence");
    expect(chroma).toContain("Used byResearch, Search");
  });

  it("separates a cross-encoder's relevance from direct support", async () => {
    const wrapper = mountCatalog();
    const rerank = text(wrapper.get('[data-strategy="rerank.cross_encoder"]'));
    expect(rerank).toContain("Relevance ranking only — does not establish support");
    const support = text(wrapper.get('[data-strategy="validate.evidence_support"]'));
    expect(support).toContain("Evidence eligibility gate");
    expect(support).toContain("Used byEvidence");
  });

  it("filters by scholarly effect and opens a pipeline that uses a strategy", async () => {
    const wrapper = mountCatalog();
    const selects = wrapper.findAll("select");
    const effect = selects.find((item) =>
      item.findAll("option").some((option) => option.attributes("value") === "eligibility_gate"),
    );
    await effect!.setValue("eligibility_gate");
    const cards = wrapper.findAll(".strategy-card");
    expect(cards.map((card) => card.attributes("data-strategy"))).toEqual([
      "validate.evidence_support",
    ]);
    await cards[0].get(".link-button").trigger("click");
    expect(wrapper.emitted("openPipeline")).toEqual([["evidence.reviewer.current@2"]]);
  });

  it("shows an explicit empty state", async () => {
    const wrapper = mountCatalog();
    await wrapper.get('input[type="search"]').setValue("no-such-operation");
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
    const wrapper = mountStageEditor("select.mmr");
    expect(wrapper.find('option[value="select.mmr"]').exists()).toBe(true);
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
    const content = text(wrapper);
    expect(text(wrapper.get(".purpose-line"))).toBe(
      "Used forEvidence·Reviewer evidence suggestion",
    );
    expect(content).toContain("This new version remains a Reviewer evidence suggestion pipeline.");
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

describe("execution history", () => {
  it("leads with the workflow and keeps the feature ID as technical detail", async () => {
    const wrapper = mount(PipelineExecutionHistory, {
      props: {
        runs: [evidenceRun],
        pipelines,
        purposes: contractPurposes,
        vocabulary: contractVocabulary,
        strategies: contractStrategies,
        selectedRunId: "run-evidence",
      },
    });
    const row = text(wrapper.get("tbody tr"));
    expect(text(wrapper.get(".run-workflow strong"))).toBe("Evidence");
    expect(text(wrapper.get(".run-workflow span"))).toBe("Reviewer evidence suggestion");
    expect(row).not.toContain("evidence_suggestion.reviewer");
    const summary = wrapper.get(".trace-summary");
    expect(text(summary.get(".trace-workflow"))).toBe("Evidence·Reviewer evidence suggestion");
    expect(text(summary.get(".trace-technical"))).toContain("evidence_suggestion.reviewer");

    const [category, purpose] = wrapper.findAll(".trace-filters select");
    await category.setValue("evidence");
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
    expect(text(wrapper)).toContain("do not mean a workflow produces better scholarship");
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
    const wrapper = mount(SystemDataPipelines, { global: { plugins: [router] } });
    await flushPromises();
    return { wrapper, router };
  }

  it("keeps the workflow filter and strategy selection in the URL", async () => {
    const { wrapper, router } = await mountStudio({ workflow: "evidence" });
    expect(wrapper.findAll(".pipeline-choice")).toHaveLength(2);
    await wrapper.get('.workflow-filter [data-category="search"]').trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.workflow).toBe("search");

    await wrapper.get("#pipeline-tab-strategies").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.section).toBe("strategies");
    expect(wrapper.get("#pipeline-tab-strategies").attributes("aria-selected")).toBe("true");
    const card = wrapper.get('[data-strategy="rerank.cross_encoder"] .strategy-technical');
    (card.element as HTMLDetailsElement).open = true;
    await card.trigger("toggle");
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
      .findAll(".detail-actions .btn")
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
    const wrapper = mount(SystemDataPipelines, { global: { plugins: [router] } });
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
    const wrapper = mount(SystemDataPipelines, { global: { plugins: [router] } });
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain("catalog offline");
  });
});

// Ensure the fixture helper rejects unknown IDs rather than inventing contracts.
describe("catalog contract fixture", () => {
  it("throws for an unknown strategy", () => {
    expect(() => contractStrategy("missing.strategy")).toThrow(/Unknown strategy/);
  });
});
