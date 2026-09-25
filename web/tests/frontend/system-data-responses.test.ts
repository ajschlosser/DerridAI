/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: routerPush }),
}));

vi.mock("../../src/runtime/runtimeBridge", () => ({
  openMessageModal: vi.fn(),
  notifyToast: vi.fn(),
  formatTimestamp: (value: string) => value,
}));

import { systemApi } from "../../src/api/system";
import * as runtime from "../../src/runtime/runtimeBridge";
import SystemDataResponses from "../../src/components/system-data/SystemDataResponses.vue";
import { useI18nStore } from "../../src/stores/i18n";

describe("System Data saved responses", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().dictionary = {};
    vi.restoreAllMocks();
    routerPush.mockReset();
    vi.spyOn(systemApi, "responseCacheRecords").mockResolvedValue({
      exists: true,
      total: 1,
      limit: 25,
      offset: 0,
      records: [{
        record_id: "rag-1",
        question: "What is différance?",
        created_at: "2026-09-24T12:00:00Z",
        generation_model: "qwen",
      }],
    });
  });

  it("sends search and pagination through the response API", async () => {
    const wrapper = mount(SystemDataResponses);
    await flushPromises();

    await wrapper.get('input[type="search"]').setValue("différance");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(systemApi.responseCacheRecords).toHaveBeenLastCalledWith(25, 0, "différance");
    expect(wrapper.text()).toContain("What is différance?");
  });

  it("deep-links a row into the selected Response Library response", async () => {
    const wrapper = mount(SystemDataResponses);
    await flushPromises();

    await wrapper.get(".row-actions .btn").trigger("click");

    expect(routerPush).toHaveBeenCalledWith({
      path: "/faq",
      query: { id: "rag-1" },
    });
  });

  it("requires destructive confirmation before deleting a saved response", async () => {
    vi.mocked(runtime.openMessageModal).mockResolvedValue(false);
    const remove = vi.spyOn(systemApi, "deleteSystemResponseCacheRecord");

    const wrapper = mount(SystemDataResponses);
    await flushPromises();
    await wrapper.get(".danger-text").trigger("click");

    expect(runtime.openMessageModal).toHaveBeenCalledWith(
      expect.objectContaining({
        tone: "danger",
        message: "What is différance?",
      }),
    );
    expect(remove).not.toHaveBeenCalled();
  });
});
