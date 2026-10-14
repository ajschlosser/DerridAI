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
import { describe, expect, it } from "vitest";
import { defineComponent } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import {
  usePipelineStudioNavigation,
  type PipelineStudioNavigation,
} from "../../src/features/pipelines/composables/usePipelineStudioNavigation";

async function setup(query: Record<string, string> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/pipelines", name: "pipelines", component: { template: "<div />" } }],
  });
  await router.push({ name: "pipelines", query });
  await router.isReady();
  let nav!: PipelineStudioNavigation;
  let runChanges = 0;
  mount(
    defineComponent({
      setup() {
        nav = usePipelineStudioNavigation(() => (runChanges += 1));
        return () => null;
      },
    }),
    { global: { plugins: [router] } },
  );
  return { nav, router, runChanges: () => runChanges };
}

describe("usePipelineStudioNavigation", () => {
  it("falls back to safe defaults for invalid sections", async () => {
    const { nav } = await setup({ section: "nonsense", operation: "also-nonsense" });
    expect(nav.section.value).toBe("pipelines");
    expect(nav.operationsSection.value).toBe("health");
  });

  it("reads and writes every Studio key, omitting defaults", async () => {
    const { nav, router } = await setup({
      section: "operations",
      operation: "benchmarks",
      strategy_q: "rerank",
      pipeline_status: "active",
    });
    expect(nav.operationsSection.value).toBe("benchmarks");
    expect(nav.strategyFilters.value.query).toBe("rerank");
    expect(nav.pipelineFilters.value.status).toBe("active");

    nav.selectOperationsSection("health");
    await flushPromises();
    expect(router.currentRoute.value.query.operation).toBeUndefined();
    expect(router.currentRoute.value.query.section).toBe("operations");

    nav.selectSection("pipelines");
    await flushPromises();
    expect(router.currentRoute.value.query.section).toBeUndefined();
    expect(router.currentRoute.value.query.operation).toBeUndefined();
  });

  it("selecting a pipeline switches to the pipelines section", async () => {
    const { nav, router } = await setup({ section: "strategies", strategy: "s1" });
    nav.selectPipeline("a@2");
    await flushPromises();
    expect(router.currentRoute.value.query).toMatchObject({ pipeline: "a@2", strategy: "s1" });
    expect(nav.section.value).toBe("pipelines");
  });

  it("restores state on Back and reports execution-query changes", async () => {
    const { nav, router, runChanges } = await setup();
    await router.push({ name: "pipelines", query: { section: "executions", status: "failed" } });
    await flushPromises();
    expect(nav.section.value).toBe("executions");
    expect(nav.runFilters.value.status).toBe("failed");
    expect(runChanges()).toBe(1);
    router.back();
    await flushPromises();
    expect(nav.runFilters.value.status).toBe("");
    expect(nav.section.value).toBe("pipelines");
  });
});
