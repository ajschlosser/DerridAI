/* Copyright 2026 Aaron John Schlosser, PhD. */
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
        field: "document_author",
        field_label: "Document author",
        value: "Jacques Derrida",
        mixed: false,
        unique_count: 0,
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

  it("keeps the cover in the masthead so insights use the full content width", () => {
    const wrapper = mount(WorksOverviewCard, {
      props: { work: workItem(), mode: "admin", citationLabel: "Full citation" },
    });
    expect(wrapper.find(".work-overview-card > .work-overview-cover").exists()).toBe(false);
    expect(wrapper.find(".work-overview-masthead .work-overview-cover").exists()).toBe(true);
    expect(wrapper.find(".work-overview-content .work-insights-panel").exists()).toBe(true);
    expect(wrapper.find("img, .work-cover-placeholder").exists()).toBe(true);
  });

  it("names the cover image from the work title", () => {
    const wrapper = mount(WorksOverviewCard, {
      props: {
        work: workItem({ cover: "https://example.test/glas.jpg" }),
        mode: "admin",
        citationLabel: "Full citation",
      },
    });
    expect(wrapper.get(".work-overview-cover img").attributes("alt")).toContain("Glas");
    expect(wrapper.get(".work-overview-cover").attributes("aria-hidden")).toBeUndefined();
  });
});
