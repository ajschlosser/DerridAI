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
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import ResearchScopeSuggestions from "../../src/components/research/ResearchScopeSuggestions.vue";

const inventory = {
  works: [{ work: "Of Grammatology", authors: ["Jacques Derrida"] }],
  truncated: false,
};

async function settle() {
  await vi.advanceTimersByTimeAsync(10);
  await nextTick();
}

describe("ResearchScopeSuggestions", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  it("proposes a confirmed-only filter and never edits the expression on its own", async () => {
    const loadInventory = vi.fn().mockResolvedValue(inventory);
    const wrapper = mount(ResearchScopeSuggestions, {
      props: {
        instructions: "Only use Of Grammatology.",
        filterExpression: "",
        collection: "corpus",
        fields: ["work"],
        debounceMs: 1,
        loadInventory,
      },
    });
    await settle();
    expect(loadInventory).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain('work = "Of Grammatology"');
    expect(wrapper.emitted("update:filterExpression")).toBeUndefined();

    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("update:filterExpression")![0]).toEqual(['work = "Of Grammatology"']);
    expect(wrapper.emitted("accepted")).toHaveLength(1);
  });

  it("does not fetch the inventory or render without instructions", async () => {
    const loadInventory = vi.fn().mockResolvedValue(inventory);
    const wrapper = mount(ResearchScopeSuggestions, {
      props: {
        instructions: "",
        filterExpression: "",
        collection: "corpus",
        fields: ["work"],
        debounceMs: 1,
        loadInventory,
      },
    });
    await settle();
    expect(loadInventory).not.toHaveBeenCalled();
    expect(wrapper.find("section").exists()).toBe(false);
  });

  it("keeps emphasis visible as an instruction instead of a filter", async () => {
    const wrapper = mount(ResearchScopeSuggestions, {
      props: {
        instructions: "Focus especially on Derrida's early works.",
        filterExpression: "",
        collection: "corpus",
        fields: ["work"],
        debounceMs: 1,
        loadInventory: vi.fn().mockResolvedValue(inventory),
      },
    });
    await settle();
    expect(wrapper.find("button").exists()).toBe(false);
    expect(wrapper.find(".research-scope-unresolved").exists()).toBe(true);
  });
});
