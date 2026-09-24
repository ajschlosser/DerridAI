/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/runtime/runtime.js", () => ({
  getProviderProfilesForUi: () => [],
  getDefaultProviderProfileId: () => "",
}));

import MetadataSchemasView from "../../src/views/MetadataSchemasView.vue";
import { metadataSchemasApi } from "../../src/api/metadataSchemas";
import { useI18nStore } from "../../src/stores/i18n";

describe("Metadata schemas page", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
    useI18nStore().dictionary = {
      "section.system": "System",
      "schemas.manage_title": "Metadata schemas",
      "schemas.manage_help": "Define the fields on JSONL records.",
    };
    vi.spyOn(metadataSchemasApi, "list").mockResolvedValue({
      items: [
        {
          id: "default",
          name: "DerridAI scholarly default",
          description: "",
          builtin: true,
          field_count: 23,
          groups: [],
          hash: "a",
        },
      ],
    });
    vi.spyOn(metadataSchemasApi, "get").mockResolvedValue({
      format_version: 1,
      id: "default",
      name: "DerridAI scholarly default",
      description: "",
      groups: [],
      fields: [],
    } as never);
  });

  it("hosts the schema editor on a System page", async () => {
    const wrapper = mount(MetadataSchemasView, { attachTo: document.body });
    await flushPromises();
    expect(wrapper.get("#schemas-page-title").text()).toBe("Metadata schemas");
    expect(wrapper.text()).toContain("System");
    expect(wrapper.get(".schema-editor").exists()).toBe(true);
    wrapper.unmount();
  });
});
