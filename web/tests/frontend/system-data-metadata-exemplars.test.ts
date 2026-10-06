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

import { systemApi } from "../../src/api/system";
import SystemDataMetadataExamples from "../../src/components/system-data/SystemDataMetadataExamples.vue";
import { useI18nStore } from "../../src/stores/i18n";

describe("System Data metadata examples", () => {
  beforeEach(() => {
    queryClient.clear();
    queryClient.setDefaultOptions({ queries: { retry: false } });
    setActivePinia(createPinia());
    vi.restoreAllMocks();
    routerPush.mockReset();
    routerReplace.mockReset();
    for (const key of Object.keys(routeQuery)) delete routeQuery[key];
    useI18nStore().dictionary = {};
    vi.spyOn(systemApi, "systemMetadataExemplars").mockResolvedValue({
      exists: true,
      count: 1,
      limit: 25,
      offset: 0,
      facets: {
        fields: ["position_holder"],
        kinds: ["positive"],
        languages: ["en"],
        scopes: ["build-1"],
        schemas: ["derrida"],
      },
      rows: [
        {
          exemplar_id: "mex-1",
          scope_id: "build-1",
          record_id: "record-1",
          record_revision: 4,
          source_document_id: "asset-1",
          field_name: "position_holder",
          field_value: "Levinas",
          kind: "positive",
          assertion_status: "human_confirmed",
          schema_id: "derrida",
          schema_version: "v7",
          language: "en",
          region_type: "main_text",
          evidence_hash: "abc123",
          evidence_block_ids: ["b2"],
          context_text: "For Levinas, responsibility precedes freedom.",
        },
      ],
    });
  });

  it("renders field/value first and reveals exact provenance details", async () => {
    const wrapper = mount(SystemDataMetadataExamples, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
      attachTo: document.body,
    });
    await flushPromises();

    expect(wrapper.text()).toContain("position_holder");
    expect(wrapper.text()).toContain("Levinas");
    expect(wrapper.text()).toContain("record-1");

    await wrapper.get(".example-row").trigger("click");
    expect(wrapper.text()).toContain("human_confirmed");
    expect(wrapper.text()).toContain("build-1");
    expect(wrapper.text()).toContain("b2");
    expect(wrapper.text()).toContain("abc123");
    expect(wrapper.text()).toContain("For Levinas, responsibility precedes freedom.");

    wrapper.unmount();
  });

  it("retains reviewed exemplars during a same-filter refresh failure", async () => {
    const wrapper = mount(SystemDataMetadataExamples, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("Levinas");

    let rejectRefresh!: (reason?: unknown) => void;
    vi.mocked(systemApi.systemMetadataExemplars).mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          rejectRefresh = reject;
        }),
    );
    await wrapper.get("form.filters").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("Levinas");
    expect(wrapper.text()).toContain("Updating");

    rejectRefresh(new Error("exemplar projection offline"));
    await flushPromises();

    expect(wrapper.text()).toContain("Levinas");
    expect(wrapper.text()).toContain("exemplar projection offline");
    expect(wrapper.text()).not.toContain("no examples match");
    wrapper.unmount();
  });

  it("withholds previous exemplars and counts when a new filter identity is pending", async () => {
    const wrapper = mount(SystemDataMetadataExamples, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();

    let resolveFilter!: (
      value: Awaited<ReturnType<typeof systemApi.systemMetadataExemplars>>,
    ) => void;
    vi.mocked(systemApi.systemMetadataExemplars).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFilter = resolve;
        }),
    );
    const selects = wrapper.findAll(".filters select");
    await selects[1].setValue("positive");
    await wrapper.get("form.filters").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).not.toContain("Levinas");
    expect(wrapper.get(".workspace-heading > strong").text()).toBe("—");
    expect(wrapper.text()).toContain("Loading metadata examples");

    resolveFilter({
      exists: true,
      count: 0,
      limit: 25,
      offset: 0,
      facets: {
        fields: ["position_holder"],
        kinds: ["positive"],
        languages: ["en"],
        scopes: ["build-1"],
        schemas: ["derrida"],
      },
      rows: [],
    });
    await flushPromises();

    expect(wrapper.get(".workspace-heading > strong").text()).toBe("0");
    expect(wrapper.text()).toContain("no examples match");
    wrapper.unmount();
  });

  it("passes field and language filters through the System Data API", async () => {
    const wrapper = mount(SystemDataMetadataExamples, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();

    const selects = wrapper.findAll(".filters select");
    await selects[0].setValue("position_holder");
    await selects[2].setValue("en");
    await flushPromises();
    await wrapper.get("form.filters").trigger("submit");
    await flushPromises();

    expect(systemApi.systemMetadataExemplars).toHaveBeenLastCalledWith(
      expect.objectContaining({
        offset: 0,
        field: "position_holder",
        language: "en",
      }),
    );
    expect(routerReplace).toHaveBeenLastCalledWith({
      name: "system-data-metadata",
      query: {
        field: "position_holder",
        kind: undefined,
        language: "en",
        build: undefined,
        schema: undefined,
        record: undefined,
        offset: undefined,
      },
    });
  });

  it("restores metadata filters and pagination from the URL", async () => {
    routeQuery.field = "position_holder";
    routeQuery.language = "en";
    routeQuery.build = "build-1";
    routeQuery.schema = "derrida";
    routeQuery.record = "record-1";
    routeQuery.offset = "25";

    const wrapper = mount(SystemDataMetadataExamples, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();

    expect(systemApi.systemMetadataExemplars).toHaveBeenCalledWith(
      expect.objectContaining({
        field: "position_holder",
        language: "en",
        scope_id: "build-1",
        schema_id: "derrida",
        record_id: "record-1",
        offset: 25,
      }),
    );
    wrapper.unmount();
  });

  it("distinguishes a missing index from a built index with no matches", async () => {
    vi.mocked(systemApi.systemMetadataExemplars).mockResolvedValueOnce({
      exists: false,
      count: 0,
      limit: 25,
      offset: 0,
      rows: [],
      facets: { fields: [], kinds: [], languages: [], scopes: [], schemas: [] },
    });
    const missing = mount(SystemDataMetadataExamples, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();
    expect(missing.text()).toContain("has not been built");
    missing.unmount();

    vi.mocked(systemApi.systemMetadataExemplars).mockResolvedValueOnce({
      exists: true,
      count: 0,
      limit: 25,
      offset: 0,
      rows: [],
      facets: { fields: [], kinds: [], languages: [], scopes: [], schemas: [] },
    });
    const empty = mount(SystemDataMetadataExamples, {
      global: { plugins: [[VueQueryPlugin, { queryClient }]] },
    });
    await flushPromises();
    expect(empty.text()).toContain("no examples match");
  });
});
