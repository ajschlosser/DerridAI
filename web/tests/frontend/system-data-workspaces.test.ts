/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const route = { query: { section: "metadata" } };

vi.mock("vue-router", () => ({
  useRoute: () => route,
  useRouter: () => ({ push }),
}));

import { systemApi } from "../../src/api/system";
import SystemDataOverview from "../../src/components/system-data/SystemDataOverview.vue";
import SystemDataView from "../../src/views/SystemDataView.vue";
import { useI18nStore } from "../../src/stores/i18n";

describe("System Data workspaces", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().dictionary = {};
    vi.restoreAllMocks();
    push.mockReset();
  });

  it("restores the selected workspace from the URL and writes navigation back to it", async () => {
    vi.spyOn(systemApi, "systemMetadataExemplars").mockResolvedValue({
      exists: false,
      count: 0,
      limit: 25,
      offset: 0,
      rows: [],
      facets: { fields: [], kinds: [], languages: [], scopes: [], schemas: [] },
    });

    const wrapper = mount(SystemDataView);
    await flushPromises();

    expect(wrapper.get("h1").text()).toBe("System Data");
    expect(wrapper.text()).not.toContain("System DataSystem Data");
    expect((wrapper.get("#system-data-section").element as HTMLSelectElement).value).toBe(
      "metadata",
    );

    const advanced = wrapper
      .findAll(".section-rail button")
      .find((button) => button.text().includes("Advanced"));
    expect(advanced).toBeTruthy();
    await advanced!.trigger("click");
    expect(push).toHaveBeenCalledWith({
      path: "/system-data",
      query: { section: "advanced" },
    });
  });

  it("keeps healthy stores visible when one overview source fails", async () => {
    vi.spyOn(systemApi, "systemData").mockRejectedValue(new Error("sqlite offline"));
    vi.spyOn(systemApi, "responseCacheRecords").mockResolvedValue({
      exists: true,
      records: [],
      total: 12,
      limit: 1,
      offset: 0,
    });
    vi.spyOn(systemApi, "systemMetadataExemplars").mockResolvedValue({
      exists: true,
      count: 3,
      limit: 1,
      offset: 0,
      rows: [],
      facets: { fields: [], kinds: [], languages: [], scopes: [], schemas: [] },
    });
    vi.spyOn(systemApi, "systemChromaCollections").mockResolvedValue({ collections: [] });

    const wrapper = mount(SystemDataOverview);
    await flushPromises();

    expect(wrapper.text()).toContain("Unavailable");
    expect(wrapper.text()).toContain("12 responses");
    expect(wrapper.text()).toContain("3 examples");
    expect(wrapper.text()).toContain("Corpus data remains separate");
  });
});
