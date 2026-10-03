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
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RelationshipBrowserView from "../../src/views/RelationshipBrowserView.vue";
import RecordTraceabilityExplorer from "../../src/components/record/RecordTraceabilityExplorer.vue";
const reads = vi.hoisted(() => ({ trace: vi.fn(), model: vi.fn(), execute: vi.fn() }));
vi.mock("../../src/runtime/runtime.js", () => ({
  getRecordObjectGraph: reads.trace,
  getDerridaiNormativeModel: reads.model,
  openAnnotationsWorkspaceRecord: vi.fn(),
}));
vi.mock("../../src/api/graphql/client", () => ({
  execute: reads.execute,
  isAbortError: () => false,
}));
const graph = (id = "r1") => ({
  specification_version: "1.0",
  root_id: `Record:${id}`,
  nodes: [
    {
      id: `Record:${id}`,
      object_id: id,
      object_type: "Record",
      label: `Record ${id}`,
      materialization: "materialized",
      summary: "Retained source identity",
    },
  ],
  edges: [],
});
const model = { specification_version: "1.0", nodes: [], edges: [] };
function pending<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
async function open(query: Record<string, string> = { record: "r1" }) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/relationships", component: { template: "<div />" } }],
  });
  await router.push({ path: "/relationships", query });
  const wrapper = mount(RelationshipBrowserView, { global: { plugins: [createPinia(), router] } });
  await flushPromises();
  return { wrapper, router };
}
function reload(wrapper: ReturnType<typeof mount>) {
  return (wrapper.vm as unknown as { load(): Promise<void> }).load();
}
beforeEach(() => {
  vi.clearAllMocks();
  reads.trace.mockImplementation(async (record: { record_id: string }) => graph(record.record_id));
  reads.model.mockResolvedValue(model);
});
describe("Relationships independent reads", () => {
  it("renders a retained trace before the optional model finishes", async () => {
    const delayed = pending<typeof model>();
    reads.model.mockReturnValueOnce(delayed.promise);
    const { wrapper } = await open();
    expect(wrapper.find(".traceability-orientation").exists()).toBe(true);
    expect(wrapper.findComponent(RecordTraceabilityExplorer).props("loading")).toBe(false);
    delayed.resolve(model);
    await flushPromises();
    wrapper.unmount();
  });
  it("keeps a trace after model failure and retries only the model", async () => {
    reads.model.mockRejectedValueOnce(new Error("Model offline"));
    const { wrapper } = await open();
    expect(wrapper.find(".traceability-orientation").exists()).toBe(true);
    await wrapper.get(".relationship-model-status button").trigger("click");
    await flushPromises();
    expect(reads.trace).toHaveBeenCalledTimes(1);
    expect(reads.model).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });
  it("retains graph DOM during same-record refresh and failure", async () => {
    const { wrapper } = await open();
    const orientation = wrapper.get(".traceability-orientation").element;
    const delayed = pending<ReturnType<typeof graph>>();
    reads.trace.mockReturnValueOnce(delayed.promise);
    const operation = reload(wrapper);
    await flushPromises();
    expect(wrapper.get(".traceability-orientation").element).toBe(orientation);
    delayed.reject(new Error("Trace offline"));
    await operation;
    await flushPromises();
    expect(wrapper.get(".traceability-orientation").element).toBe(orientation);
    expect(wrapper.text()).toContain("Trace offline");
    wrapper.unmount();
  });
  it("does not reread the model on record changes and rejects the earlier trace", async () => {
    const delayed = pending<ReturnType<typeof graph>>();
    reads.trace.mockReturnValueOnce(delayed.promise);
    const { wrapper, router } = await open();
    await router.replace({ query: { record: "r2" } });
    await flushPromises();
    delayed.resolve(graph("r1"));
    await flushPromises();
    expect(wrapper.findComponent(RecordTraceabilityExplorer).props("graph")?.root_id).toBe(
      "Record:r2",
    );
    expect(reads.model).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });
  it("reports model-only read failure and keeps a retry available", async () => {
    reads.model.mockRejectedValueOnce(new Error("Model offline"));
    const { wrapper } = await open({ mode: "model" });
    expect(wrapper.get(".relationship-model-status").text()).toContain("Model offline");
    await wrapper.get(".relationship-model-status button").trigger("click");
    await flushPromises();
    expect(reads.model).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });
});
