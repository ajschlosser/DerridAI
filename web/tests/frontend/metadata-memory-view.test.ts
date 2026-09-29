/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { metadataMemoryApi } from "../../src/api/metadataMemory";
import { useI18nStore } from "../../src/stores/i18n";
import MetadataMemoryView from "../../src/views/MetadataMemoryView.vue";

const dictionary = {
  "section.system": "System",
  "metadata_memory.title": "Metadata memory",
  "metadata_memory.help": "Inspect reviewed precedents.",
  "metadata_memory.refresh": "Refresh",
  "metadata_memory.authority_title": "Authority:",
  "metadata_memory.authority_help": "Reviewed corpus metadata remains authoritative.",
  "metadata_memory.summary": "Metadata memory summary",
  "metadata_memory.entries": "Precedents",
  "metadata_memory.evidence_bound": "Evidence-bound",
  "metadata_memory.corrections": "Corrections",
  "metadata_memory.fields": "Fields",
  "metadata_memory.unavailable": "Metadata memory is unavailable",
  "metadata_memory.search": "Search",
  "metadata_memory.search_placeholder": "Search memory",
  "metadata_memory.field": "Field",
  "metadata_memory.all_fields": "All fields",
  "metadata_memory.kind": "Precedent type",
  "metadata_memory.all_kinds": "All types",
  "metadata_memory.build": "Corpus build",
  "metadata_memory.all_builds": "All builds",
  "metadata_memory.language": "Language",
  "metadata_memory.all_languages": "All languages",
  "metadata_memory.apply_filters": "Apply filters",
  "metadata_memory.clear_filters": "Clear filters",
  "metadata_memory.precedents": "Learned precedents",
  "metadata_memory.showing": "Showing {start}–{end} of {total}",
  "metadata_memory.loading": "Loading",
  "metadata_memory.field_value": "Field / reviewed value",
  "metadata_memory.authority": "Review authority",
  "metadata_memory.source": "Source record",
  "metadata_memory.scope": "Scope",
  "metadata_memory.evidence": "Evidence and indexed context",
  "metadata_memory.rejected_value": "Rejected model value",
  "metadata_memory.bound": "Evidence-bound",
  "metadata_memory.page": "Page",
  "metadata_memory.source_stale": "Source revision could not be confirmed.",
  "metadata_memory.evidence_unresolved": "Evidence could not be resolved.",
  "metadata_memory.context_only": "Context-only reviewer memory.",
  "metadata_memory.blocks": "Evidence blocks",
  "metadata_memory.indexed_context": "Indexed context",
  "metadata_memory.empty": "No metadata precedents match these filters.",
  "metadata_memory.kind_positive": "Reviewed precedent",
  "metadata_memory.kind_correction": "Correction / negative precedent",
  "common.previous": "Previous",
  "common.next": "Next",
};

const RouterLink = { props: ["to"], template: '<a :data-to="JSON.stringify(to)"><slot /></a>' };

async function mountView(query: Record<string, string> = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/metadata-memory",
        name: "metadatamemory",
        component: { template: "<div />" },
      },
    ],
  });
  await router.push({ name: "metadatamemory", query });
  await router.isReady();
  const wrapper = mount(MetadataMemoryView, {
    attachTo: document.body,
    global: { plugins: [router], stubs: { RouterLink } },
  });
  return { wrapper, router };
}

