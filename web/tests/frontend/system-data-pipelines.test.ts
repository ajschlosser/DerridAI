/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { chromaApi } from "../../src/api/chroma";
import { pipelinesApi } from "../../src/api/pipelines";
import SystemDataPipelines from "../../src/components/system-data/SystemDataPipelines.vue";
import { pipelineKey } from "../../src/domain/pipelinePresentation";
import {
  contractPurposes,
  contractStrategy,
  contractVocabulary,
} from "../../src/components/pipelines/fixtures/pipelineCatalogContract";
import { queryClient } from "../../src/realtime/dataQuery";
import { dataKey } from "../../src/realtime/resourceKeys";
import { useI18nStore } from "../../src/stores/i18n";
import type {
  PipelineCatalog,
  PipelineOperationalMetrics,
  PipelineRunTrace,
} from "../../src/types/pipelines";

const catalog: PipelineCatalog = {
  purposes: contractPurposes,
  vocabulary: contractVocabulary,
  strategies: [
    "retrieve.chroma_similarity",
    "validate.provenance",
    "pack.evidence_context",
    "llm.generate_answer",
  ].map(contractStrategy),
  pipelines: [
    {
      pipeline_id: "research.current",
      version: 1,
      name: "Research — current production chain",
      purpose: "research",
      status: "active",
      entry_stage_ids: ["dense"],
      built_in: true,
      stages: [
        {
          id: "dense",
          strategy: "retrieve.chroma_similarity",
          enabled: true,
          config: { fetch_k: 500 },
          next: ["provenance"],
        },
        {
          id: "provenance",
          strategy: "validate.provenance",
          enabled: true,
          config: {},
          next: ["pack"],
        },
        {
          id: "pack",
          strategy: "pack.evidence_context",
          enabled: true,
          config: {},
          next: ["generate"],
        },
        {
          id: "generate",
          strategy: "llm.generate_answer",
          enabled: true,
          config: {},
          next: [],
        },
      ],
      validation: { valid: true, issues: [] },
      runtime_support: { supported: true, adapter: "research" },
    },
    {
      pipeline_id: "research.custom",
      version: 2,
      name: "Research — custom",
      purpose: "research",
      status: "active",
      entry_stage_ids: ["dense"],
      built_in: false,
      stages: [
        {
          id: "dense",
          strategy: "retrieve.chroma_similarity",
          enabled: true,
          config: { fetch_k: 250 },
          next: ["provenance"],
        },
        {
          id: "provenance",
          strategy: "validate.provenance",
          enabled: true,
          config: {},
          next: ["pack"],
        },
        {
          id: "pack",
          strategy: "pack.evidence_context",
          enabled: true,
          config: {},
          next: ["generate"],
        },
        {
          id: "generate",
          strategy: "llm.generate_answer",
          enabled: true,
          config: {},
          next: [],
        },
      ],
      validation: { valid: true, issues: [] },
      runtime_support: { supported: true, adapter: "research" },
    },
  ],
  assignments: [
    {
      feature: "research",
      pipeline_id: "research.current",
      pipeline_version: 1,
      scope: "system",
      scope_id: null,
      override_allowed: true,
      source: "built_in",
    },
  ],
};

const metrics: PipelineOperationalMetrics = {
  sampled_run_count: 3,
  status_counts: { completed: 2, failed: 1 },
  fallback_run_count: 1,
  warning_run_count: 1,
  average_run_elapsed_ms: 900,
  p95_run_elapsed_ms: 1400,
  workflows: [
    {
      category: "research",
      features: ["research"],
      run_count: 3,
      failed_count: 1,
      fallback_run_count: 1,
      warning_run_count: 1,
      average_elapsed_ms: 900,
      p95_elapsed_ms: 1400,
    },
  ],
  features: [
    {
      feature: "research",
      run_count: 3,
      failed_count: 1,
      fallback_run_count: 1,
      warning_run_count: 1,
      average_elapsed_ms: 900,
      p95_elapsed_ms: 1400,
    },
  ],
  strategies: [
    {
      strategy_id: "retrieve.chroma_similarity",
      stage_ids: ["dense"],
      executions: 3,
      fallback_count: 1,
      warning_count: 1,
      model_call_count: 0,
      issue_count: 1,
      status_counts: { completed: 2, unavailable: 1 },
      average_elapsed_ms: 55,
      p95_elapsed_ms: 80,
      average_input_count: 1,
      average_output_count: 18,
    },
  ],
  sample_limit: 250,
  feature_filter: null,
  owner_filter: null,
};

