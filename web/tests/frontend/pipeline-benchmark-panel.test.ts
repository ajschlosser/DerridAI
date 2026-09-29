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
  model_config: {},
  left_pipeline: { pipeline_hash: "left-hash" },
  right_pipeline: { pipeline_hash: "right-hash" },
  comparison: {
    non_persistent: true,
    left: { elapsed_seconds: 0.4 },
    right: { elapsed_seconds: 0.5 },
    comparison: {
      candidate_overlap: { jaccard_overlap: 0.5 },
      jaccard_overlap: 0.25,
    },
  },
  reproducibility_warnings: [],
} as unknown as ResearchPipelineBenchmarkRun;

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

  it("creates an immutable case before running a fixed benchmark", async () => {
    const wrapper = mount(PipelineBenchmarkPanel, { props: { pipelines } });
    const details = wrapper.find("details");
    (details.element as HTMLDetailsElement).open = true;
    await details.trigger("toggle");
    await flushPromises();

    const textInputs = wrapper.findAll('input[type="text"]');
    await textInputs[0].setValue("trace-definition-001");
    await wrapper.find('input[type="number"]').setValue(1);
    await wrapper.find("select").setValue("corpus");
    await wrapper.find("textarea").setValue("What is the trace?");

    const createButton = wrapper
      .findAll("button")
      .find((item) => item.text().includes("Create immutable case"));
    expect(createButton).toBeTruthy();
    await createButton!.trigger("click");
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
    expect(wrapper.text()).toContain("What is the trace?");
    expect(wrapper.text()).toContain("a".repeat(64));

    const runButton = wrapper
      .findAll("button")
      .find((item) => item.text().includes("Run fixed benchmark"));
    expect(runButton).toBeTruthy();
    await runButton!.trigger("click");
    await flushPromises();

    expect(pipelinesApi.runResearchBenchmark).toHaveBeenCalledWith({
      case_id: "trace-definition-001",
      case_version: 1,
      left: { pipeline_id: "research.current", version: 1 },
      right: { pipeline_id: "research.balanced", version: 1 },
    });
    expect(wrapper.text()).toContain("benchmark-1");
    expect(wrapper.text()).toContain("left-hash");
    expect(wrapper.text()).toContain("right-hash");
    expect(wrapper.text()).toContain("do not declare a winner");
  });
});
