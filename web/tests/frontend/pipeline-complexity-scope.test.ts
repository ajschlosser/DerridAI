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
