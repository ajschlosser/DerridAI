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

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import WorksOverviewCard from "../../src/components/works/WorksOverviewCard.vue";
import type { WorksItem } from "../../src/types/works";
import { useI18nStore } from "../../src/stores/i18n";

function workItem(overrides: Partial<WorksItem> = {}): WorksItem {
  return {
    work: "Glas",
    count: 12,
    review: 2,
    annotations: 1,
    files: ["glas.jsonl"],
    authors: ["Jacques Derrida"],
    years: ["1974"],
    cover: "",
    citation: "Derrida, Jacques. Glas.",
    year_label: "1974",
    subtitle: "Jacques Derrida · 1974",
    publisher: { field_label: "Publisher", value: "Galilée", mixed: false, unique_count: 0 },
    translator: { field_label: "Translator", value: "", mixed: false, unique_count: 0 },
    metadata: [
      {
        field_id: "derridai.document.document_author",
        field: "document_author",
        field_label: "Document author",
        value: "Jacques Derrida",
        mixed: false,
        unique_count: 0,
        empty: false,
      },
    ],
    status: { kind: "synced", label: "Synced" },
    insights: [
      {
        id: "topics",
        field: "topics",
        title: "Top 5 topics in the work",
        heading: "Top 5 topics",
        type: "bars",
        values: [{ key: "writing", value: 4 }],
      },
    ],
    ...overrides,
  };
}

describe("WorksOverviewCard", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useI18nStore().languages = [
      { code: "en-US", name: "English", flag: "" },
      { code: "fr-CA", name: "Français", flag: "" },
    ] as never;
  });

  it("is inspector content: no page heading, insights disclosed, secondary actions in a menu", () => {
    const wrapper = mount(WorksOverviewCard, {
      props: { work: workItem(), mode: "admin", citationLabel: "Full citation" },
    });
    expect(wrapper.find("h1").exists()).toBe(false);
    expect(wrapper.get("h2#selected-work-title").text()).toBe("Glas");
    expect(wrapper.find("details.works-inspector-insights").exists()).toBe(true);
    expect(wrapper.text()).toContain("Open records");
    expect(wrapper.text()).toContain("Edit metadata");
    expect(wrapper.text()).not.toContain("Populate metadata with LLM");
  });

  it("shows populated metadata by default and lets administrators reveal empty fields", async () => {
    const wrapper = mount(WorksOverviewCard, {
      props: {
        work: workItem({
          metadata: [
            {
              field_id: "derridai.document.document_author",
              field: "document_author",
              field_label: "Document author",
              value: "Jacques Derrida",
              mixed: false,
              unique_count: 0,
              empty: false,
            },
            {
              field_id: "derridai.document.publisher",
              field: "publisher",
              field_label: "Publisher",
              value: "—",
              mixed: false,
              unique_count: 0,
              empty: true,
            },
          ],
        }),
        mode: "admin",
      },
    });

    expect(wrapper.get(".works-inspector-metadata").text()).toContain("Jacques Derrida");
    expect(wrapper.get(".works-inspector-metadata").text()).not.toContain("Publisher");
    const toggle = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Show empty fields"))!;
    await toggle.trigger("click");
    expect(wrapper.get(".works-inspector-metadata").text()).toContain("Publisher");
    expect(wrapper.get(".works-inspector-metadata").text()).toContain("—");
  });

  it("names the cover image from the work title", () => {
    const wrapper = mount(WorksOverviewCard, {
      props: {
        work: workItem({ cover: "https://example.test/glas.jpg" }),
        mode: "admin",
        citationLabel: "Full citation",
      },
    });
    expect(wrapper.get(".works-inspector-cover img").attributes("alt")).toContain("Glas");
    expect(wrapper.get(".works-inspector-cover").attributes("aria-hidden")).toBeUndefined();
  });

  it("offers review only when records need it and emits close for the persistent inspector", async () => {
    const wrapper = mount(WorksOverviewCard, {
      props: { work: workItem({ review: 3 }), mode: "admin", closable: true },
    });
    expect(wrapper.text()).toContain("Review records");
    await wrapper.get("button[aria-label='Close work details']").trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);
    await wrapper.setProps({ work: workItem({ review: 0 }) });
    expect(wrapper.text()).not.toContain("Review records");
  });

  it("does not expose admin operations to researchers", () => {
    const wrapper = mount(WorksOverviewCard, {
      props: { work: workItem(), mode: "researcher" },
    });
    expect(wrapper.text()).toContain("Browse records");
    expect(wrapper.text()).not.toContain("Edit metadata");
    expect(wrapper.find(".ui-menu").exists()).toBe(false);
  });
});
