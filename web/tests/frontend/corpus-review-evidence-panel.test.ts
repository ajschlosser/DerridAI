/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { CorpusRecord, SourceBlock } from "../../src/api/corpus";
import FieldEvidenceList from "../../src/components/FieldEvidenceList.vue";
import CorpusReviewEvidencePanel from "../../src/components/corpus-builder/CorpusReviewEvidencePanel.vue";

const record: CorpusRecord = {
  record_id: "record-1",
  text: "Evidence-bearing text.",
  text_length: 22,
  source_block_ids: ["block-1"],
  source_spans: [],
  metadata_evidence: {
    speaker: {
      block_ids: ["block-1"],
      confidence: 0.9,
      reason: "Named in the passage.",
    },
  },
};

const blocks: SourceBlock[] = [
  {
    block_id: "block-1",
    page: 12,
    bbox: [],
    type: "paragraph",
    text: "Derrida writes that...",
    extraction_method: "pdf_text",
    confidence: 0.99,
  },
];

function mountPanel(overrides: Record<string, unknown> = {}) {
  return mount(CorpusReviewEvidencePanel, {
    props: {
      record,
      fields: ["speaker", "position_holder"],
      selectedField: "speaker",
      blocks,
      evidenceBlockIds: new Set(["block-1"]),
      paginatedSource: true,
      disabled: false,
      ...overrides,
    },
  });
}

describe("Corpus Builder review evidence panel", () => {
  it("owns evidence tabpanel semantics and field presentation", () => {
    const wrapper = mountPanel();
    const panel = wrapper.get("#review-panel-evidence");

    expect(panel.attributes("role")).toBe("tabpanel");
    expect(panel.attributes("aria-labelledby")).toBe("review-tab-evidence");
    expect(wrapper.findComponent(FieldEvidenceList).exists()).toBe(true);
  });

  it("forwards selected evidence field changes to the parent", () => {
    const wrapper = mountPanel();

    wrapper.findComponent(FieldEvidenceList).vm.$emit("select", "position_holder");

    expect(wrapper.emitted("update:selectedField")?.at(-1)).toEqual(["position_holder"]);
  });

  it("forwards evidence-block toggles without owning the mutation", async () => {
    const wrapper = mountPanel();

    const toggle = wrapper.get(".evidence-toggle");
    expect(toggle.attributes("aria-pressed")).toBe("true");

    await toggle.trigger("click");

    expect(wrapper.emitted("toggleEvidence")?.at(-1)).toEqual(["block-1"]);
  });

  it("uses page locators for paginated sources", () => {
    const wrapper = mountPanel();

    expect(wrapper.get(".source-block header").text()).toContain("12");
  });

  it("disables evidence mutation controls while busy", () => {
    const wrapper = mountPanel({ disabled: true });

    expect(wrapper.get(".evidence-toggle").attributes("disabled")).toBeDefined();
  });
});
