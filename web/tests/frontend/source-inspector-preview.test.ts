// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SourceInspector from "../../src/components/sources/SourceInspector.vue";
import { corpusSourcesApi, type SourceDetail } from "../../src/api/corpus";

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

describe("SourceInspector extracted-text preview", () => {
  beforeEach(() => setActivePinia(createPinia()));
  afterEach(() => vi.restoreAllMocks());

  it("shows persisted text blocks without rendering source markup", async () => {
    vi.spyOn(corpusSourcesApi, "blocks").mockResolvedValue({
      items: [
        { block_id: "b1", text: "The first paragraph." },
        { block_id: "b2", text: "<script>alert('not rendered')</script>" },
      ],
      total: 2,
      offset: 0,
      limit: 8,
    });

    const wrapper = mount(SourceInspector, { props: { sourceId: "source-1", detail } });
    await flushPromises();

    expect(wrapper.get(".si-preview-text").text()).toContain("The first paragraph.");
    expect(wrapper.find("script").exists()).toBe(false);
    expect(wrapper.get(".si-preview-text").text()).toContain("<script>");
  });

  it.each(["text", "rtf", "docx", "html"])(
    "loads a safe extracted preview for %s sources",
    async (media_kind) => {
      vi.spyOn(corpusSourcesApi, "blocks").mockResolvedValue({
        items: [{ block_id: "b1", text: `Preview for ${media_kind}` }],
        total: 1,
        offset: 0,
        limit: 8,
      });
      const wrapper = mount(SourceInspector, {
        props: { sourceId: "source-1", detail: { ...detail, media_kind } },
      });
      await flushPromises();
      expect(wrapper.get(".si-preview-text").text()).toContain(`Preview for ${media_kind}`);
      expect(corpusSourcesApi.blocks).toHaveBeenCalledWith("asset-1", 0, 8);
    },
  );
});
