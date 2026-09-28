// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SourceInspector from "../../src/components/sources/SourceInspector.vue";
import type { SourceDetail } from "../../src/api/corpus";
import * as documentReads from "../../src/features/sources/api/documentIntelligenceReads";

const detail: SourceDetail = {
  asset_id: "asset-1",
  sha256: "abc123",
  filename: "essay.docx",
  created_at: "2026-09-27T00:00:00Z",
  media_kind: "text",
  catalog_metadata: {},
  initial_metadata: {},
  captures: [],
  builds: [],
};
const block = (block_id: string, text: string) => ({
  block_id,
  text,
  page: 1,
  bbox: [0, 0, 1, 1],
  type: "paragraph",
  extraction_method: "test",
  confidence: 1,
});

describe("SourceInspector extracted-text preview", () => {
  beforeEach(() => setActivePinia(createPinia()));
  afterEach(() => vi.restoreAllMocks());

  it("shows persisted text blocks without rendering source markup", async () => {
    vi.spyOn(documentReads, "sourceDocumentPreview").mockResolvedValue([
      block("b1", "The first paragraph."),
      block("b2", "<script>alert('not rendered')</script>"),
    ]);

    const wrapper = mount(SourceInspector, { props: { sourceId: "source-1", detail } });
    await flushPromises();

    expect(wrapper.get(".si-preview-text").text()).toContain("The first paragraph.");
    expect(wrapper.find("script").exists()).toBe(false);
    expect(wrapper.get(".si-preview-text").text()).toContain("<script>");
  });

  it.each(["text", "rtf", "docx", "html"])(
    "loads a safe extracted preview for %s sources",
    async (media_kind) => {
      vi.spyOn(documentReads, "sourceDocumentPreview").mockResolvedValue([
        block("b1", `Preview for ${media_kind}`),
      ]);
      const wrapper = mount(SourceInspector, {
        props: { sourceId: "source-1", detail: { ...detail, media_kind } },
      });
      await flushPromises();
      expect(wrapper.get(".si-preview-text").text()).toContain(`Preview for ${media_kind}`);
      expect(documentReads.sourceDocumentPreview).toHaveBeenCalledWith("asset-1", 8);
    },
  );
});
