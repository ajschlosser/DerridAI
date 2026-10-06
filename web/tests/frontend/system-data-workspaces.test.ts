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

const push = vi.fn();
const replace = vi.fn();
const route = { name: "system-data-metadata", query: {} as Record<string, string> };

vi.mock("vue-router", () => ({
  RouterLink: { props: ["to"], template: "<a><slot /></a>" },
  useRoute: () => route,
  useRouter: () => ({ push, replace }),
}));

import { systemApi } from "../../src/api/system";
import SystemDataOverview from "../../src/components/system-data/SystemDataOverview.vue";
import SystemDataDatabases from "../../src/components/system-data/SystemDataDatabases.vue";
import SystemDataAdvanced from "../../src/components/system-data/SystemDataAdvanced.vue";
import SystemDataView from "../../src/views/SystemDataView.vue";
import { useI18nStore } from "../../src/stores/i18n";

describe("System Data workspaces", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().dictionary = {};
    vi.restoreAllMocks();
    push.mockReset();
    replace.mockReset();
    for (const key of Object.keys(route.query)) delete route.query[key];
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

    const wrapper = mount(SystemDataView, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
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
      name: "system-data-advanced",
      query: {},
    });
  });

  it("retains internal vector collections while refresh is pending or fails", async () => {
    const collections = [
      {
        name: "metadata-memory",
        role: "system",
        count: 7,
        derived: false,
      },
    ];
    const read = vi.spyOn(systemApi, "systemChromaCollections").mockResolvedValueOnce({
      collections,
    });

    const wrapper = mount(SystemDataAdvanced);
    await flushPromises();
    expect(wrapper.text()).toContain("metadata-memory");
    expect(wrapper.text()).toContain("Read-only query console");

    let rejectRefresh!: (reason?: unknown) => void;
    read.mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          rejectRefresh = reject;
        }),
    );
    await wrapper.get(".workspace-heading .btn").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("metadata-memory");
    expect(wrapper.text()).toContain("Updating");

    rejectRefresh(new Error("vector service offline"));
    await flushPromises();

    expect(wrapper.text()).toContain("metadata-memory");
    expect(wrapper.text()).toContain("vector service offline");
    expect(wrapper.text()).not.toContain("No internal vector collections are available.");
    wrapper.unmount();
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

    queryClient.clear();
    queryClient.setDefaultOptions({ queries: { retry: false } });
    const wrapper = mount(SystemDataOverview, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("Unavailable");
    expect(wrapper.text()).toContain("12 responses");
    expect(wrapper.text()).toContain("3 examples");
    expect(wrapper.text()).toContain("Corpus data remains separate");
  });
});
