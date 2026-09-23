// Copyright 2026 Aaron John Schlosser, PhD.
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
