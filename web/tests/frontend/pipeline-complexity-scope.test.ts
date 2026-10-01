/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import PipelineComplexityView from "../../src/components/pipelines/PipelineComplexityView.vue";
import { analysisFixture } from "../../src/components/pipelines/fixtures/pipelineAnalysisFixture";
import { contractStrategies } from "../../src/components/pipelines/fixtures/pipelineCatalogContract";

describe("PipelineComplexityView measured growth", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("shows growth against collection size separately from candidate count", () => {
    const analysis = analysisFixture();
    const first = analysis.latency.stages[0];
    analysis.latency.stages[0] = {
      ...first,
      observed_scaling: null,
      observed_scope_scaling: {
        exponent: 1.02,
        r_squared: 0.97,
        points: 12,
        min_input: 100,
        max_input: 5000,
      },
    };
    const wrapper = mount(PipelineComplexityView, {
      props: {
        complexity: analysis.complexity,
        latency: analysis.latency,
        strategies: contractStrategies,
      },
    });
    expect(wrapper.text()).toContain("N^1.02");
    expect(wrapper.text()).not.toContain("n^1.02");
  });

  it("shows a dash when nothing was measured", () => {
    const analysis = analysisFixture();
    const wrapper = mount(PipelineComplexityView, {
      props: {
        complexity: analysis.complexity,
        latency: analysis.latency,
        strategies: contractStrategies,
      },
    });
    expect(wrapper.find(".none").exists()).toBe(true);
    expect(wrapper.text()).not.toContain("N^");
  });
});
