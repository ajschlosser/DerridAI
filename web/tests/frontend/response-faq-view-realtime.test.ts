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
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const bridge = vi.hoisted(() => ({
  getResponseFaqPage: vi.fn(),
  notifyToast: vi.fn(),
  gradeResponseFaqRecord: vi.fn(),
  rerunResponseFaqRecord: vi.fn(),
}));
vi.mock("../../src/runtime/runtimeBridge", () => bridge);

import ResponseFaqView from "../../src/views/ResponseFaqView.vue";
import { queryClient } from "../../src/realtime/dataQuery";
import { dataKey } from "../../src/realtime/resourceKeys";
import { useAuthStore } from "../../src/stores/auth";
import ResponseFaqArchiveDialog from "../../src/components/research/ResponseFaqArchiveDialog.vue";

const record = (id: string, question: string) => ({ record_id: id, question, text: question });
const page = (records: ReturnType<typeof record>[]) => ({
  records,
  count: records.length,
  total: records.length,
});

const mounted: Array<ReturnType<typeof mount>> = [];
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
async function mountView(url = "/faq") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/faq", component: ResponseFaqView }],
  });
  await router.push(url);
  await router.isReady();
  const pinia = createPinia();
  useAuthStore(pinia).user = { id: "reader", role: "admin", capabilities: [] } as never;
  const wrapper = mount(ResponseFaqView, {
    attachTo: document.body,
    global: { plugins: [pinia, router, [VueQueryPlugin, { queryClient }]] },
  });
  mounted.push(wrapper);
  await flushPromises();
  return wrapper;
}

