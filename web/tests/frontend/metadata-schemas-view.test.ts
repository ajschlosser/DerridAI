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
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/domain/sharedProviderProfiles", () => ({
  getProviderProfilesForUi: () => [],
  getDefaultProviderProfileId: () => "",
}));
vi.mock("../../src/domain/appBootstrap", () => ({
  getProviderProfilesForUi: () => [],
  getDefaultProviderProfileId: () => "",
}));

import MetadataSchemasView from "../../src/views/MetadataSchemasView.vue";
import { metadataSchemasApi } from "../../src/api/metadataSchemas";
import { useI18nStore } from "../../src/stores/i18n";

async function mountView(query: Record<string, string> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/schemas", name: "schemas", component: { template: "<div />" } }],
  });
  await router.push({ name: "schemas", query });
  await router.isReady();
  return {
    router,
    wrapper: mount(MetadataSchemasView, {
      attachTo: document.body,
      global: { plugins: [router] },
    }),
  };
}

describe("Metadata schemas page", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
    useI18nStore().dictionary = {
      "section.system": "System",
      "section.corpus_management": "Corpus Management",
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

  it("hosts the schema editor in Corpus Management", async () => {
    const { wrapper } = await mountView();
    await flushPromises();
    expect(wrapper.get("#schemas-page-title").text()).toBe("Metadata schemas");
    expect(wrapper.text()).toContain("Corpus Management");
    expect(wrapper.find(".schema-editor").exists()).toBe(true);
    wrapper.unmount();
  });

  it("restores schema and tab selection from the URL", async () => {
    vi.spyOn(metadataSchemasApi, "list").mockResolvedValueOnce({
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
        {
          id: "notes",
          name: "Notes",
          description: "",
          builtin: false,
          field_count: 2,
          groups: [],
          hash: "b",
        },
      ],
    });
    vi.spyOn(metadataSchemasApi, "get").mockImplementationOnce(async () => {
      return {
        format_version: 1,
        id: "notes",
        name: "Notes",
        description: "",
        groups: [],
        fields: [],
      } as never;
    });

    const { wrapper, router } = await mountView({ schema: "notes", tab: "groups" });
    await flushPromises();

    expect(metadataSchemasApi.get).toHaveBeenCalledWith("notes");
    expect(wrapper.get("#schema-tab-groups").attributes("aria-selected")).toBe("true");

    await wrapper.get("#schema-tab-preview").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.tab).toBe("preview");
    wrapper.unmount();
  });

  it("offers a New schema that starts empty but keeps the built-in groups", async () => {
    vi.spyOn(metadataSchemasApi, "get").mockResolvedValue({
      format_version: 1,
      id: "default",
      name: "DerridAI scholarly default",
      description: "",
      groups: [
        {
          key: "discourse",
          label: "Discourse",
          intro: "Intro",
          notes: [],
          trailer: "",
          footer: "",
        },
      ],
      fields: [],
    } as never);
    const { wrapper } = await mountView();
    await flushPromises();
    await wrapper.get("button.new-schema").trigger("click");
    await flushPromises();
    expect(wrapper.find(".schema-item.is-new").exists()).toBe(true);
    expect(wrapper.get(".schema-item.is-new").text()).toContain("New schema");
    wrapper.unmount();
  });
});