describe("Metadata memory page", () => {
  afterEach(() => vi.useRealTimers());
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
    useI18nStore().dictionary = dictionary;
    vi.spyOn(metadataMemoryApi, "list").mockResolvedValue({
      items: [
        {
          id: "mex-1",
          memory_type: "evidence_bound",
          kind: "correction",
          field: "position_holder",
          value: "Levinas",
          rejected_value: "Derrida",
          authority: "human_override",
          review_method: "human_review_of_llm_proposal",
          record_id: "r1",
          record_revision: 4,
          build_id: "build-1",
          source_document_id: "asset-1",
          schema_id: "derrida",
          schema_version: "v1",
          language: "en",
          region_type: "main_text",
          page_start: 12,
          page_end: 12,
          evidence_bound: true,
          evidence_hash: "hash",
          evidence_block_ids: ["b2"],
          evidence_text: "For Levinas, responsibility precedes freedom.",
          context_text: "Context around the evidence.",
          source_current: true,
        },
      ],
      total: 1,
      offset: 0,
      limit: 50,
      summary: { entries: 1, evidence_bound: 1, corrections: 1, fields: 1, backends: 2 },
      facets: {
        fields: ["position_holder"],
        kinds: ["correction"],
        languages: ["en"],
        builds: ["build-1"],
      },
      derived: true,
      authoritative_source: "reviewed corpus metadata and evidence",
      available: true,
      error: "",
    });
  });

  it("presents learned metadata as auditable scholarly memory", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    expect(wrapper.get("#metadata-memory-title").text()).toBe("Metadata memory");
    expect(wrapper.text()).toContain("position_holder");
    expect(wrapper.text()).toContain("Levinas");
    expect(wrapper.text()).toContain("Derrida");
    expect(wrapper.text()).toContain("Correction / negative precedent");
    expect(wrapper.text()).toContain("For Levinas, responsibility precedes freedom.");
    expect(wrapper.text()).toContain("r1 · r4");
    expect(wrapper.text()).not.toContain("derridai_metadata_exemplars");

    wrapper.unmount();
  });

  it("applies select filters immediately, shows removable chips, and debounces search", async () => {
    const list = vi.mocked(metadataMemoryApi.list);
    const { wrapper } = await mountView();
    await flushPromises();
    list.mockClear();

    await wrapper.findAll("select")[0].setValue("position_holder");
    await flushPromises();
    expect(list).toHaveBeenCalledTimes(1);
    expect(list.mock.calls[0][0]).toMatchObject({ field: "position_holder", offset: 0 });
    expect(wrapper.find(".filter-chips").text()).toContain("position_holder");

    vi.useFakeTimers();
    await wrapper.get("input[type=search]").setValue("levinas");
    expect(list).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(350);
    await flushPromises();
    expect(list).toHaveBeenCalledTimes(2);
    expect(list.mock.calls[1][0]).toMatchObject({ q: "levinas" });
    vi.useRealTimers();

    await wrapper.findAll(".chip")[1].trigger("click");
    await flushPromises();
    expect(list.mock.calls.at(-1)?.[0]).toMatchObject({ q: "levinas", field: "" });
    wrapper.unmount();
  });

  it("restores filters from the URL and keeps filter state shareable", async () => {
    const { wrapper, router } = await mountView({
      q: "levinas",
      field: "position_holder",
      kind: "correction",
      build: "build-1",
      language: "en",
      offset: "50",
    });
    await flushPromises();

    expect(wrapper.get("input[type=search]").element.value).toBe("levinas");
    expect(wrapper.findAll("select")[0].element.value).toBe("position_holder");
    expect(metadataMemoryApi.list).toHaveBeenCalledWith(
      expect.objectContaining({
        q: "levinas",
        field: "position_holder",
        kind: "correction",
        build_id: "build-1",
        language: "en",
        offset: 50,
      }),
    );

    await wrapper.findAll("select")[0].setValue("");
    await flushPromises();
    expect(router.currentRoute.value.query.field).toBeUndefined();
    expect(router.currentRoute.value.query.q).toBe("levinas");

    wrapper.unmount();
  });

  it("links the related System Data surfaces and reveals details on demand", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    const targets = wrapper.findAll(".memory-relations a").map((a) => a.attributes("data-to"));
    expect(targets.join()).toContain("semantic_memory_outbox");
    expect(targets.join()).toContain("system-data-metadata");

    expect(wrapper.text()).not.toContain("Context around the evidence.");
    await wrapper.get(".details-toggle").trigger("click");
    expect(wrapper.text()).toContain("Context around the evidence.");
    expect(wrapper.get(".details-toggle").attributes("aria-expanded")).toBe("true");
    wrapper.unmount();
  });
});
