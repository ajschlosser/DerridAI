// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({ previewUnitPolicy: vi.fn() }));
vi.mock("../../src/api/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/api/corpus")>()),
  corpusBuilderApi,
}));

import CorpusRecordSizeAdvice from "../../src/components/CorpusRecordSizeAdvice.vue";

const asset = (over: Record<string, unknown> = {}) =>
  ({
    asset_id: "a1",
    sha256: "abc",
    filename: "essay.txt",
    created_at: "2026-09-23T08:00:00Z",
    page_count: 1,
    block_count: 6,
    ocr_pages: 0,
    warnings: [],
    metadata: {},
    media_kind: "text",
    ...over,
  }) as never;
const sizing = (preferred = 100) => ({
  preferred_record_chars: preferred,
  record_length_tolerance: 10,
  long_record_chars: preferred + 50,
  absolute_record_chars: preferred + 100,
});
const stats = (median: number, max = median * 2) => ({
  policy: { mode: "default" },
  unit_count: 6,
  source_block_count: 6,
  median_chars: median,
  max_chars: max,
  min_chars: 10,
  sample: [],
});

describe("CorpusRecordSizeAdvice", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("with Automatic units, says nothing: the build divides paragraphs that are too long itself", async () => {
    corpusBuilderApi.previewUnitPolicy.mockResolvedValue(stats(564, 2047));
    const wrapper = mount(CorpusRecordSizeAdvice, { props: { asset: asset(), sizing: sizing() } });
    await flushPromises();
    expect(wrapper.find(".size-advice").exists()).toBe(false);
  });

  it("warns when explicitly chosen units are far larger than the requested record length and offers the fix", async () => {
    corpusBuilderApi.previewUnitPolicy.mockResolvedValue(stats(564, 2047));
    const wrapper = mount(CorpusRecordSizeAdvice, {
      props: { asset: asset({ unit_policy: { mode: "paragraph" } }), sizing: sizing() },
    });
    await flushPromises();
    expect(wrapper.get(".size-advice").text()).toContain("564");
    expect(wrapper.get(".size-advice").text()).toContain("2,047");
    expect(corpusBuilderApi.previewUnitPolicy).toHaveBeenCalledWith("a1", { mode: "default" });
    const [sentences, chars] = wrapper.findAll("button");
    await sentences.trigger("click");
    await chars.trigger("click");
    expect(wrapper.emitted("apply")).toEqual([
      [{ mode: "sentence" }],
      [{ mode: "chars", chars: 100 }],
    ]);
  });

  it("stays quiet when the units already fit the requested length", async () => {
    corpusBuilderApi.previewUnitPolicy.mockResolvedValue(stats(96));
    const wrapper = mount(CorpusRecordSizeAdvice, { props: { asset: asset(), sizing: sizing() } });
    await flushPromises();
    expect(wrapper.find(".size-advice").exists()).toBe(false);
  });

  it("does not suggest what is already applied", async () => {
    corpusBuilderApi.previewUnitPolicy.mockResolvedValue(stats(300));
    const wrapper = mount(CorpusRecordSizeAdvice, {
      props: { asset: asset({ unit_policy: { mode: "sentence" } }), sizing: sizing() },
    });
    await flushPromises();
    const labels = wrapper.findAll("button").map((b) => b.text());
    expect(labels.some((text) => /sentences/i.test(text))).toBe(false);
    expect(labels.some((text) => /every 100 characters/i.test(text))).toBe(true);
  });

  it("stays quiet if the preview cannot be loaded", async () => {
    corpusBuilderApi.previewUnitPolicy.mockRejectedValue(new Error("nope"));
    const wrapper = mount(CorpusRecordSizeAdvice, { props: { asset: asset(), sizing: sizing() } });
    await flushPromises();
    expect(wrapper.find(".size-advice").exists()).toBe(false);
  });
});
