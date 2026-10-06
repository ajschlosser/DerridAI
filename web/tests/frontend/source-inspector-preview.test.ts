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


describe("SourceInspector request identity", () => {
  beforeEach(() => setActivePinia(createPinia()));
  afterEach(() => vi.restoreAllMocks());

  it("withholds the previous source while a new source detail is pending", async () => {
    let resolveSecond!: (value: SourceDetail) => void;
    vi.spyOn(documentReads, "sourceDocumentDetail")
      .mockResolvedValueOnce({ ...detail, asset_id: "asset-a", filename: "A.docx" })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve;
          }),
      );
    vi.spyOn(documentReads, "sourceDocumentPreview").mockResolvedValue([]);

    const wrapper = mount(SourceInspector, { props: { sourceId: "source-a" } });
    await flushPromises();
    expect(wrapper.text()).toContain("A.docx");

    await wrapper.setProps({ sourceId: "source-b" });
    await flushPromises();

    expect(wrapper.text()).not.toContain("A.docx");
    expect(wrapper.find(".ui-loading-state").exists()).toBe(true);

    resolveSecond({ ...detail, asset_id: "asset-b", filename: "B.docx" });
    await flushPromises();
    expect(wrapper.text()).toContain("B.docx");
  });

  it("ignores a late detail response from a superseded source", async () => {
    let resolveFirst!: (value: SourceDetail) => void;
    vi.spyOn(documentReads, "sourceDocumentDetail")
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve;
          }),
      )
      .mockResolvedValueOnce({ ...detail, asset_id: "asset-b", filename: "B.docx" });
    vi.spyOn(documentReads, "sourceDocumentPreview").mockResolvedValue([]);

    const wrapper = mount(SourceInspector, { props: { sourceId: "source-a" } });
    await wrapper.setProps({ sourceId: "source-b" });
    await flushPromises();
    expect(wrapper.text()).toContain("B.docx");

    resolveFirst({ ...detail, asset_id: "asset-a", filename: "A.docx" });
    await flushPromises();

    expect(wrapper.text()).toContain("B.docx");
    expect(wrapper.text()).not.toContain("A.docx");
  });
});
