/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

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

describe("Metadata memory page", () => {
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
    const wrapper = mount(MetadataMemoryView, { attachTo: document.body });
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
});
