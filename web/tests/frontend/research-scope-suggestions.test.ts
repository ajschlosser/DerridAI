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

import { researchFiltersApi } from "../../src/api/researchFilters";
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
    expect(wrapper.find(".research-scope-proposals button").exists()).toBe(false);
    expect(wrapper.find(".research-scope-unresolved").exists()).toBe(true);
  });
});

describe("optional model suggestions", () => {
  it("calls only on demand and labels the confirmed filter as model assisted", async () => {
    const resolveModel = vi.fn().mockResolvedValue({
      source: "model_assisted",
      model: "local",
      expression: 'custom_role = "witness"',
      unresolved: [],
    });
    const wrapper = mount(ResearchScopeSuggestions, {
      props: {
        instructions: "Only relevant witness passages",
        filterExpression: "",
        collection: "corpus",
        fields: [],
        inventoryData: {
          works: [],
          truncated: false,
          fields: [{ key: "custom_role", type: "string", values: ["witness"] }],
        },
        resolveModel,
        debounceMs: 1,
      },
    });
    await settle();
    expect(resolveModel).not.toHaveBeenCalled();
    const button = wrapper.findAll("button").find((item) => item.text().includes("Ollama"))!;
    await button.trigger("click");
    await settle();
    expect(resolveModel).toHaveBeenCalledTimes(1);
    expect(wrapper.emitted("update:filterExpression")).toBeUndefined();
    await wrapper
      .findAll("button")
      .find((item) => item.text() === "Add to filter")!
      .trigger("click");
    expect(wrapper.emitted("accepted")?.[0]).toEqual(["model_assisted"]);
  });
  it("rejects a late model result after collection identity changes", async () => {
    let complete!: (value: {
      source: "model_assisted";
      model: string;
      expression: string;
      unresolved: string[];
    }) => void;
    const resolveModel = vi.fn(
      () =>
        new Promise<Awaited<ReturnType<typeof researchFiltersApi.resolve>>>((resolve) => {
          complete = resolve;
        }),
    );
    const wrapper = mount(ResearchScopeSuggestions, {
      props: {
        instructions: "Only unknown scope",
        filterExpression: "",
        collection: "A",
        fields: [],
        inventoryData: {
          works: [],
          truncated: false,
          fields: [{ key: "role", values: ["witness"] }],
        },
        resolveModel,
      },
    });
    await settle();
    await wrapper
      .findAll("button")
      .find((item) => item.text().includes("Ollama"))!
      .trigger("click");
    await wrapper.setProps({ collection: "B" });
    complete({
      source: "model_assisted",
      model: "old",
      expression: 'role = "witness"',
      unresolved: [],
    });
    await settle();
    expect(wrapper.text()).not.toContain('role = "witness"');
  });
});
