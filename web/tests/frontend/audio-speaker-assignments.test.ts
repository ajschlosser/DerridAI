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

import { readFile } from "node:fs/promises";

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { format } from "prettier";
import { beforeEach, describe, expect, it } from "vitest";

import AudioSpeakerAssignments from "../../src/components/corpus-builder/AudioSpeakerAssignments.vue";
import CorpusMetadataConfiguration from "../../src/components/corpus-builder/CorpusMetadataConfiguration.vue";

const schema = {
  id: "default",
  name: "Default",
  description: "",
  builtin: true,
  field_count: 0,
  groups: [],
  hash: "default",
};

describe("audio speaker assignments", () => {
  it("prints the exact Prettier output for the component", async () => {
    const source = await readFile("src/components/corpus-builder/AudioSpeakerAssignments.vue", "utf8");
    const formatted = await format(source, { parser: "vue", printWidth: 100 });
    console.log("\n--- PRETTIER OUTPUT ---\n" + formatted + "--- END PRETTIER OUTPUT ---");
    expect(source).toBe(formatted);
  });

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renames detected speaker IDs and emits the complete assignment map", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const wrapper = mount(AudioSpeakerAssignments, {
      props: {
        speakers: ["SPEAKER_1", "SPEAKER_2"],
        assignments: { SPEAKER_1: "Jacques Derrida", SPEAKER_2: "" },
      },
      global: { plugins: [pinia] },
    });

    const inputs = wrapper.findAll("input");
    expect(inputs).toHaveLength(2);
    expect(inputs[0].element.value).toBe("Jacques Derrida");

    await inputs[1].setValue("Interviewer");
    await inputs[1].trigger("change");

    expect(wrapper.emitted("save")?.at(-1)?.[0]).toEqual({
      SPEAKER_1: "Jacques Derrida",
      SPEAKER_2: "Interviewer",
    });
  });

  it("surfaces the speaker editor in Metadata only for diarized audio", () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const audio = mount(CorpusMetadataConfiguration, {
      props: {
        schemaId: "default",
        runGuidance: {},
        schemaChoices: [schema],
        chosenSchema: schema,
        runGuidanceFields: [],
        mediaKind: "audio",
        speakers: ["SPEAKER_1", "SPEAKER_2"],
        voiceAssignments: {},
      },
      global: { plugins: [pinia] },
    });
    expect(audio.findComponent(AudioSpeakerAssignments).exists()).toBe(true);

    const text = mount(CorpusMetadataConfiguration, {
      props: {
        schemaId: "default",
        runGuidance: {},
        schemaChoices: [schema],
        chosenSchema: schema,
        runGuidanceFields: [],
        mediaKind: "text",
        speakers: ["SPEAKER_1"],
        voiceAssignments: {},
      },
      global: { plugins: [pinia] },
    });
    expect(text.findComponent(AudioSpeakerAssignments).exists()).toBe(false);
  });
});