describe("ResponseFaqView server state", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    queryClient.clear();
    queryClient.setDefaultOptions({ queries: { retry: false, staleTime: 30_000 } });
    bridge.getResponseFaqPage.mockReset();
  });
  afterEach(() => {
    mounted.splice(0).forEach((wrapper) => wrapper.unmount());
    queryClient.clear();
  });

  it("mounts the archive frame without claiming zero questions on a delayed first read", async () => {
    const read = deferred<ReturnType<typeof page>>();
    bridge.getResponseFaqPage.mockReturnValue(read.promise);
    const wrapper = await mountView();
    expect(wrapper.find("#response-faq-title").exists()).toBe(true);
    expect(wrapper.find(".response-faq-page-actions").text()).toContain("Find");
    expect(wrapper.find(".response-faq-loading .is-skeleton").exists()).toBe(true);
    const archive = wrapper.findComponent(ResponseFaqArchiveDialog);
    expect(archive.props("ready")).toBe(false);
    read.resolve(page([record("a", "First question")]));
    await flushPromises();
  });

  it("reports initial failure locally and retries instead of showing an empty library", async () => {
    bridge.getResponseFaqPage.mockRejectedValue(new Error("Unavailable"));
    const wrapper = await mountView();
    expect(wrapper.find(".response-faq-read-error").text()).toContain("Unavailable");
    expect(wrapper.findComponent(ResponseFaqArchiveDialog).props("error")).toContain("Unavailable");
    bridge.getResponseFaqPage.mockResolvedValue(page([record("a", "Recovered")]));
    await wrapper.find(".response-faq-read-error button").trigger("click");
    await flushPromises();
    expect(wrapper.find(".response-faq-workspace").text()).toContain("Recovered");
  });

  it("retains answer DOM through refresh failure and clears the error on identical-data recovery", async () => {
    const data = page([record("a", "First question")]);
    bridge.getResponseFaqPage.mockResolvedValue(data);
    const wrapper = await mountView();
    const frame = wrapper.find(".response-faq-workspace").element;
    bridge.getResponseFaqPage.mockRejectedValue(new Error("Offline"));
    await queryClient.invalidateQueries({ queryKey: dataKey("response_library") });
    await flushPromises();
    expect(wrapper.find(".response-faq-workspace").element).toBe(frame);
    expect(wrapper.find(".response-faq-read-error").text()).toContain("Offline");
    bridge.getResponseFaqPage.mockResolvedValue(data);
    await wrapper.find(".response-faq-read-error button").trigger("click");
    await flushPromises();
    expect(wrapper.find(".response-faq-read-error").exists()).toBe(false);
    expect(wrapper.find(".response-faq-workspace").element).toBe(frame);
  });

  it("uses a fresh cached revisit without another request", async () => {
    bridge.getResponseFaqPage.mockResolvedValue(page([record("a", "First question")]));
    const first = await mountView();
    first.unmount();
    const second = await mountView();
    expect(second.find(".response-faq-workspace").text()).toContain("First question");
    expect(bridge.getResponseFaqPage).toHaveBeenCalledTimes(1);
  });

  it("clears rows for a changed filter, retains the independent answer and rejects a late older page", async () => {
    bridge.getResponseFaqPage.mockResolvedValue(page([record("a", "First question")]));
    const wrapper = await mountView();
    const old = deferred<ReturnType<typeof page>>();
    bridge.getResponseFaqPage.mockImplementation(({ query }) =>
      query === "old" ? old.promise : Promise.resolve(page([record("b", "New question")])),
    );
    const archive = wrapper.findComponent(ResponseFaqArchiveDialog);
    archive.vm.$emit("search", "old");
    await new Promise((resolve) => setTimeout(resolve, 280));
    await flushPromises();
    expect(archive.props("records")).toEqual([]);
    expect(wrapper.find(".response-faq-workspace").text()).toContain("First question");
    archive.vm.$emit("search", "new");
    await new Promise((resolve) => setTimeout(resolve, 280));
    await flushPromises();
    old.resolve(page([record("old", "Wrong question")]));
    await flushPromises();
    expect(archive.props("records")).toEqual([record("b", "New question")]);
    expect(wrapper.text()).not.toContain("Wrong question");
    expect(wrapper.find(".response-faq-workspace").text()).toContain("First question");
  });

  it("clears inaccessible answers after authorization failure", async () => {
    bridge.getResponseFaqPage.mockResolvedValue(page([record("a", "Private question")]));
    const wrapper = await mountView();
    bridge.getResponseFaqPage.mockRejectedValue(
      Object.assign(new Error("Forbidden"), { status: 403 }),
    );
    await queryClient.invalidateQueries({ queryKey: dataKey("response_library") });
    await flushPromises();
    expect(wrapper.find(".response-faq-workspace").exists()).toBe(false);
    expect(wrapper.findComponent(ResponseFaqArchiveDialog).props("records")).toEqual([]);
    expect(wrapper.find(".response-faq-read-error").text()).toContain("Forbidden");
  });

  it("changes a deep-linked answer atomically with its evidence and rejects an earlier route read", async () => {
    const a = { ...record("a", "Answer A"), evidence: [{ text: "Evidence A" }] };
    const b = { ...record("b", "Answer B"), evidence: [{ text: "Evidence B" }] };
    bridge.getResponseFaqPage.mockResolvedValue(page([a]));
    const wrapper = await mountView("/faq?id=a");
    const old = deferred<ReturnType<typeof page>>();
    const current = deferred<ReturnType<typeof page>>();
    bridge.getResponseFaqPage.mockImplementation(({ query }) =>
      query === "old" ? old.promise : current.promise,
    );
    const router = wrapper.vm.$router;
    await router.push("/faq?q=old&id=old");
    await flushPromises();
    expect(wrapper.find(".response-faq-workspace").exists()).toBe(false);
    await router.push("/faq?q=current&id=b");
    await flushPromises();
    current.resolve(page([b]));
    await flushPromises();
    old.resolve(page([record("old", "Wrong answer")]));
    await flushPromises();
    expect(wrapper.find(".response-faq-workspace").text()).toContain("Answer B");
    expect(wrapper.text()).not.toContain("Answer A");
    expect(router.currentRoute.value.query.id).toBe("b");
  });

  it("clears the former account cache on a scope change", async () => {
    bridge.getResponseFaqPage.mockResolvedValue(page([record("a", "Private question")]));
    const wrapper = await mountView();
    const auth = useAuthStore();
    auth.user = null;
    await flushPromises();
    expect(wrapper.find(".response-faq-workspace").exists()).toBe(false);
    expect(
      queryClient.getQueriesData({
        queryKey: dataKey("response_library", "workspace", JSON.stringify(["reader", "admin", []])),
      }),
    ).toEqual([]);
  });

  it("cancels the debounced archive search on unmount", async () => {
    bridge.getResponseFaqPage.mockResolvedValue(page([record("a", "First question")]));
    const wrapper = await mountView();
    wrapper.findComponent(ResponseFaqArchiveDialog).vm.$emit("search", "later");
    await flushPromises();
    wrapper.unmount();
    await new Promise((resolve) => setTimeout(resolve, 280));
    expect(bridge.getResponseFaqPage).toHaveBeenCalledTimes(1);
  });

  it("refetches the same page on a response_library invalidation", async () => {
    bridge.getResponseFaqPage.mockResolvedValue(page([record("a", "First question")]));
    const wrapper = await mountView();
    expect(bridge.getResponseFaqPage).toHaveBeenCalledTimes(1);

    bridge.getResponseFaqPage.mockResolvedValue(
      page([record("a", "First question"), record("b", "Second question")]),
    );
    await queryClient.invalidateQueries({ queryKey: dataKey("response_library") });
    await flushPromises();

    expect(bridge.getResponseFaqPage).toHaveBeenCalledTimes(2);
    expect(bridge.getResponseFaqPage.mock.calls[1][0]).toEqual(
      bridge.getResponseFaqPage.mock.calls[0][0],
    );
    wrapper.unmount();
  });
});
