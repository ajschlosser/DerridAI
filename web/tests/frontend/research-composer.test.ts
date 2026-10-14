/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ResearchComposer from "../../src/components/research/ResearchComposer.vue";

const base = {
  prompt: "What is the gift?",
  instructions: "",
  sourceCollection: "derrida",
  providerProfileId: "p1",
  responseLanguage: "auto",
  preset: "precision",
  evidenceCount: 2,
  stores: [{ name: "derrida", count: 10 }],
  profiles: [{ id: "p1", name: "Scholarly", type: "ollama" }],
  history: [],
  canRun: true,
};

function composer(props: Record<string, unknown> = {}) {
  return mount(ResearchComposer, { props: { ...base, ...props } as never });
}

describe("ResearchComposer", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("collapses to the question, a context summary and run while a run is open", () => {
    const wrapper = composer({ compact: true });
    expect(wrapper.find(".research-composer-compact").exists()).toBe(true);
    expect(wrapper.find(".research-compose-context").exists()).toBe(false);
    expect(wrapper.find<HTMLTextAreaElement>("#researchQuestion").element.value).toBe(
      "What is the gift?",
    );
    const context = wrapper.find(".research-compact-context").text();
    expect(context).toContain("derrida");
    expect(context).toContain("Scholarly");
    expect(context).toContain("High precision");
  });

  it("asks to expand from the compact state", async () => {
    const wrapper = composer({ compact: true });
    await wrapper.find(".research-compact-actions .btn:not(.primary)").trigger("click");
    expect(wrapper.emitted("expand")).toHaveLength(1);
  });

  it("runs on Ctrl+Enter or Cmd+Enter only when running is allowed", async () => {
    for (const compact of [true, false]) {
      const wrapper = composer({ compact });
      await wrapper.find("#researchQuestion").trigger("keydown", { key: "Enter", ctrlKey: true });
      await wrapper.find("#researchQuestion").trigger("keydown", { key: "Enter", metaKey: true });
      await wrapper.find("#researchQuestion").trigger("keydown", { key: "Enter" });
      expect(wrapper.emitted("run")).toHaveLength(2);
    }
    const blocked = composer({ canRun: false });
    await blocked.find("#researchQuestion").trigger("keydown", { key: "Enter", ctrlKey: true });
    expect(blocked.emitted("run")).toBeUndefined();
  });
});
