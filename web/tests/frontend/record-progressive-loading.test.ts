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

import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { reactive, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({
  snapshot: vi.fn(),
  graph: vi.fn(),
  model: vi.fn(),
  semantic: vi.fn(),
}));
vi.mock("../../src/runtime/runtime.js", () => ({
  getRecordWorkspaceSnapshot: mocks.snapshot,
  getRecordObjectGraph: mocks.graph,
  getDerridaiNormativeModel: mocks.model,
}));
vi.mock("../../src/composables/useNewerData", () => ({
  useNewerData: () => ({ hasNewer: ref(false), acknowledge: vi.fn() }),
}));
vi.mock("../../src/api/corpus", () => ({
  corpusBuildsApi: { recordSemanticMapBuild: mocks.semantic },
}));
const route = reactive({
  fullPath: "/record?record=0",
  path: "/record",
  query: { record: "0" } as Record<string, string>,
});
vi.mock("vue-router", () => ({ useRoute: () => route }));
import { compressUrlState } from "../../src/domain/urlState";
import RecordView from "../../src/views/RecordView.vue";
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function record(id: string) {
  return {
    available: true,
    mode: "workspace",
    record_id: id,
    record: { record_id: id, text: id, work: id },
    capabilities: { edit: true },
  };
}
const mountView = () =>
  mount(RecordView, {
    global: {
      stubs: {
        RecordWorkspaceHeader: true,
        RecordReadingPane: true,
        RecordInspector: true,
        RecordEditSheet: true,
        CorpusRecordSemanticMap: true,
        NewerDataBanner: true,
      },
    },
  });
describe("Record progressive loading", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    setActivePinia(createPinia());
    route.fullPath = "/record?record=0";
    route.query = { record: "0" };
    mocks.snapshot.mockResolvedValue(record("A"));
    mocks.graph.mockResolvedValue(null);
    mocks.model.mockResolvedValue(null);
    mocks.semantic.mockResolvedValue({ build_id: null });
  });
  it("shows a frame before the first read and keeps primary content usable while the graph waits", async () => {
    const read = deferred<ReturnType<typeof record>>();
    const graph = deferred<null>();
    mocks.snapshot.mockReturnValueOnce(read.promise);
    mocks.graph.mockReturnValueOnce(graph.promise);
    const wrapper = mountView();
    expect(wrapper.find("h1").exists()).toBe(true);
    expect(wrapper.text()).not.toContain("No record selected");
    read.resolve(record("A"));
    await flushPromises();
    expect(wrapper.findComponent({ name: "RecordReadingPane" }).props("text")).toBe("A");
    graph.resolve(null);
    await flushPromises();
    wrapper.unmount();
  });
  it("preserves the reading pane and open editor through refresh and a failed refresh", async () => {
    const wrapper = mountView();
    await flushPromises();
    wrapper.findComponent({ name: "RecordWorkspaceHeader" }).vm.$emit("edit");
    await flushPromises();
    const pane = wrapper.get("record-reading-pane-stub").element;
    const edit = wrapper.get("record-edit-sheet-stub").element;
    const read = deferred<ReturnType<typeof record>>();
    mocks.snapshot.mockReturnValueOnce(read.promise);
    window.dispatchEvent(new Event("derridai:record-updated"));
    await flushPromises();
    expect(wrapper.get("record-reading-pane-stub").element).toBe(pane);
    expect(wrapper.get("record-edit-sheet-stub").element).toBe(edit);
    read.reject(new Error("offline"));
    await flushPromises();
    expect(wrapper.get("record-reading-pane-stub").element).toBe(pane);
    expect(wrapper.text()).toContain("offline");
    expect(wrapper.findComponent({ name: "RecordEditSheet" }).props("open")).toBe(true);
    wrapper.unmount();
  });
  it("clears a different selection immediately and ignores an older read resolving last", async () => {
    const a = deferred<ReturnType<typeof record>>();
    mocks.snapshot.mockReturnValueOnce(a.promise);
    const wrapper = mountView();
    await flushPromises();
    route.query = { record: "1" };
    route.fullPath = "/record?record=1";
    mocks.snapshot.mockResolvedValueOnce(record("B"));
    await flushPromises();
    a.resolve(record("A"));
    await flushPromises();
    expect(wrapper.findComponent({ name: "RecordReadingPane" }).props("text")).toBe("B");
    wrapper.unmount();
  });
});

describe("Record identity and authorization", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    setActivePinia(createPinia());
    route.query = { record: "0" };
    mocks.snapshot.mockResolvedValue(record("A"));
    mocks.graph.mockResolvedValue(null);
    mocks.model.mockResolvedValue(null);
    mocks.semantic.mockResolvedValue({ build_id: null });
  });
  it("does not reload or unmount the pane when only the find query changes", async () => {
    const wrapper = mountView();
    await flushPromises();
    const pane = wrapper.get("record-reading-pane-stub").element;
    route.query = { record: "0", ts: compressUrlState({ q: "term", rr: "" }) };
    await flushPromises();
    const calls = mocks.snapshot.mock.calls.length;
    route.query = { record: "0", ts: compressUrlState({ q: "other", rr: "" }) };
    await flushPromises();
    expect(wrapper.get("record-reading-pane-stub").element).toBe(pane);
    expect(mocks.snapshot).toHaveBeenCalledTimes(calls);
    wrapper.unmount();
  });
  it("clears retained content on access denial", async () => {
    const wrapper = mountView();
    await flushPromises();
    mocks.snapshot.mockRejectedValueOnce(Object.assign(new Error("Forbidden"), { status: 403 }));
    window.dispatchEvent(new Event("derridai:record-updated"));
    await flushPromises();
    expect(wrapper.find("record-reading-pane-stub").exists()).toBe(false);
    expect(wrapper.text()).toContain("Forbidden");
    wrapper.unmount();
  });
  it("does not apply an old graph after a new record is selected", async () => {
    const graph = deferred<null>();
    mocks.graph.mockReturnValueOnce(graph.promise);
    const wrapper = mountView();
    await flushPromises();
    mocks.snapshot.mockResolvedValueOnce(record("B"));
    route.query = { record: "1" };
    await flushPromises();
    graph.resolve(null);
    await flushPromises();
    expect(wrapper.findComponent({ name: "RecordReadingPane" }).props("text")).toBe("B");
    wrapper.unmount();
  });
});
