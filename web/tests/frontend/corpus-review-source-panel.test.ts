// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import type { CorpusRecord, SourceBlock } from "../../src/api/corpus";
import CorpusReviewSourcePanel from "../../src/components/corpus-builder/CorpusReviewSourcePanel.vue";

const blocks: SourceBlock[] = [
  {
    block_id: "b1",
    page: 1,
    type: "paragraph",
    text: "First block.",
    bbox: [0, 0, 1, 1],
    extraction_method: "native",
    confidence: 1,
  },
  {
    block_id: "b2",
    page: 1,
    type: "paragraph",
    text: "Second block.",
    bbox: [0, 0, 1, 1],
    extraction_method: "native",
    confidence: 1,
  },
];

function mountPanel(props: Record<string, unknown> = {}) {
  return mount(CorpusReviewSourcePanel, {
    props: {
      record: {
        record_id: "r1",
        text: "Original extraction.",
        text_length: 20,
        source_block_ids: ["b1"],
        source_spans: [],
        source_extracted_text: "Original extraction.",
      } as CorpusRecord,
      showPdfExplorer: false,
      page: 1,
      pageCount: 1,
      pageWidth: 0,
      pageHeight: 0,
      pageBlocks: [],
      evidenceIds: [],
      zoomable: false,
      canPreviousPage: false,
      canNextPage: false,
      canMergePrevious: true,
      canMergeNext: true,
      profiles: [],
      providerProfileId: "",
      modelOverride: "",
      concurrencyRisk: false,
      activeRequests: 0,
      concurrencyLimit: 1,
      blocks,
      evidenceBlockIds: new Set(["b1"]),
      paginatedSource: true,
      selectedEvidenceField: "speaker",
      busy: false,
      ...props,
    },
    global: {
      stubs: {
        CorpusSourceSummary: true,
        CorpusBoundaryAdjudication: true,
        CorpusRevisionHistory: true,
      },
    },
  });
}

describe("CorpusReviewSourcePanel", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("keeps the tabpanel identity and shows the original extraction", () => {
    const wrapper = mountPanel();
    expect(wrapper.attributes("id")).toBe("review-panel-source");
    expect(wrapper.attributes("aria-labelledby")).toBe("review-tab-source");
    expect(wrapper.find(".original-extraction-snapshot").text()).toBe("Original extraction.");
  });

  it("forwards evidence toggles and splits without mutating anything itself", async () => {
    const wrapper = mountPanel();
    await wrapper.get(".evidence-toggle").trigger("click");
    expect(wrapper.emitted("toggleEvidence")?.[0]).toEqual(["b1"]);
    await wrapper.get(".split-button").trigger("click");
    expect(wrapper.emitted("split")?.[0]).toEqual(["b1"]);
    // No split control after the final block.
    expect(wrapper.findAll(".split-button")).toHaveLength(1);
    expect(wrapper.findAll(".source-block")[0].classes()).toContain("evidence-block");
  });

  it("disables block actions while busy and hides evidence toggles without a field", async () => {
    const busy = mountPanel({ busy: true });
    expect(busy.get(".evidence-toggle").attributes("disabled")).toBeDefined();
    expect(busy.get(".split-button").attributes("disabled")).toBeDefined();
    const none = mountPanel({ selectedEvidenceField: "" });
    expect(none.find(".evidence-toggle").exists()).toBe(false);
  });
});
