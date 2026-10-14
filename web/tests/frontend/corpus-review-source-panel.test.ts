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
import { describe, expect, it } from "vitest";
import type { CorpusRecord, SourceBlock } from "../../src/api/corpus";
import CorpusBoundaryAdjudication from "../../src/components/CorpusBoundaryAdjudication.vue";
import CorpusSourceSummary from "../../src/components/CorpusSourceSummary.vue";
import CorpusReviewSourcePanel from "../../src/components/corpus-builder/CorpusReviewSourcePanel.vue";

const record: CorpusRecord = {
  record_id: "record-1",
  text: "Reviewed source text.",
  text_length: 21,
  source_block_ids: ["block-1", "block-2"],
  source_spans: [],
  source_extracted_text: "Original extracted source text.",
};

const blocks: SourceBlock[] = [
  {
    block_id: "block-1",
    page: 12,
    bbox: [],
    type: "paragraph",
    text: "First source block.",
    extraction_method: "pdf_text",
    confidence: 0.99,
  },
  {
    block_id: "block-2",
    page: 12,
    bbox: [],
    type: "paragraph",
    text: "Second source block.",
    extraction_method: "pdf_text",
    confidence: 0.98,
  },
];

function mountPanel(overrides: Record<string, unknown> = {}) {
  return mount(CorpusReviewSourcePanel, {
    props: {
      record,
      workspaceMode: "record",
      mediaKind: "pdf",
      audioUrl: "",
      imageUrl: "",
      showPdfExplorer: true,
      pdfUrl: "",
      page: 12,
      pageCount: 20,
      pageWidth: 612,
      pageHeight: 792,
      pageBlocks: blocks,
      visibleBlocks: blocks,
      evidenceIds: ["block-1"],
      evidenceBlockIds: new Set(["block-1"]),
      selectedEvidenceField: "speaker",
      paginatedSource: true,
      canPreviousSourcePage: true,
      canNextSourcePage: true,
      canMergePrevious: true,
      canMergeNext: true,
      profiles: [
        {
          id: "local",
          name: "Local Ollama",
          type: "ollama",
          model: "gemma4:e2b",
          max_concurrent_requests: 1,
        },
      ],
      providerProfileId: "local",
      modelOverride: "",
      activeRequests: 1,
      disabled: false,
      ...overrides,
    },
  });
}

describe("Corpus Builder review source panel", () => {
  it("owns the source tabpanel semantics", () => {
    const wrapper = mountPanel();
    const panel = wrapper.get("#review-panel-source");

    expect(panel.attributes("role")).toBe("tabpanel");
    expect(panel.attributes("aria-labelledby")).toBe("review-tab-source");
  });

  it("forwards source navigation and viewer actions", () => {
    const wrapper = mountPanel();
    const summary = wrapper.findComponent(CorpusSourceSummary);

    summary.vm.$emit("previous");
    summary.vm.$emit("next");
    summary.vm.$emit("openViewer");
    summary.vm.$emit("openPdfExplorer");

    expect(wrapper.emitted("previousSourcePage")).toHaveLength(1);
    expect(wrapper.emitted("nextSourcePage")).toHaveLength(1);
    expect(wrapper.emitted("openViewer")).toHaveLength(1);
    expect(wrapper.emitted("openPdfExplorer")).toHaveLength(1);
  });

  it("forwards boundary provider and adjudication actions", () => {
    const wrapper = mountPanel();
    const adjudication = wrapper.findComponent(CorpusBoundaryAdjudication);

    expect(adjudication.props("concurrencyRisk")).toBe(true);
    expect(adjudication.props("concurrencyLimit")).toBe(1);

    adjudication.vm.$emit("update:providerProfileId", "remote");
    adjudication.vm.$emit("update:modelOverride", "review-model");
    adjudication.vm.$emit("adjudicate", "next", "local", "review-model");

    expect(wrapper.emitted("update:providerProfileId")?.at(-1)).toEqual(["remote"]);
    expect(wrapper.emitted("update:modelOverride")?.at(-1)).toEqual(["review-model"]);
    expect(wrapper.emitted("adjudicate")?.at(-1)).toEqual(["next", "local", "review-model"]);
  });

  it("forwards evidence and split mutations without owning them", async () => {
    const wrapper = mountPanel();
    const evidenceToggle = wrapper.get(".evidence-toggle");
    const splitButton = wrapper.get(".split-button");

    expect(evidenceToggle.attributes("aria-pressed")).toBe("true");
    await evidenceToggle.trigger("click");
    await splitButton.trigger("click");

    expect(wrapper.emitted("toggleEvidence")?.at(-1)).toEqual(["block-1"]);
    expect(wrapper.emitted("split")?.at(-1)).toEqual(["block-1"]);
  });

  it("disables mutation controls while busy", () => {
    const wrapper = mountPanel({ disabled: true });

    expect(wrapper.get(".evidence-toggle").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".split-button").attributes("disabled")).toBeDefined();
  });
});
