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
import { queryClient } from "../../src/realtime/dataQuery";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { routerPush, routerReplace, routeQuery } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routerReplace: vi.fn(),
  routeQuery: {} as Record<string, string>,
}));

vi.mock("vue-router", () => ({
  useRoute: () => ({ query: routeQuery }),
  useRouter: () => ({ push: routerPush, replace: routerReplace }),
}));

vi.mock("../../src/composables/messageDialog", () => ({
  openMessageDialog: vi.fn(),
}));

import { systemApi } from "../../src/api/system";
import { openMessageDialog } from "../../src/composables/messageDialog";
import SystemDataResponses from "../../src/components/system-data/SystemDataResponses.vue";
import { useI18nStore } from "../../src/stores/i18n";

describe("System Data saved responses", () => {
  beforeEach(() => {
    queryClient.clear();
    queryClient.setDefaultOptions({ queries: { retry: false } });
    setActivePinia(createPinia());
    useI18nStore().dictionary = {};
    vi.restoreAllMocks();
    routerPush.mockReset();
    routerReplace.mockReset();
    for (const key of Object.keys(routeQuery)) delete routeQuery[key];
    vi.spyOn(systemApi, "responseCacheRecords").mockResolvedValue({
      exists: true,
      total: 1,
      limit: 25,
      offset: 0,
      records: [
        {
          record_id: "rag-1",
          question: "What is différance?",
          created_at: "2026-09-24T12:00:00Z",
          generation_model: "qwen",
        },
      ],
    });
  });

  it("sends search and pagination through the response API", async () => {
    const wrapper = mount(SystemDataResponses, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();

    await wrapper.get('input[type="search"]').setValue("différance");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(systemApi.responseCacheRecords).toHaveBeenLastCalledWith(25, 0, "différance");
    expect(routerReplace).toHaveBeenLastCalledWith({
      name: "system-data-responses",
      query: { q: "différance", offset: undefined },
    });
    expect(wrapper.text()).toContain("What is différance?");
  });

  it("restores response search and pagination from the URL", async () => {
    routeQuery.q = "difference";
    routeQuery.offset = "25";

    const wrapper = mount(SystemDataResponses, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();

    const searchInput = wrapper.get('input[type="search"]').element as HTMLInputElement;
    expect(searchInput.value).toBe("difference");
    expect(systemApi.responseCacheRecords).toHaveBeenCalledWith(25, 25, "difference");
    wrapper.unmount();
  });

  it("deep-links a row into the selected Response Library response", async () => {
    const wrapper = mount(SystemDataResponses, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();

    await wrapper.get(".row-actions .btn").trigger("click");

    expect(routerPush).toHaveBeenCalledWith({
      path: "/faq",
      query: { id: "rag-1" },
    });
  });

  it("requires destructive confirmation before deleting a saved response", async () => {
    vi.mocked(openMessageDialog).mockResolvedValue(false);
    const remove = vi.spyOn(systemApi, "deleteSystemResponseCacheRecord");

    const wrapper = mount(SystemDataResponses, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();
    await wrapper.get(".danger-text").trigger("click");

    expect(openMessageDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        tone: "danger",
        message: "What is différance?",
      }),
    );
    expect(remove).not.toHaveBeenCalled();
  });
});