const trace: PipelineRunTrace = {
  run_id: "rag-1",
  feature: "research",
  pipeline_id: "research.current",
  pipeline_version: 1,
  resolved_pipeline: {},
  resolved_hash: "abc",
  status: "completed",
  started_at: "2026-09-28T12:00:00Z",
  finished_at: "2026-09-28T12:00:01Z",
  total_elapsed_ms: 1000,
  stages: [
    {
      stage_id: "dense",
      strategy_id: "retrieve.chroma_similarity",
      strategy_version: 1,
      status: "completed",
      elapsed_ms: 50,
      input_count: 1,
      output_count: 20,
      parameters: {},
      collection: "primary",
    },
  ],
};

async function mountStudio(query: Record<string, string> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/pipelines",
        name: "pipelines",
        component: { template: "<div />" },
      },
    ],
  });
  await router.push({ name: "pipelines", query });
  await router.isReady();
  const wrapper = mount(SystemDataPipelines, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  });
  await flushPromises();
  return { wrapper, router };
}

describe("System Data Pipeline Studio", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    queryClient.clear();
    useI18nStore().dictionary = {};
    vi.restoreAllMocks();
    vi.spyOn(pipelinesApi, "catalog").mockResolvedValue(structuredClone(catalog));
    vi.spyOn(pipelinesApi, "runs").mockResolvedValue({
      runs: [structuredClone(trace)],
      limit: 30,
      offset: 0,
      total: 1,
    });
    vi.spyOn(pipelinesApi, "metrics").mockResolvedValue(structuredClone(metrics));
    vi.spyOn(chromaApi, "collections").mockResolvedValue([] as never);
    vi.spyOn(pipelinesApi, "researchBenchmarkCases").mockResolvedValue({
      cases: [],
      limit: 200,
      offset: 0,
    });
    vi.spyOn(pipelinesApi, "cloneDraft").mockImplementation(async (pipelineId, version) => {
      const source = catalog.pipelines.find(
        (item) => item.pipeline_id === pipelineId && item.version === version,
      );
      if (!source) throw new Error("Pipeline definition not found.");
      return {
        pipeline: {
          ...structuredClone(source),
          pipeline_id: source.built_in ? `${source.pipeline_id}.custom` : source.pipeline_id,
          version: source.built_in ? 1 : source.version + 1,
          name: source.built_in ? `${source.name} — custom` : source.name,
          status: "draft",
          built_in: false,
          derived_from: `${source.pipeline_id}@${source.version}`,
          created_at: null,
          created_by: null,
          validation: undefined,
          runtime_support: undefined,
        },
      };
    });
  });

  it("shows assigned definitions and durable execution traces", async () => {
    const { wrapper } = await mountStudio();

    expect(wrapper.text()).toContain("Pipeline Studio");
    expect(wrapper.text()).toContain("Research — current production chain");
    expect(wrapper.text()).toContain("Chroma semantic similarity");
    expect(wrapper.text()).toContain("Pipeline diagram");
    expect(wrapper.text()).toContain("Active assignment");

    await wrapper.find("#pipeline-tab-operations").trigger("click");
    expect(wrapper.text()).toContain("Operational health");
    expect(wrapper.text()).toContain("95th-percentile run time");
    expect(wrapper.text()).toContain("Stage strategy health");
    await wrapper.find("#pipeline-operations-tab-compare").trigger("click");
    expect(wrapper.text()).toContain("Test and compare Research pipelines");
    await wrapper.find("#pipeline-operations-tab-benchmarks").trigger("click");
    expect(wrapper.text()).toContain("Benchmark Research pipelines");

    await wrapper.find("#pipeline-tab-executions").trigger("click");
    expect(wrapper.text()).toContain("Execution history");
    expect(wrapper.text()).toContain("retrieve.chroma_similarity");
  });

  it("keeps selected definitions and traces in the URL", async () => {
    const { wrapper, router } = await mountStudio();

    const custom = wrapper
      .findAll(".pipeline-choice")
      .find((item) => item.text().includes("Research — custom"));
    expect(custom).toBeTruthy();
    await custom!.trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.query.pipeline).toBe(pipelineKey(catalog.pipelines[1]));
    expect(router.currentRoute.value.query.run).toBe("rag-1");
  });

  it("assigns an active runtime-supported pipeline", async () => {
    const assign = vi.spyOn(pipelinesApi, "setAssignment").mockResolvedValue({
      assignment: {
        feature: "research",
        pipeline_id: "research.custom",
        pipeline_version: 2,
        scope: "system",
        scope_id: null,
        override_allowed: true,
        source: "system",
      },
    });

    const { wrapper } = await mountStudio();

    const custom = wrapper
      .findAll(".pipeline-choice")
      .find((item) => item.text().includes("Research — custom"));
    expect(custom).toBeTruthy();
    await custom!.trigger("click");

    const activate = wrapper
      .findAll(".detail-actions button")
      .find((item) => item.text().includes("Make active"));
    expect(activate).toBeTruthy();
    await activate!.trigger("click");
    await flushPromises();

    expect(assign).toHaveBeenCalledWith(
      expect.objectContaining({
        feature: "research",
        pipeline_id: "research.custom",
        pipeline_version: 2,
      }),
    );
  });

  it("assigns an evidence-recovery pipeline and shows its cELF compliance", async () => {
    const recoveryCatalog = structuredClone(catalog);
    recoveryCatalog.pipelines.push({
      ...structuredClone(catalog.pipelines[0]),
      pipeline_id: "evidence.recovery.cascade",
      name: "Evidence recovery — relevance cascade (non-cELF-guaranteed)",
      purpose: "evidence_recovery",
      built_in: true,
      runtime_support: {
        supported: true,
        adapter: "evidence_recovery",
        celf_compliant: false,
        reason: "Non-cELF-guaranteed: candidates from 'mmr' reach the provenance gate.",
      },
    });
    vi.spyOn(pipelinesApi, "catalog").mockResolvedValue(recoveryCatalog);
    const assign = vi.spyOn(pipelinesApi, "setAssignment").mockResolvedValue({
      assignment: {
        feature: "evidence_recovery",
        pipeline_id: "evidence.recovery.cascade",
        pipeline_version: 1,
        scope: "system",
        scope_id: null,
        override_allowed: false,
        source: "system",
      },
    });

    const { wrapper } = await mountStudio();
    const choice = wrapper
      .findAll(".pipeline-choice")
      .find((item) => item.text().includes("relevance cascade"));
    await choice!.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Evidence recovery");
    expect(wrapper.text()).toContain("Non-cELF-guaranteed");
    const activate = wrapper
      .findAll(".detail-actions button")
      .find((item) => item.text().includes("Make active"));
    await activate!.trigger("click");
    await flushPromises();

    expect(assign).toHaveBeenCalledWith(
      expect.objectContaining({
        feature: "evidence_recovery",
        pipeline_id: "evidence.recovery.cascade",
      }),
    );
  });

  it.each([
    ["corpus_segmentation", "corpus.segmentation.custom", "Segmentation"],
    ["corpus_document_manifest", "corpus.document_manifest.custom", "Document manifest"],
    ["corpus_text_touchup", "corpus.text_touchup.custom", "Text touch-up"],
    [
      "corpus_reviewer_evidence_choice",
      "corpus.reviewer_evidence_choice.custom",
      "Reviewer evidence choice",
    ],
  ])("labels and assigns a %s pipeline to its feature", async (feature, pipelineId, label) => {
    const featureCatalog = structuredClone(catalog);
    featureCatalog.pipelines.push({
      ...structuredClone(catalog.pipelines[0]),
      pipeline_id: pipelineId,
      name: "Custom — review first",
      purpose: feature,
      built_in: false,
      runtime_support: { supported: true, adapter: feature },
    });
    vi.spyOn(pipelinesApi, "catalog").mockResolvedValue(featureCatalog);
    const assign = vi.spyOn(pipelinesApi, "setAssignment").mockResolvedValue({
      assignment: {
        feature,
        pipeline_id: pipelineId,
        pipeline_version: 1,
        scope: "system",
        scope_id: null,
        override_allowed: true,
        source: "system",
      },
    });

    const { wrapper } = await mountStudio();
    const choice = wrapper
      .findAll(".pipeline-choice")
      .find((item) => item.text().includes("review first"));
    await choice!.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain(label);
    const activate = wrapper
      .findAll(".detail-actions button")
      .find((item) => item.text().includes("Make active"));
    await activate!.trigger("click");
    await flushPromises();

    expect(assign).toHaveBeenCalledWith(
      expect.objectContaining({ feature, pipeline_id: pipelineId }),
    );
  });

  it("clones a definition into an immutable custom version editor", async () => {
    const { wrapper } = await mountStudio();

    const clone = wrapper
      .findAll(".detail-actions button")
      .find((item) => item.text().includes("Clone & edit"));
    expect(clone).toBeTruthy();
    await clone!.trigger("click");
    await flushPromises();

    expect(pipelinesApi.cloneDraft).toHaveBeenCalledWith("research.current", 1);
    expect(wrapper.text()).toContain("New pipeline version");
    const idInput = wrapper.find('.pipeline-editor input[autocomplete="off"]');
    expect((idInput.element as HTMLInputElement).value).toBe("research.current.custom");
    expect(wrapper.text()).toContain("Stages");
  });

  it("asks the server for the next version when cloning a saved custom pipeline", async () => {
    const { wrapper } = await mountStudio();

    const custom = wrapper
      .findAll(".pipeline-choice")
      .find((item) => item.text().includes("Research — custom"));
    expect(custom).toBeTruthy();
    await custom!.trigger("click");

    const clone = wrapper
      .findAll(".detail-actions button")
      .find((item) => item.text().includes("Clone & edit"));
    expect(clone).toBeTruthy();
    await clone!.trigger("click");
    await flushPromises();

    expect(pipelinesApi.cloneDraft).toHaveBeenCalledWith("research.custom", 2);
    const inputs = wrapper.findAll(".pipeline-editor input");
    const idInput = inputs.find((input) => (input.attributes("autocomplete") || "") === "off");
    expect((idInput!.element as HTMLInputElement).value).toBe("research.custom");
    const versionInput = inputs.find((input) => input.attributes("type") === "number");
    expect((versionInput!.element as HTMLInputElement).value).toBe("3");
  });

  it("filters execution history and deletes one trace", async () => {
    const deleteRun = vi.spyOn(pipelinesApi, "deleteRun").mockResolvedValue({
      deleted: true,
      run_id: "rag-1",
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { wrapper } = await mountStudio();

    await wrapper.find("#pipeline-tab-executions").trigger("click");
    const query = wrapper.find('.trace-filters input[type="search"]');
    await query.setValue("rag-1");
    await wrapper.find(".trace-filters").trigger("submit");
    await flushPromises();

    expect(pipelinesApi.runs).toHaveBeenCalledWith(
      expect.objectContaining({ query: "rag-1", limit: 25, offset: 0 }),
    );

    await wrapper.find(".run-actions .ui-menu-trigger").trigger("click");
    await wrapper
      .findAll('[role="menuitem"]')
      .find((item) => item.text() === "Delete execution")!
      .trigger("click");
    await flushPromises();
    expect(deleteRun).toHaveBeenCalledWith("rag-1");
  });

  it("moves the glossary out of the page and into a Help dialog", async () => {
    const { wrapper } = await mountStudio();
    expect(wrapper.find(".concept-guide, .plain-language-guide").exists()).toBe(false);
    expect(document.body.querySelector("[role=dialog]")).toBeNull();

    const help = wrapper.findAll(".ui-page-header button").find((b) => b.text() === "Help")!;
    await help.trigger("click");
    await flushPromises();
    const dialog = document.body.querySelector("[role=dialog]")!;
    expect(dialog.textContent).toContain("How Pipeline Studio is organized");
    expect(dialog.textContent).toContain("Core concepts");
    expect(dialog.textContent).toContain("Pipeline lifecycle");
    expect(dialog.textContent).toContain("Reading pipeline graphs");
    for (const term of ["Execution trace", "Scholarly effect", "Assignment", "Strategy"]) {
      expect(dialog.textContent).toContain(term);
    }
    wrapper.unmount();
  });

  it("uses the shared tabs and keeps Operations state in the URL", async () => {
    const { wrapper, router } = await mountStudio();
    expect(wrapper.findAll('.ui-page-header [role="tab"]').map((tab) => tab.text())).toEqual([
      "Pipelines",
      "Strategies",
      "Executions",
      "Operations",
    ]);
    await wrapper.get("#pipeline-tab-operations").trigger("click");
    await flushPromises();
    await wrapper.get("#pipeline-operations-tab-benchmarks").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query).toMatchObject({
      section: "operations",
      operation: "benchmarks",
    });
    router.back();
    await flushPromises();
    await flushPromises();
    expect(router.currentRoute.value.query.operation).toBeUndefined();
    expect(wrapper.get("#pipeline-operations-tab-health").attributes("aria-selected")).toBe("true");
  });

  it("drills from an attention row into the matching server-side execution filter", async () => {
    const { wrapper, router } = await mountStudio({ section: "operations" });
    const row = wrapper.get('.attention tbody tr[data-kind="workflow"]');
    await row.get("button").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query).toMatchObject({
      section: "executions",
      run_workflow: "research",
    });
    expect(pipelinesApi.runs).toHaveBeenLastCalledWith(
      expect.objectContaining({ category: "research", offset: 0 }),
    );
    expect(wrapper.get("#pipeline-tab-executions").attributes("aria-selected")).toBe("true");
  });

  it("refetches on a pipelines invalidation without losing selection, section, or filters", async () => {
    const { wrapper, router } = await mountStudio({
      section: "executions",
      status: "failed",
      pipeline: pipelineKey(catalog.pipelines[1]),
    });
    expect(wrapper.findAll(".ui-page-header button").some((b) => b.text() === "Refresh")).toBe(
      false,
    );
    const before = vi.mocked(pipelinesApi.catalog).mock.calls.length;
    await queryClient.invalidateQueries({ queryKey: dataKey("pipelines") });
    await flushPromises();
    expect(vi.mocked(pipelinesApi.catalog).mock.calls.length).toBe(before + 1);
    expect(router.currentRoute.value.query).toMatchObject({
      section: "executions",
      status: "failed",
      pipeline: pipelineKey(catalog.pipelines[1]),
    });
  });

  it("does not reload the catalog when switching sections", async () => {
    const { wrapper } = await mountStudio();
    const before = vi.mocked(pipelinesApi.catalog).mock.calls.length;
    await wrapper.get("#pipeline-tab-strategies").trigger("click");
    await wrapper.get("#pipeline-tab-executions").trigger("click");
    await wrapper.get("#pipeline-tab-pipelines").trigger("click");
    await flushPromises();
    expect(vi.mocked(pipelinesApi.catalog).mock.calls.length).toBe(before);
  });
});
