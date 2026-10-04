/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026 Aaron John Schlosser, PhD
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import MediaStructureConfigurator from "../../src/components/MediaStructureConfigurator.vue";
import AudioSpeakerAssignments from "../../src/components/corpus-builder/AudioSpeakerAssignments.vue";

describe("audio speaker assignments", () => {
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

  it("surfaces speaker controls in Structure and keeps the no-speaker state visible", () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const audio = mount(MediaStructureConfigurator, {
      props: {
        mediaKind: "audio",
        filename: "seminar.wav",
        blockCount: 12,
        audioProvenance: { duration_seconds: 90, diarization_status: "complete" },
        speakers: ["SPEAKER_1", "SPEAKER_2"],
        voiceAssignments: {},
      },
      global: { plugins: [pinia] },
    });
    expect(audio.findComponent(AudioSpeakerAssignments).exists()).toBe(true);
    expect(audio.findAll("input")).toHaveLength(2);

    const noSpeakers = mount(MediaStructureConfigurator, {
      props: {
        mediaKind: "audio",
        filename: "lecture.wav",
        blockCount: 4,
        audioProvenance: { diarization_status: "no_speakers" },
        speakers: [],
      },
      global: { plugins: [pinia] },
    });
    expect(noSpeakers.findComponent(AudioSpeakerAssignments).exists()).toBe(true);
    expect(noSpeakers.get(".speaker-empty").text()).toContain("timed evidence");

    const text = mount(MediaStructureConfigurator, {
      props: { mediaKind: "text", filename: "notes.txt", blockCount: 3 },
      global: { plugins: [pinia] },
    });
    expect(text.findComponent(AudioSpeakerAssignments).exists()).toBe(false);
  });
});
