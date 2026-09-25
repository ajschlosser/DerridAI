/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { systemApi } from "../../src/api/system";
import SystemDataMetadataExamples from "../../src/components/system-data/SystemDataMetadataExamples.vue";
import { useI18nStore } from "../../src/stores/i18n";

describe("System Data metadata examples", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
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
    const wrapper = mount(SystemDataMetadataExamples, { attachTo: document.body });
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

  it("passes field and language filters through the System Data API", async () => {
    const wrapper = mount(SystemDataMetadataExamples);
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
    const missing = mount(SystemDataMetadataExamples);
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
    const empty = mount(SystemDataMetadataExamples);
    await flushPromises();
    expect(empty.text()).toContain("no examples match");
  });
});
