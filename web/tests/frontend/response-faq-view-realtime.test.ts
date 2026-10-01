/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
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

const record = (id: string, question: string) => ({ record_id: id, question, text: question });
const page = (records: ReturnType<typeof record>[]) => ({
  records,
  count: records.length,
  total: records.length,
});

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/faq", component: ResponseFaqView }],
  });
  await router.push("/faq");
  await router.isReady();
  const wrapper = mount(ResponseFaqView, {
    attachTo: document.body,
    global: { plugins: [createPinia(), router, [VueQueryPlugin, { queryClient }]] },
  });
  await flushPromises();
  return wrapper;
}

describe("ResponseFaqView server state", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    queryClient.clear();
    bridge.getResponseFaqPage.mockReset();
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
