// Copyright 2026 Aaron John Schlosser, PhD.
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({ recordContext: vi.fn() }));
vi.mock("../../src/api/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/api/corpus")>()),
  corpusBuilderApi,
}));

import RecordContextReader from "../../src/components/corpus-builder/RecordContextReader.vue";

const item = (id: string, text: string, page: number | null = 3) => ({
  record_id: id,
  text,
  text_length: text.length,
  page_start: page,
  page_end: page,
});

function mountReader(props: Record<string, unknown> = {}) {
  return mount(RecordContextReader, {
    props: { buildId: "b1", recordId: "r3", text: "Focus text.", ...props },
  });
}

describe("RecordContextReader", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    corpusBuilderApi.recordContext.mockResolvedValue({
      record_id: "r3",
      before: [item("r1", "Far before."), item("r2", "Near before.")],
      after: [item("r4", "Near after."), item("r5", "Far after.", null)],
      truncated: false,
    });
  });

  it("shows the focus record between its neighbours in document order", async () => {
    const wrapper = mountReader();
    await flushPromises();
    const texts = wrapper.findAll(".ctx-item p, .ctx-focus").map((node) => node.text());
    expect(texts).toEqual([
      "Far before.",
      "Near before.",
      "Focus text.",
      "Near after.",
      "Far after.",
    ]);
    expect(corpusBuilderApi.recordContext).toHaveBeenCalledWith("b1", "r3");
  });

  it("fades neighbours with distance and keeps the focus at full strength", async () => {
    const wrapper = mountReader();
    await flushPromises();
    const [far, near] = wrapper.findAll(".ctx-item");
    expect(Number(near.attributes("style")?.match(/opacity: ([\d.]+)/)?.[1])).toBeGreaterThan(
      Number(far.attributes("style")?.match(/opacity: ([\d.]+)/)?.[1]),
    );
    expect(wrapper.get(".ctx-focus").attributes("style")).toBeUndefined();
  });

  it("jumps to a neighbouring record", async () => {
    const wrapper = mountReader();
    await flushPromises();
    await wrapper.findAll(".ctx-jump")[1].trigger("click");
    expect(wrapper.emitted("select")?.[0]).toEqual(["r2"]);
  });

  it("does not fetch when surrounding records are switched off", async () => {
    const wrapper = mountReader({ showContext: false });
    await flushPromises();
    expect(corpusBuilderApi.recordContext).not.toHaveBeenCalled();
    expect(wrapper.find(".ctx-item").exists()).toBe(false);
    expect(wrapper.get(".ctx-focus").text()).toBe("Focus text.");
  });

  it("keeps the record readable and says so when context cannot be loaded", async () => {
    corpusBuilderApi.recordContext.mockRejectedValueOnce(new Error("boom"));
    const wrapper = mountReader();
    await flushPromises();
    expect(wrapper.get(".ctx-focus").text()).toBe("Focus text.");
    expect(wrapper.get(".ctx-note").attributes("role")).toBe("status");
  });

  it("caches a record's context and refetches for another record", async () => {
    const wrapper = mountReader();
    await flushPromises();
    await wrapper.setProps({ recordId: "r4", text: "Other." });
    await flushPromises();
    expect(corpusBuilderApi.recordContext).toHaveBeenCalledTimes(2);
    await wrapper.setProps({ recordId: "r3", text: "Focus text." });
    await flushPromises();
    expect(corpusBuilderApi.recordContext).toHaveBeenCalledTimes(2);
  });

  it("still shows the record when the context response has no neighbour lists", async () => {
    corpusBuilderApi.recordContext.mockResolvedValue({ record_id: "r3" });
    const wrapper = mountReader();
    await flushPromises();
    expect(wrapper.find(".ctx-focus").text()).toBe("Focus text.");
    expect(wrapper.findAll(".ctx-item")).toHaveLength(0);
  });
});
