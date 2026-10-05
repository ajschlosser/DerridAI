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
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import ResearchFilterEditor from "../../src/components/research/ResearchFilterEditor.vue";
import type { ResearchFilterPreview } from "../../src/api/researchFilters";

const ok: ResearchFilterPreview = {
  valid: true,
  fields_referenced: ["work"],
  collection_filter_fields: ["work", "page_start"],
  unsupported_fields: [],
  errors: [],
  warnings: [],
};

function mountEditor(modelValue: string, preview = vi.fn().mockResolvedValue(ok)) {
  const wrapper = mount(ResearchFilterEditor, {
    props: {
      modelValue,
      collection: "corpus",
      fields: ["work", "page_start"],
      debounceMs: 10,
      preview,
    },
  });
  return { wrapper, preview };
}

async function settle() {
  await vi.advanceTimersByTimeAsync(20);
  await nextTick();
}

describe("ResearchFilterEditor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });
  afterEach(() => vi.useRealTimers());

  it("does not call the server and reports no filter for empty input", async () => {
    const { wrapper, preview } = mountEditor("");
    await settle();
    expect(preview).not.toHaveBeenCalled();
    expect(wrapper.emitted("change")?.at(-1)).toEqual([{ plan: null, valid: true }]);
  });

  it("emits the compiled plan and verifies it with the server", async () => {
    const { wrapper, preview } = mountEditor('work = "A" and page_start >= 3');
    await settle();
    const change = wrapper.emitted("change")?.at(-1)?.[0] as { plan: unknown; valid: boolean };
    expect(change.valid).toBe(true);
    expect(change.plan).toEqual({
      metadata_filter: { $and: [{ work: { $eq: "A" } }, { page_start: { $gte: 3 } }] },
      document_filter: null,
    });
    expect(preview).toHaveBeenCalledTimes(1);
    expect(preview.mock.calls[0][0]).toMatchObject({ collection: "corpus" });
    expect(wrapper.find("[role=status]").text()).toContain("The server accepted this filter");
    expect(wrapper.find("details pre").text()).toContain("$gte");
  });

  it("marks invalid input, exposes aria-invalid, and never calls the server", async () => {
    const { wrapper, preview } = mountEditor("author = 'x'");
    await settle();
    expect(wrapper.find("textarea").attributes("aria-invalid")).toBe("true");
    expect(wrapper.emitted("change")?.at(-1)).toEqual([{ plan: null, valid: false }]);
    expect(wrapper.find("[role=status] li").exists()).toBe(true);
    expect(preview).not.toHaveBeenCalled();
  });

  it("ignores a stale server response after the filter changes", async () => {
    let resolveFirst: (value: ResearchFilterPreview) => void = () => undefined;
    const preview = vi
      .fn()
      .mockImplementationOnce(() => new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce({
        ...ok,
        valid: false,
        errors: [{ code: "unknown_field", params: { field: "work" } }],
      });
    const { wrapper } = mountEditor('work = "A"', preview);
    await vi.advanceTimersByTimeAsync(20);
    await wrapper.setProps({ modelValue: 'work = "B"' });
    await settle();
    resolveFirst(ok);
    await settle();
    const status = wrapper.find("[role=status]").text();
    expect(status).toContain("The server rejected this filter.");
    expect(status).not.toContain("The server accepted this filter");
  });

  it("falls back gracefully when the preview is unavailable", async () => {
    const { wrapper } = mountEditor('work = "A"', vi.fn().mockRejectedValue(new Error("down")));
    await settle();
    expect(wrapper.find("[role=status]").text()).toContain("The server check is unavailable.");
    expect(wrapper.emitted("change")?.at(-1)?.[0]).toMatchObject({ valid: true });
  });

  it("inserts a suggestion by replacing the partial word", async () => {
    const { wrapper } = mountEditor("pa");
    await settle();
    const button = wrapper.findAll(".research-filter-suggestions button")[0];
    expect(button.text()).toBe("page_start");
    await button.trigger("click");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["page_start "]);
  });
});
