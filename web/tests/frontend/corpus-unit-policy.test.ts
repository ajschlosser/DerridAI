// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({ previewUnitPolicy: vi.fn() }));
vi.mock("../../src/api/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/api/corpus")>()),
  corpusBuilderApi,
}));

import CorpusUnitPolicy from "../../src/components/CorpusUnitPolicy.vue";

const asset = {
  asset_id: "a1",
  sha256: "abc",
  filename: "essay.txt",
  created_at: "2026-09-23T08:00:00Z",
  page_count: 1,
  block_count: 3,
  ocr_pages: 0,
  warnings: [],
  metadata: {},
  media_kind: "text",
} as never;

const preview = (count: number) => ({
  policy: { mode: "sentence" },
  unit_count: count,
  source_block_count: 3,
  median_chars: 88,
  max_chars: 240,
  min_chars: 12,
  sample: [{ block_id: "b1-u001", page: 1, text: "First sentence." }],
});

describe("CorpusUnitPolicy", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
    vi.clearAllTimers();
    vi.clearAllMocks();
    corpusBuilderApi.previewUnitPolicy.mockResolvedValue(preview(42));
  });

  it("previews the current choice and offers no apply until something changes", async () => {
    const wrapper = mount(CorpusUnitPolicy, { props: { asset } });
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    expect(corpusBuilderApi.previewUnitPolicy).toHaveBeenCalledWith("a1", { mode: "default" });
    expect(wrapper.get(".btn.primary").attributes("disabled")).toBeDefined();
    expect(wrapper.find(".unit-pending").exists()).toBe(false);
  });

  it("previews a sentence policy and applies it", async () => {
    const wrapper = mount(CorpusUnitPolicy, { props: { asset } });
    await wrapper.get('input[value="sentence"]').setValue(true);
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    expect(corpusBuilderApi.previewUnitPolicy).toHaveBeenLastCalledWith("a1", { mode: "sentence" });
    expect(wrapper.get(".unit-stats").text()).toContain("42");
    expect(wrapper.get(".unit-sample").text()).toContain("First sentence.");
    expect(wrapper.find(".unit-pending").exists()).toBe(true);
    await wrapper.get(".btn.primary").trigger("click");
    expect(wrapper.emitted("apply")?.[0]).toEqual([{ mode: "sentence" }]);
  });

  it("asks for a size in characters and validates it", async () => {
    const wrapper = mount(CorpusUnitPolicy, { props: { asset } });
    await wrapper.get('input[value="chars"]').setValue(true);
    await wrapper.get("#unit-chars-input").setValue("10");
    expect(wrapper.get(".btn.primary").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".unit-chars small").attributes("role")).toBe("alert");
    await wrapper.get(".preset:nth-child(2)").trigger("click");
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    expect(corpusBuilderApi.previewUnitPolicy).toHaveBeenLastCalledWith("a1", {
      mode: "chars",
      chars: 500,
    });
    await wrapper.get(".btn.primary").trigger("click");
    expect(wrapper.emitted("apply")?.[0]).toEqual([{ mode: "chars", chars: 500 }]);
  });

  it("previews from the original when the source is already a derived version", async () => {
    mount(CorpusUnitPolicy, {
      props: {
        asset: {
          ...(asset as object),
          asset_id: "a2",
          derived_from_asset_id: "a1",
          unit_policy: { mode: "line" },
        } as never,
      },
    });
    await vi.advanceTimersByTimeAsync(300);
    expect(corpusBuilderApi.previewUnitPolicy).toHaveBeenCalledWith("a1", { mode: "line" });
  });

  it("locks the choices while a build is using the source", () => {
    const wrapper = mount(CorpusUnitPolicy, { props: { asset, disabled: true } });
    expect(wrapper.get("fieldset").attributes("disabled")).toBeDefined();
  });

  it("shows an error instead of stale numbers when the preview fails", async () => {
    corpusBuilderApi.previewUnitPolicy.mockRejectedValueOnce(new Error("No such asset"));
    const wrapper = mount(CorpusUnitPolicy, { props: { asset } });
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    expect(wrapper.get(".unit-error").text()).toBe("No such asset");
  });
});
