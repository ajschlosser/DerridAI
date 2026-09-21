/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const records = {
  a: {record_id: "r-a", work: "Glas", document_author: "Derrida", text: "left"},
  b: {record_id: "r-b", work: "Glas", document_author: "Derrida", text: "right"},
};
const runtime = vi.hoisted(() => ({
  persistPrefs: vi.fn(),
  getCompareLibrary: vi.fn(() => [
    {value: "f::0", label: "tab.jsonl · r-a · Glas", search: "derrida"},
    {value: "f::1", label: "tab.jsonl · r-b · Glas", search: "derrida"},
  ]),
  getCompareRecord: vi.fn((key: string) => key === "f::0" ? {record: records.a, label: "r-a"} : key === "f::1" ? {record: records.b, label: "r-b"} : null),
  ensureCompareLibrary: vi.fn(async () => undefined),
  copyJsonToClipboard: vi.fn(),
  copyCitation: vi.fn(),
  // Only the runtime-owned fields; the shared Compare fields come from the compare store.
  state: { researcherCompareA: "", researcherCompareB: "" },
}));
vi.mock("../../src/runtime/runtime.js", () => ({...runtime}));

import CompareView from "../../src/views/CompareView.vue";
import { compareState, createCompareState, touchCorpus } from "../../src/state/workspaceState";
import { useAuthStore } from "../../src/stores/auth";
import { useI18nStore } from "../../src/stores/i18n";

async function mountView() {
  const pinia = createPinia();
  setActivePinia(pinia);
  useAuthStore().user = {id: 1, username: "u", role: "admin", capabilities: []} as never;
  useI18nStore().languages = [{code: "en-US", name: "English", flag: "🇺🇸"}] as never;
  const router = createRouter({history: createMemoryHistory(), routes: [{path: "/compare", component: CompareView}]});
  await router.push("/compare");
  await router.isReady();
  const wrapper = mount(CompareView, {attachTo: document.body, global: {plugins: [pinia, router]}});
  await flushPromises();
  return wrapper;
}

describe("CompareView", () => {
  beforeEach(() => {
    Object.assign(compareState, createCompareState(), { compareA: "f::0" });
  });

  it("loads a library record into the A editor so copies can be edited beside the original", async () => {
    const wrapper = await mountView();
    await wrapper.findAll("button").find(button => button.text().includes("Load into editor"))?.trigger("click");
    await flushPromises();
    expect((wrapper.get("#compare-editor-A").element as HTMLTextAreaElement).value).toContain('"record_id": "r-a"');
    expect(wrapper.text()).toContain("Editable copy");
  });

  it("shows a live text difference after pasting two valid records", async () => {
    const wrapper = await mountView();
    const tabs = wrapper.findAll('[role="tab"]');
    await tabs[1]?.trigger("click");
    await tabs[3]?.trigger("click");
    await wrapper.get("#compare-editor-A").setValue(JSON.stringify(records.a));
    await wrapper.get("#compare-editor-B").setValue(JSON.stringify(records.b));
    await flushPromises();
    expect(wrapper.text()).toContain("changed");
    expect(wrapper.text()).toContain("text");
  });

  it("reads the record library again when the loaded corpus changes while it is open", async () => {
    const wrapper = await mountView();
    const before = runtime.getCompareLibrary.mock.calls.length;
    runtime.getCompareLibrary.mockReturnValueOnce([{value: "f2::0", label: "new.jsonl · r-new · Late Work", search: "late"}] as never);
    touchCorpus();
    await flushPromises();
    expect(runtime.getCompareLibrary.mock.calls.length).toBeGreaterThan(before);
    wrapper.unmount();
  });
});
