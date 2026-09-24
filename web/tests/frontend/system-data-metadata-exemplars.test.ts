/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("../../src/runtime/runtimeBridge", () => ({
  openMessageModal: vi.fn().mockResolvedValue(false),
  notifyToast: vi.fn(),
  formatTimestamp: (value: string) => value,
}));

import { systemApi } from "../../src/api/system";
import SystemDataView from "../../src/views/SystemDataView.vue";
import { useI18nStore } from "../../src/stores/i18n";

describe("System Data metadata exemplars", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
    useI18nStore().dictionary = {
      "runtime.system_data": "System Data",
      "runtime.system_metadata_exemplars": "Metadata exemplars",
      "runtime.system_metadata_exemplars_help":
        "Read-only, evidence-bound examples learned from reviewed metadata decisions.",
      "runtime.system_exemplar_context": "Evidence context",
      "runtime.system_exemplar_record": "Record ID",
      "runtime.system_exemplar_build": "Build",
      "runtime.system_exemplar_schema": "Schema",
      "runtime.system_exemplar_region": "Region",
      "runtime.system_exemplar_evidence_blocks": "Evidence blocks",
      "runtime.system_exemplar_evidence_hash": "Evidence hash",
    };
    vi.spyOn(systemApi, "systemData").mockResolvedValue({ databases: [] });
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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ total: 0, records: [] }),
      }),
    );
  });

  it("renders exemplars as audit-oriented system data", async () => {
    const wrapper = mount(SystemDataView, { attachTo: document.body });
    await flushPromises();

    expect(wrapper.text()).toContain("Metadata exemplars");
    expect(wrapper.text()).toContain("position_holder");
    expect(wrapper.text()).toContain("Levinas");
    expect(wrapper.text()).toContain("record-1");
    expect(wrapper.text()).toContain("b2");
    expect(wrapper.text()).not.toContain("Embedding contract");
    expect(wrapper.text()).not.toContain("Derived vector stores");

    await wrapper.get(".exemplar-context summary").trigger("click");
    expect(wrapper.text()).toContain("For Levinas, responsibility precedes freedom.");

    wrapper.unmount();
  });

  it("passes field and language filters through the System Data API", async () => {
    const wrapper = mount(SystemDataView);
    await flushPromises();

    await wrapper.find('select').setValue("position_holder");
    const selects = wrapper.findAll(".exemplar-filters select");
    await selects[2].setValue("en");
    await wrapper.find(".exemplar-filter-actions .btn").trigger("click");
    await flushPromises();

    expect(systemApi.systemMetadataExemplars).toHaveBeenLastCalledWith(
      expect.objectContaining({
        offset: 0,
        field: "position_holder",
        language: "en",
      }),
    );

    wrapper.unmount();
  });
});
