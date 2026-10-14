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

const timing = vi.hoisted(() => ({ measure: vi.fn() }));
vi.mock("../../src/domain/interactionTiming", () => ({
  measureInteractionToNextFrame: timing.measure,
}));

import ResearchComposer from "../../src/components/research/ResearchComposer.vue";
import { useI18nStore } from "../../src/stores/i18n";

const baseProps = {
  prompt: "",
  instructions: "",
  sourceCollection: "derrida_primary",
  providerProfileId: "phi4",
  responseLanguage: "auto",
  preset: "balanced",
  evidenceCount: 0,
  promptMetadata: {
    evidence: ["speaker", "position_holder", "stance", "discourse_role"],
    context: ["quoted_author"],
    record: [],
  },
  stores: [{ name: "derrida_primary", count: 12 }],
  profiles: [{ id: "phi4", name: "Phi-4", type: "ollama" as const, model: "phi4:14b" }],
  history: [],
  canRun: true,
  canConfigure: true,
  canManageRuns: true,
};

describe("ResearchComposer prompt metadata setup", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    useI18nStore().dictionary = {
      "research.prompt_metadata": "Prompt metadata",
      "research.configure_prompt_metadata": "Configure prompt metadata",
      "research.metadata_with_evidence": "Evidence",
      "research.metadata_as_context": "Context",
      "research.metadata_with_record": "Record",
    };
  });

  it("surfaces prompt metadata before a run and opens its configuration directly", async () => {
    const wrapper = mount(ResearchComposer, { props: baseProps });

    const control = wrapper.get(".research-context-action");
    expect(control.text()).toContain("Prompt metadata");
    expect(control.text()).toContain("Evidence 4");
    expect(control.text()).toContain("Context 1");
    expect(control.text()).toContain("Record 0");

    await wrapper.get(".research-context-action-button").trigger("click");
    expect(wrapper.emitted("promptMetadata")).toHaveLength(1);

    wrapper.unmount();
  });
  it("accepts a draft before configuration arrives while run controls remain disabled", async () => {
    const wrapper = mount(ResearchComposer, {
      props: {
        ...baseProps,
        canConfigure: false,
        canDraft: true,
        canRun: false,
        canManageRuns: false,
      },
    });
    await wrapper.get("#researchQuestion").setValue("Early research draft");
    expect(wrapper.emitted("update:prompt")).toEqual([["Early research draft"]]);
    expect(timing.measure).toHaveBeenCalledWith("derridai.research.prompt.input_to_frame");
    expect(wrapper.get(".research-run-button").attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });
});

describe("ResearchComposer follow-up settings", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });
  const summary = (wrapper: ReturnType<typeof mount>) =>
    Object.fromEntries(
      wrapper
        .findAll(".research-composer-effective dt")
        .map((dt) => [
          dt.text(),
          (dt.element.nextElementSibling as HTMLElement).textContent?.trim(),
        ]),
    );

  it("states the effective corpus, profile, preset and context, with full settings on demand", async () => {
    const wrapper = mount(ResearchComposer, {
      props: { ...baseProps, compact: true, filterExpression: 'work == "Glas"' },
    });
    expect(summary(wrapper)).toMatchObject({
      Corpus: "derrida_primary",
      Evidence: "Retrieved from the corpus for this question",
      "Retrieval scope filter": 'work == "Glas"',
    });
    expect(Object.values(summary(wrapper))).toContain("Balanced");
    expect(Object.values(summary(wrapper)).join(" ")).toContain("Phi-4 · phi4:14b");
    expect(wrapper.text()).toContain("they are not evidence");
    expect(wrapper.find("#researchComposerSettings").exists()).toBe(false);
    const toggle = wrapper.get(".research-composer-settings-toggle");
    expect(toggle.attributes("aria-expanded")).toBe("false");
    await toggle.trigger("click");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(wrapper.find("#researchComposerSettings select").exists()).toBe(true);
    wrapper.unmount();
  });

  it("distinguishes selected passages used as evidence from ones the preset ignores", async () => {
    const wrapper = mount(ResearchComposer, {
      props: { ...baseProps, compact: true, evidenceCount: 2, preset: "balanced" },
    });
    const evidence = () => wrapper.get("[data-evidence-mode]");
    expect(evidence().attributes("data-evidence-mode")).toBe("retrieval");
    expect(evidence().text()).toBe("2 selected passages, not used by this retrieval profile");
    await wrapper.setProps({ preset: "hybrid" });
    expect(evidence().attributes("data-evidence-mode")).toBe("used");
    expect(evidence().text()).toBe("2 selected passages, used as evidence");
    wrapper.unmount();
  });

  it("says when no profile is configured and omits the summary for new questions", async () => {
    const wrapper = mount(ResearchComposer, {
      props: { ...baseProps, compact: true, profiles: [], providerProfileId: "" },
    });
    expect(Object.values(summary(wrapper))).toContain("No profile");
    await wrapper.setProps({ sourceCollection: "", stores: [] });
    expect(summary(wrapper).Corpus).toBe("No corpus database available");
    await wrapper.setProps({ compact: false });
    expect(wrapper.find(".research-composer-effective").exists()).toBe(false);
    expect(wrapper.find("#researchComposerSettings").exists()).toBe(true);
    wrapper.unmount();
  });
  it("lists an explicit context scope with per-turn removal and a reset", async () => {
    const wrapper = mount(ResearchComposer, {
      props: {
        ...baseProps,
        compact: true,
        contextScope: [{ turn_id: "t2", ordinal: 2, question: "On the gift" }],
      },
    });
    const scope = wrapper.get(".research-composer-context-scope");
    expect(scope.text()).toContain("Only these earlier turns, as context rather than evidence");
    expect(scope.text()).toContain("Turn 2: On the gift");
    await scope.get("button[aria-label='Remove turn 2 from context']").trigger("click");
    expect(wrapper.emitted("removeContextTurn")).toEqual([["t2"]]);
    await wrapper.setProps({ contextScope: [] });
    expect(wrapper.get(".research-composer-context-scope").text()).toContain(
      "No earlier turns are used as context.",
    );
    await wrapper.get(".research-composer-context-scope > button").trigger("click");
    expect(wrapper.emitted("resetContext")).toHaveLength(1);
    wrapper.unmount();
  });
});
