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

  it("uses deterministic neighbour previews and keeps the focus at full strength", async () => {
    const longText = `  ${"A".repeat(150)}  ${"B".repeat(20)}\nwith spacing`;
    corpusBuilderApi.recordContext.mockResolvedValueOnce({
      record_id: "r3",
      before: [item("r1", longText)],
      after: [],
      truncated: false,
    });
    const wrapper = mountReader();
    await flushPromises();
    const preview = wrapper.get(".ctx-item p");
    expect(preview.element.firstChild?.textContent?.trimEnd()).toBe(`${longText.slice(0, 150)}…`);
    await preview.get(".ctx-expand").trigger("click");
    expect(preview.element.firstChild?.textContent?.trim()).toBe(longText.trim());
    expect(preview.get(".ctx-expand").attributes("aria-expanded")).toBe("true");
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

  it("discards an in-flight response when context is switched off", async () => {
    let resolve!: (value: unknown) => void;
    corpusBuilderApi.recordContext.mockReturnValueOnce(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const wrapper = mountReader();
    await wrapper.setProps({ showContext: false });
    resolve({ record_id: "r3", before: [item("r2", "Obsolete.")], after: [] });
    await flushPromises();
    expect(wrapper.find(".ctx-item").exists()).toBe(false);
    expect(wrapper.get(".ctx-focus").text()).toBe("Focus text.");
    wrapper.unmount();
  });

  it("invalidates context when the authoritative text changes", async () => {
    const wrapper = mountReader();
    await flushPromises();
    await wrapper.setProps({ text: "Reviewed text." });
    await flushPromises();
    expect(corpusBuilderApi.recordContext).toHaveBeenCalledTimes(2);
    wrapper.unmount();
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
