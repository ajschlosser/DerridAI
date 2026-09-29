/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { chromaApi } from "../../src/api/chroma";
import { pipelinesApi } from "../../src/api/pipelines";
import PipelineBenchmarkPanel from "../../src/components/pipelines/PipelineBenchmarkPanel.vue";
import { useI18nStore } from "../../src/stores/i18n";
import type {
  PipelineDefinition,
  ResearchBenchmarkCase,
  ResearchBenchmarkRun,
  ResearchPipelineComparisonResult,
} from "../../src/types/pipelines";

const pipelines: PipelineDefinition[] = [
  {
    pipeline_id: "research.current",
    version: 1,
    name: "Research current",
    purpose: "research",
    status: "active",
    entry_stage_ids: ["dense"],
    stages: [],
    runtime_support: { supported: true, adapter: "research" },
  },
  {
    pipeline_id: "research.balanced",
    version: 1,
    name: "Research balanced",
    purpose: "research",
    status: "draft",
    entry_stage_ids: ["dense"],
    stages: [],
    runtime_support: { supported: true, adapter: "research" },
  },
];

const benchmarkCase: ResearchBenchmarkCase = {
  benchmark_id: "trace-core",
  version: 1,
  name: "Trace core",
  request: {
    prompt: "What is the trace?",
    source_collection: "corpus",
    query_decomposition: false,
  },
  collection_snapshot: {
    name: "corpus",
    count: 42,
    source_snapshot_hash: "source-sha",
    embedding_revision: "emb-v1",
  },
  reproducibility_warnings: [],
  created_at: "2026-09-29T19:00:00Z",
  created_by: "admin",
};

const comparison = {
  non_persistent: true,
  left: {
    pipeline: {
      pipeline_id: "research.current",
      pipeline_version: 1,
      pipeline_hash: "hash-a",
      name: "Research current",
      purpose: "research",
    },
    elapsed_seconds: 0.4,
    warnings: [],
    retrieval: {},
    candidate_retention: "complete_for_comparison",
    candidates: {
      pre_rerank: { count: 2, record_ids: ["r1", "r2"], scores: {} },
      post_rerank: { count: 2, record_ids: ["r1", "r2"], scores: {} },
      post_selection: { count: 1, record_ids: ["r1"], scores: {} },
    },
    resource_use: { query_transform_model_calls: 0, cross_encoder_calls: 1 },
    evidence: [],
    stages: [],
  },
  right: {
    pipeline: {
      pipeline_id: "research.balanced",
      pipeline_version: 1,
      pipeline_hash: "hash-b",
      name: "Research balanced",
      purpose: "research",
    },
    elapsed_seconds: 0.5,
    warnings: [],
    retrieval: {},
    candidate_retention: "complete_for_comparison",
    candidates: {
      pre_rerank: { count: 2, record_ids: ["r2", "r3"], scores: {} },
      post_rerank: { count: 2, record_ids: ["r2", "r3"], scores: {} },
      post_selection: { count: 1, record_ids: ["r2"], scores: {} },
    },
    resource_use: { query_transform_model_calls: 0, cross_encoder_calls: 1 },
    evidence: [],
    stages: [],
  },
  comparison: {
    shared_record_ids: [],
    left_only_record_ids: ["r1"],
    right_only_record_ids: ["r2"],
    shared_count: 0,
    union_count: 2,
    jaccard_overlap: 0,
    candidate_overlap: {
      shared_record_ids: ["r2"],
      left_only_record_ids: ["r1"],
      right_only_record_ids: ["r3"],
      shared_count: 1,
      union_count: 3,
      jaccard_overlap: 1 / 3,
    },
    post_rerank_overlap: {
      shared_record_ids: ["r2"],
      left_only_record_ids: ["r1"],
      right_only_record_ids: ["r3"],
      shared_count: 1,
      union_count: 3,
      jaccard_overlap: 1 / 3,
    },
    rank_changes: [],
  },
} as unknown as ResearchPipelineComparisonResult;

const benchmarkRun: ResearchBenchmarkRun = {
  benchmark_run_id: "benchmark-1",
  benchmark_id: "trace-core",
  benchmark_version: 1,
  case: benchmarkCase,
  owner: "admin",
  created_at: "2026-09-29T19:05:00Z",
  app_version: "0.80.7",
  git_commit: "abc123",
  collection_snapshot: benchmarkCase.collection_snapshot,
  reproducibility_warnings: [],
  comparison,
};

describe("PipelineBenchmarkPanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().dictionary = {};
    vi.restoreAllMocks();
    vi.spyOn(chromaApi, "collections").mockResolvedValue([
      {
        name: "corpus",
        count: 42,
        protected: false,
        collection_role: "general",
        language_codes: ["en"],
      },
    ] as never);
    vi.spyOn(pipelinesApi, "benchmarkCases").mockResolvedValue({
      cases: [structuredClone(benchmarkCase)],
      limit: 100,
      offset: 0,
    });
    vi.spyOn(pipelinesApi, "createBenchmarkCase").mockResolvedValue({
      case: structuredClone(benchmarkCase),
    });
    vi.spyOn(pipelinesApi, "runBenchmark").mockResolvedValue({
      run: structuredClone(benchmarkRun),
    });
  });

  it("saves an immutable fixed case and runs exact pipeline versions without ranking them", async () => {
    const wrapper = mount(PipelineBenchmarkPanel, { props: { pipelines } });
    const details = wrapper.find("details");
    (details.element as HTMLDetailsElement).open = true;
    await details.trigger("toggle");
    await flushPromises();

    const inputs = wrapper.findAll("input");
    await inputs[0].setValue("trace-core");
    await inputs[1].setValue("Trace core");
    await wrapper.find("textarea").setValue("What is the trace?");
    const selects = wrapper.findAll("select");
    await selects[0].setValue("corpus");

    const save = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Save immutable case"));
    expect(save).toBeTruthy();
    await save!.trigger("click");
    await flushPromises();

    expect(pipelinesApi.createBenchmarkCase).toHaveBeenCalledWith({
      benchmark_id: "trace-core",
      name: "Trace core",
      request: {
        prompt: "What is the trace?",
        source_collection: "corpus",
        query_decomposition: false,
      },
      notes: null,
    });

    const runnerSelects = wrapper.findAll(".runner select");
    await runnerSelects[0].setValue("trace-core@1");
    await runnerSelects[1].setValue("research.current@1");
    await runnerSelects[2].setValue("research.balanced@1");

    const run = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Run fixed benchmark"));
    expect(run).toBeTruthy();
    await run!.trigger("click");
    await flushPromises();

    expect(pipelinesApi.runBenchmark).toHaveBeenCalledWith({
      benchmark_id: "trace-core",
      benchmark_version: 1,
      left: { pipeline_id: "research.current", version: 1 },
      right: { pipeline_id: "research.balanced", version: 1 },
    });
    expect(wrapper.text()).toContain("benchmark-1");
    expect(wrapper.text()).toContain("33%");
    expect(wrapper.text()).toContain("hash-a");
    expect(wrapper.text()).toContain("hash-b");
    expect(wrapper.text()).toContain("not a quality score or winner");
  });
});
