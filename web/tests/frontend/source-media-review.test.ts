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
import CorpusSourceSummary from "../../src/components/CorpusSourceSummary.vue";
import CorpusBuildReadiness from "../../src/components/CorpusBuildReadiness.vue";
const blocks = [
  {
    block_id: "a1",
    page: 1,
    bbox: [],
    type: "paragraph",
    text: "Hello.",
    extraction_method: "whisper",
    confidence: 0.8,
    start: 1,
    end: 3,
    speaker: "S1",
  },
];
describe("media-specific review", () => {
  it("plays audio with timed speaker evidence without PDF navigation", () => {
    const wrapper = mount(CorpusSourceSummary, {
      props: { mediaKind: "audio", audioUrl: "/audio.wav", page: 1, pageCount: 4, blocks },
    });
    expect(wrapper.get("audio").attributes("controls")).toBeDefined();
    expect(wrapper.text()).toContain("00:00:01–00:00:03 S1");
    expect(wrapper.text()).toContain("Hello.");
    expect(wrapper.text()).not.toContain("PDF");
    expect(wrapper.find(".source-page-nav").exists()).toBe(false);
  });
  it("shows text without audio or page controls", () => {
    const wrapper = mount(CorpusSourceSummary, {
      props: { mediaKind: "text", page: 1, pageCount: 4, blocks },
    });
    expect(wrapper.find("audio").exists()).toBe(false);
    expect(wrapper.find(".source-page-nav").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("PDF");
    expect(wrapper.text()).toContain("Hello.");
  });
  it("shows image previews without introducing PDF controls", () => {
    const wrapper = mount(CorpusSourceSummary, {
      props: { mediaKind: "image", imageUrl: "/scan.png", page: 1, pageCount: 1, blocks: [] },
    });
    expect(wrapper.get("img").attributes("src")).toBe("/scan.png");
    expect(wrapper.find(".source-page-nav").exists()).toBe(false);
    expect(wrapper.find("audio").exists()).toBe(false);
  });
  it("omits pagination and layout readiness for audio", () => {
    const wrapper = mount(CorpusBuildReadiness, {
      props: { mediaKind: "audio", sourceFilename: "clip.wav", pageCount: 4, blockCount: 4 },
    });
    expect(wrapper.text()).not.toContain("pages");
    expect(wrapper.text()).not.toContain("Structure");
  });
});

it("hides PDF page-bound fields in an audio manifest", async () => {
  const { default: DocumentManifestEditor } = await import(
    "../../src/components/DocumentManifestEditor.vue"
  );
  const wrapper = mount(DocumentManifestEditor, { props: { mediaKind: "audio", manifest: {} } });
  expect(wrapper.text()).not.toContain("physical PDF page");
  expect(wrapper.text()).toContain("Source-supported notes");
});
