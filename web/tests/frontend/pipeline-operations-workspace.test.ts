/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { chromaApi } from "../../src/api/chroma";
import { pipelinesApi } from "../../src/api/pipelines";
import PipelineOperationsWorkspace from "../../src/components/pipelines/PipelineOperationsWorkspace.vue";
import {
  contractPurposes,
  contractStrategies,
  contractVocabulary,
} from "../../src/components/pipelines/fixtures/pipelineCatalogContract";
import { useI18nStore } from "../../src/stores/i18n";
import type { PipelineOperationalMetrics } from "../../src/types/pipelines";

const metrics: PipelineOperationalMetrics = {
  sampled_run_count: 250,
  status_counts: { completed: 243, failed: 7 },
  fallback_run_count: 18,
  warning_run_count: 0,
  p95_run_elapsed_ms: 4200,
  workflows: [
    {
      category: "evidence",
      features: ["evidence_suggestion.reviewer"],
      run_count: 41,
      failed_count: 2,
      fallback_run_count: 4,
      warning_run_count: 0,
      p95_elapsed_ms: 4100,
    },
    {
      category: "research",
      features: ["research"],
      run_count: 64,
      failed_count: 0,
      fallback_run_count: 0,
      warning_run_count: 0,
      p95_elapsed_ms: 900,
    },
  ],
  features: [],
  strategies: [
    {
      strategy_id: "rerank.cross_encoder",
      stage_ids: ["rerank"],
      executions: 64,
      fallback_count: 8,
      warning_count: 0,
      model_call_count: 0,
      issue_count: 3,
      status_counts: { failed: 3 },
      p95_elapsed_ms: 5800,
    },
  ],
  sample_limit: 250,
};

function mountOperations(operation: "health" | "compare" | "benchmarks" = "health") {
  return mount(PipelineOperationsWorkspace, {
    props: {
      operation,
      pipelines: [],
      metrics,
      strategies: contractStrategies,
      purposes: contractPurposes,
      vocabulary: contractVocabulary,
    },
  });
}

describe("PipelineOperationsWorkspace", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().dictionary = {};
    vi.restoreAllMocks();
    vi.spyOn(chromaApi, "collections").mockResolvedValue([] as never);
    vi.spyOn(pipelinesApi, "researchBenchmarkCases").mockResolvedValue({
      cases: [],
      limit: 200,
      offset: 0,
    });
  });

  it("renders only the selected subsection, with no accordion shells", async () => {
    const wrapper = mountOperations("health");
    expect(wrapper.find("details.comparison-panel, details.benchmark-panel").exists()).toBe(false);
    expect(wrapper.text()).toContain("Operational health");
    expect(wrapper.text()).not.toContain("Test and compare Research pipelines");
    expect(wrapper.findAll('[role="tab"]').map((tab) => tab.text())).toEqual([
      "Health",
      "Compare",
      "Benchmarks",
    ]);

    await wrapper.get("#pipeline-operations-tab-compare").trigger("click");
    expect(wrapper.emitted("update:operation")).toEqual([["compare"]]);
    await wrapper.setProps({ operation: "compare" });
    await flushPromises();
    expect(wrapper.text()).toContain("Test and compare Research pipelines");
    expect(wrapper.text()).not.toContain("Operational health");
  });

  it("states the health disclaimer once", () => {
    const text = mountOperations("health").text();
    expect(text.match(/not the scholarly validity/g)).toHaveLength(1);
  });

  it("surfaces what needs attention and deep-links only to supported filters", async () => {
    const wrapper = mountOperations("health");
    const rows = wrapper.findAll(".attention tbody tr");
    // Failures first, then issues: evidence (2), strategy (3 failed) → strategy leads.
    expect(rows.map((row) => row.attributes("data-kind"))).toEqual(["strategy", "workflow"]);
    expect(rows[0].text()).toContain("View strategy");
    expect(rows[0].text()).not.toContain("View executions");

    await rows[1].get("button").trigger("click");
    expect(wrapper.emitted("viewExecutions")).toEqual([["evidence"]]);
    await rows[0].get("button").trigger("click");
    expect(wrapper.emitted("viewStrategy")).toEqual([["rerank.cross_encoder"]]);
  });

  it("keeps Compare form state while another subsection is showing", async () => {
    const wrapper = mountOperations("compare");
    await flushPromises();
    await wrapper.get("textarea").setValue("A question worth keeping");
    await wrapper.setProps({ operation: "health" });
    await wrapper.setProps({ operation: "compare" });
    expect((wrapper.get("textarea").element as HTMLTextAreaElement).value).toBe(
      "A question worth keeping",
    );
  });
});
