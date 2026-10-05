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
import { VueQueryPlugin } from "@tanstack/vue-query";
import { queryClient } from "../../src/realtime/dataQuery";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { chromaApi } from "../../src/api/chroma";
import { pipelinesApi } from "../../src/api/pipelines";
import PipelineBenchmarkWorkspace from "../../src/components/pipelines/PipelineBenchmarkWorkspace.vue";
import { useI18nStore } from "../../src/stores/i18n";
import type {
  PipelineDefinition,
  ResearchPipelineBenchmarkCase,
  ResearchPipelineBenchmarkRun,
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

const fixedCase: ResearchPipelineBenchmarkCase = {
  case_id: "trace-definition-001",
  version: 1,
  prompt: "What is the trace?",
  instructions: null,
  source_collection: "corpus",
  query_decomposition: false,
  notes: null,
  corpus_snapshot: {
    fingerprint: "a".repeat(64),
    collections: [{ name: "corpus", count: 42 }],
    limitations: [],
  },
  created_at: "2026-09-29T20:00:00Z",
  created_by: "admin",
};

const phase = (ids: string[]) => ({ count: ids.length, record_ids: ids, scores: {} });
const side = (hash: string, name: string, elapsed: number, ids: string[]) => ({
  pipeline: { pipeline_hash: hash, name, pipeline_version: 1 },
  elapsed_seconds: elapsed,
  warnings: [],
  candidates: {
    pre_rerank: phase(ids),
    post_rerank: phase(ids),
    post_selection: phase(ids),
  },
  context_characters: 100,
  resource_use: { query_transform_model_calls: 0, cross_encoder_calls: 0 },
  evidence: ids.map((id, index) => ({
    record_id: id,
    rank: index + 1,
    work: `Work ${id}`,
    citation: "",
    retrieval_hits: [],
  })),
});

const benchmark = {
  benchmark_run_id: "benchmark-1",
  case_id: fixedCase.case_id,
  case_version: fixedCase.version,
  mode: "retrieval_only",
  created_at: "2026-09-29T20:01:00Z",
  created_by: "admin",
  case_snapshot: fixedCase,
  fixed_input: {
    prompt: fixedCase.prompt,
    instructions: null,
    source_collection: "corpus",
  },
  corpus: fixedCase.corpus_snapshot,
  retrieval_config: {},
  model_identity: {},
  left_pipeline: { pipeline_hash: "left-hash" },
  right_pipeline: { pipeline_hash: "right-hash" },
  comparison: {
    non_persistent: true,
    left: side("left-hash", "Research current", 0.4, ["r1", "r2"]),
    right: side("right-hash", "Research balanced", 0.5, ["r2", "r3"]),
    comparison: {
      shared_record_ids: ["r2"],
      left_only_record_ids: ["r1"],
      right_only_record_ids: ["r3"],
      shared_count: 1,
      union_count: 3,
      candidate_overlap: { jaccard_overlap: 0.5, shared_count: 1, union_count: 2 },
      jaccard_overlap: 0.25,
      rank_changes: [],
    },
  },
  reproducibility_warnings: ["Index was rebuilt after the case was captured."],
} as unknown as ResearchPipelineBenchmarkRun;

describe("PipelineBenchmarkWorkspace", () => {
  beforeEach(() => {
    queryClient.clear();
    setActivePinia(createPinia());
    useI18nStore().dictionary = {};
    vi.restoreAllMocks();

    vi.spyOn(chromaApi, "collections").mockResolvedValue([
      {
        name: "_response_cache",
        count: 7,
        protected: false,
        collection_role: "general",
        language_codes: [],
        metadata: { derridai_system_collection: "response_cache" },
      },
      {
        name: "corpus",
        count: 42,
        protected: false,
        collection_role: "general",
        language_codes: ["en"],
      },
    ] as never);
    vi.spyOn(pipelinesApi, "researchBenchmarkCases").mockResolvedValue({
      cases: [],
      limit: 200,
      offset: 0,
    });
    vi.spyOn(pipelinesApi, "createResearchBenchmarkCase").mockResolvedValue({
      case: fixedCase,
    });
    vi.spyOn(pipelinesApi, "runResearchBenchmark").mockResolvedValue({
      benchmark,
    });
  });

  const body = () => document.body;
  function setField(element: Element | null, value: string) {
    const field = element as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
    field.value = value;
    field.dispatchEvent(new Event(field.tagName === "SELECT" ? "change" : "input"));
  }
  const dialogButton = (label: string) =>
    [...body().querySelectorAll<HTMLButtonElement>("[role=dialog] button")].find((button) =>
      button.textContent?.includes(label),
    );

  it("creates an immutable case in a dialog, selects it, and runs a fixed benchmark", async () => {
    const wrapper = mount(PipelineBenchmarkWorkspace, {
      props: { pipelines },
      attachTo: document.body,
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();
    // The create form is not permanently on screen.
    expect(body().querySelector("[role=dialog]")).toBeNull();
    expect(wrapper.text()).toContain("No benchmark cases yet");

    await wrapper
      .findAll("button")
      .find((item) => item.text().includes("New benchmark case"))!
      .trigger("click");
    await flushPromises();
    const dialog = body().querySelector("[role=dialog]")!;
    expect(dialog.textContent).toContain("cannot be replaced");
    expect(
      [...dialog.querySelectorAll<HTMLSelectElement>("select option")].map((option) => option.value),
    ).not.toContain("_response_cache");
    setField(dialog.querySelector('input[type="text"]'), "trace-definition-001");
    setField(dialog.querySelector('input[type="number"]'), "1");
    setField(dialog.querySelector("select"), "corpus");
    setField(dialog.querySelector("textarea"), "What is the trace?");
    await flushPromises();

    dialogButton("Create immutable case")!.click();
    await flushPromises();

    expect(pipelinesApi.createResearchBenchmarkCase).toHaveBeenCalledWith(
      expect.objectContaining({
        case_id: "trace-definition-001",
        version: 1,
        prompt: "What is the trace?",
        source_collection: "corpus",
        query_decomposition: false,
      }),
    );
    // Closed, selected, and showing the immutable snapshot.
    expect(body().querySelector("[role=dialog]")).toBeNull();
    expect(wrapper.find(".case-choice.selected").text()).toContain("trace-definition-001");
    expect(wrapper.text()).toContain("What is the trace?");
    expect(wrapper.text()).toContain("a".repeat(64));

    await wrapper
      .findAll("button")
      .find((item) => item.text().includes("Run fixed benchmark"))!
      .trigger("click");
    await flushPromises();

    expect(pipelinesApi.runResearchBenchmark).toHaveBeenCalledWith({
      case_id: "trace-definition-001",
      case_version: 1,
      left: { pipeline_id: "research.current", version: 1 },
      right: { pipeline_id: "research.balanced", version: 1 },
    });
    // Rendered through the shared comparison result, with provenance and drift limits visible.
    expect(wrapper.find(".comparison-result").exists()).toBe(true);
    expect(wrapper.findAll(".aligned tbody tr")).toHaveLength(3);
    expect(wrapper.text()).toContain("benchmark-1");
    expect(wrapper.text()).toContain("left-hash");
    expect(wrapper.text()).toContain("right-hash");
    expect(wrapper.text()).toContain("Index was rebuilt after the case was captured.");
    expect(wrapper.text()).toContain("do not declare a winner");
    wrapper.unmount();
  });

  it("lists saved cases and switches the fixed case without editing it", async () => {
    vi.spyOn(pipelinesApi, "researchBenchmarkCases").mockResolvedValue({
      cases: [fixedCase, { ...fixedCase, case_id: "second", version: 3 }],
      limit: 200,
      offset: 0,
    });
    const wrapper = mount(PipelineBenchmarkWorkspace, {
      props: { pipelines },
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();
    const choices = wrapper.findAll(".case-choice");
    expect(choices).toHaveLength(2);
    expect(wrapper.find("#pipeline-benchmark-run").text()).toBe("trace-definition-001 · v1");
    await choices[1].trigger("click");
    expect(wrapper.find("#pipeline-benchmark-run").text()).toBe("second · v3");
    expect(wrapper.find("textarea").exists()).toBe(false);
  });
});
