/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { chromaApi } from "../../src/api/chroma";
import { pipelinesApi } from "../../src/api/pipelines";
import PipelineComparisonPanel from "../../src/components/pipelines/PipelineComparisonPanel.vue";
import { useI18nStore } from "../../src/stores/i18n";
import type {
  PipelineDefinition,
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

const comparison: ResearchPipelineComparisonResult = {
  non_persistent: true,
  left: {
    pipeline: {
      pipeline_id: "research.current",
      pipeline_version: 1,
      pipeline_hash: "left",
      name: "Research current",
      purpose: "research",
    },
    elapsed_seconds: 0.42,
    warnings: [],
    retrieval: { raw_count: 20, deduplicated_count: 12 },
    candidate_retention: "complete_for_comparison",
    candidates: {
      pre_rerank: {
        count: 3,
        record_ids: ["r1", "r2", "r4"],
        scores: {
          relevance: { count: 3, minimum: 0.7, maximum: 0.9, mean: 0.8 },
          rrf_score: { count: 3, minimum: 0.01, maximum: 0.03, mean: 0.02 },
          rerank_score: { count: 0, minimum: null, maximum: null, mean: null },
        },
      },
      post_rerank: {
        count: 2,
        record_ids: ["r1", "r2"],
        scores: {
          relevance: { count: 2, minimum: 0.8, maximum: 0.9, mean: 0.85 },
          rrf_score: { count: 2, minimum: 0.02, maximum: 0.03, mean: 0.025 },
          rerank_score: { count: 2, minimum: 0.8, maximum: 0.9, mean: 0.85 },
        },
      },
      post_selection: {
        count: 2,
        record_ids: ["r1", "r2"],
        scores: {
          relevance: { count: 0, minimum: null, maximum: null, mean: null },
          rrf_score: { count: 0, minimum: null, maximum: null, mean: null },
          rerank_score: { count: 0, minimum: null, maximum: null, mean: null },
        },
      },
    },
    context_characters: 840,
    resource_use: { query_transform_model_calls: 0, cross_encoder_calls: 1 },
    stages: [],
    evidence: [
      {
        record_id: "r1",
        rank: 1,
        work: "Of Grammatology",
        citation: "Derrida 1976: 65",
        collection: "corpus",
        retrieval_hits: [],
      },
      {
        record_id: "r2",
        rank: 2,
        work: "Writing and Difference",
        citation: "Derrida 1978: 10",
        collection: "corpus",
        retrieval_hits: [],
      },
    ],
  },
  right: {
    pipeline: {
      pipeline_id: "research.balanced",
      pipeline_version: 1,
      pipeline_hash: "right",
      name: "Research balanced",
      purpose: "research",
    },
    elapsed_seconds: 0.55,
    warnings: [],
    retrieval: { raw_count: 18, deduplicated_count: 11 },
    candidate_retention: "complete_for_comparison",
    candidates: {
      pre_rerank: {
        count: 3,
        record_ids: ["r2", "r3", "r4"],
        scores: {
          relevance: { count: 3, minimum: 0.65, maximum: 0.88, mean: 0.76 },
          rrf_score: { count: 3, minimum: 0.01, maximum: 0.03, mean: 0.02 },
          rerank_score: { count: 0, minimum: null, maximum: null, mean: null },
        },
      },
      post_rerank: {
        count: 2,
        record_ids: ["r2", "r3"],
        scores: {
          relevance: { count: 2, minimum: 0.74, maximum: 0.88, mean: 0.81 },
          rrf_score: { count: 2, minimum: 0.02, maximum: 0.03, mean: 0.025 },
          rerank_score: { count: 2, minimum: 0.78, maximum: 0.91, mean: 0.845 },
        },
      },
      post_selection: {
        count: 2,
        record_ids: ["r2", "r3"],
        scores: {
          relevance: { count: 0, minimum: null, maximum: null, mean: null },
          rrf_score: { count: 0, minimum: null, maximum: null, mean: null },
          rerank_score: { count: 0, minimum: null, maximum: null, mean: null },
        },
      },
    },
    context_characters: 790,
    resource_use: { query_transform_model_calls: 0, cross_encoder_calls: 1 },
    stages: [],
    evidence: [
      {
        record_id: "r2",
        rank: 1,
        work: "Writing and Difference",
        citation: "Derrida 1978: 10",
        collection: "corpus",
        retrieval_hits: [],
      },
      {
        record_id: "r3",
        rank: 2,
        work: "Margins of Philosophy",
        citation: "Derrida 1982: 3",
        collection: "corpus",
        retrieval_hits: [],
      },
    ],
  },
  comparison: {
    shared_record_ids: ["r2"],
    left_only_record_ids: ["r1"],
    right_only_record_ids: ["r3"],
    shared_count: 1,
    union_count: 3,
    jaccard_overlap: 1 / 3,
    candidate_overlap: {
      shared_record_ids: ["r2", "r4"],
      left_only_record_ids: ["r1"],
      right_only_record_ids: ["r3"],
      shared_count: 2,
      union_count: 4,
      jaccard_overlap: 0.5,
    },
    post_rerank_overlap: {
      shared_record_ids: ["r2"],
      left_only_record_ids: ["r1"],
      right_only_record_ids: ["r3"],
      shared_count: 1,
      union_count: 3,
      jaccard_overlap: 1 / 3,
    },
    elapsed_seconds_delta: 0.13,
    context_characters_delta: -50,
    rank_changes: [{ record_id: "r2", left_rank: 2, right_rank: 1, rank_delta: -1 }],
  },
};

describe("PipelineComparisonPanel", () => {
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
    vi.spyOn(pipelinesApi, "compareResearch").mockResolvedValue(structuredClone(comparison));
  });

  it("runs a non-persistent comparison and explains descriptive overlap", async () => {
    const wrapper = mount(PipelineComparisonPanel, { props: { pipelines } });
    const details = wrapper.find("details");
    (details.element as HTMLDetailsElement).open = true;
    await details.trigger("toggle");
    await flushPromises();

    await wrapper.find("textarea").setValue("What is the trace?");
    const selects = wrapper.findAll("select");
    expect(selects.length).toBe(3);
    await selects[0].setValue("corpus");
    await selects[1].setValue("research.current@1");
    await selects[2].setValue("research.balanced@1");

    const button = wrapper
      .findAll("button")
      .find((item) => item.text().includes("Run dry comparison"));
    expect(button).toBeTruthy();
    await button!.trigger("click");
    await flushPromises();

    expect(pipelinesApi.compareResearch).toHaveBeenCalledWith({
      request: {
        prompt: "What is the trace?",
        source_collection: "corpus",
        query_decomposition: false,
      },
      left: { pipeline_id: "research.current", version: 1 },
      right: { pipeline_id: "research.balanced", version: 1 },
    });
    expect(wrapper.text()).toContain("Candidate-pool overlap");
    expect(wrapper.text()).toContain("50%");
    expect(wrapper.text()).toContain("Final evidence overlap");
    expect(wrapper.text()).toContain("33%");
    expect(wrapper.text()).toContain("Cross-encoder calls: 1");
    expect(wrapper.text()).toContain("Only in Pipeline A");
    expect(wrapper.text()).toContain("r1");
    expect(wrapper.text()).toContain("r3");
    expect(wrapper.text()).toContain("does not declare either pipeline better");
  });
});
