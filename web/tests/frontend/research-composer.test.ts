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
import { beforeEach, describe, expect, it } from "vitest";
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
});
