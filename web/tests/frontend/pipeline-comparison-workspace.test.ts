/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { chromaApi } from "../../src/api/chroma";
import { pipelinesApi } from "../../src/api/pipelines";
import PipelineComparisonWorkspace from "../../src/components/pipelines/PipelineComparisonWorkspace.vue";
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

describe("PipelineComparisonWorkspace", () => {
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
    const wrapper = mount(PipelineComparisonWorkspace, { props: { pipelines } });
    await flushPromises();
    expect(wrapper.find("details.comparison-panel").exists()).toBe(false);

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
    expect(wrapper.text()).toContain("Only in Pipeline B");

    // One aligned table: shared records first (Pipeline A's order), then A-only, then B-only.
    const rows = wrapper.findAll(".aligned tbody tr");
    expect(rows.map((row) => row.get("code").text())).toEqual(["r2", "r1", "r3"]);
    expect(rows.map((row) => row.attributes("data-presence"))).toEqual(["both", "left", "right"]);
    expect(rows[0].findAll("td").map((cell) => cell.text())).toEqual(["#2", "#1"]);
    expect(rows[1].findAll("td").map((cell) => cell.text())).toEqual(["#1", "—"]);
    expect(rows[2].findAll("td").map((cell) => cell.text())).toEqual(["—", "#2"]);
    expect(rows[0].text()).toContain("Writing and Difference");
    expect(wrapper.text()).not.toMatch(/\b(winner|best)\b/i);
    expect(wrapper.text()).toContain("does not declare either pipeline better");
  });

  it("runs a reviewer-evidence comparison on the same field value and blocks", async () => {
    const evidencePipelines: PipelineDefinition[] = [
      {
        pipeline_id: "evidence.reviewer.current",
        version: 2,
        name: "Reviewer current",
        purpose: "evidence_suggestion",
        status: "active",
        entry_stage_ids: ["lexical"],
        stages: [],
        runtime_support: { supported: true, adapter: "evidence_suggestion" },
      },
      {
        pipeline_id: "evidence.lexical-only",
        version: 1,
        name: "Lexical only",
        purpose: "evidence_suggestion",
        status: "draft",
        entry_stage_ids: ["lexical"],
        stages: [],
        runtime_support: { supported: true, adapter: "evidence_suggestion" },
      },
    ];
    vi.spyOn(pipelinesApi, "compareEvidenceSuggestion").mockResolvedValue({
      non_persistent: true,
      left: {
        pipeline: {
          pipeline_id: "evidence.reviewer.current",
          pipeline_version: 2,
          pipeline_hash: "left",
          purpose: "evidence_suggestion",
        },
        elapsed_seconds: 0.12,
        stages: [],
        candidates: [{ block_id: "b1", rank: 1, score: 0.9 }],
      },
      right: {
        pipeline: {
          pipeline_id: "evidence.lexical-only",
          pipeline_version: 1,
          pipeline_hash: "right",
          purpose: "evidence_suggestion",
        },
        elapsed_seconds: 0.08,
        stages: [],
        candidates: [{ block_id: "b1", rank: 1, score: 0.7 }],
      },
      comparison: {
        shared_block_ids: ["b1"],
        left_only_block_ids: [],
        right_only_block_ids: [],
        shared_count: 1,
        union_count: 1,
        jaccard_overlap: 1,
        rank_changes: [{ block_id: "b1", left_rank: 1, right_rank: 1, rank_delta: 0 }],
        elapsed_seconds_delta: -0.04,
      },
    });

    const wrapper = mount(PipelineComparisonWorkspace, {
      props: { pipelines: [...pipelines, ...evidencePipelines] },
    });
    await flushPromises();
    const radios = wrapper.findAll('input[type="radio"]');
    await radios[1].setValue();
    await wrapper.findAll("textarea")[0].setValue("hospitality");
    await wrapper
      .findAll("textarea")[1]
      .setValue('[{"block_id":"b1","text":"welcome the stranger"}]');
    await wrapper.find("input[type='text']").setValue("topic");
    const button = wrapper
      .findAll("button")
      .find((item) => item.text().includes("Run dry comparison"));
    await button!.trigger("click");
    await flushPromises();
    expect(pipelinesApi.compareEvidenceSuggestion).toHaveBeenCalledWith(
      expect.objectContaining({
        value: "hospitality",
        field: "topic",
        left: { pipeline_id: "evidence.reviewer.current", version: 2 },
        right: { pipeline_id: "evidence.lexical-only", version: 1 },
      }),
    );
    expect(wrapper.text()).toContain("Suggested-block overlap");
    expect(wrapper.text()).toContain("100%");
    expect(wrapper.text()).toContain("b1");
    expect(wrapper.text()).not.toMatch(/\b(winner|best)\b/i);
  });
});
