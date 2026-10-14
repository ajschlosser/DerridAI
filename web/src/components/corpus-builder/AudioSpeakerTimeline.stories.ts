/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import AudioSpeakerTimeline from "./AudioSpeakerTimeline.vue";

const meta = {
  title: "Corpus Builder/Setup/Audio Speaker Timeline",
  component: AudioSpeakerTimeline,
  args: {
    duration: 32,
    voiceAssignments: {
      SPEAKER_1: "Jacques Derrida",
      SPEAKER_2: "Interviewer",
    },
    blocks: [
      {
        block_id: "audio-1",
        page: 1,
        bbox: [],
        type: "paragraph",
        text: "The first timed statement.",
        extraction_method: "whisper+word-speaker-alignment",
        confidence: 0.94,
        start: 0,
        end: 11,
        speaker: "SPEAKER_1",
        speaker_assignment: {
          method: "word_overlap",
          confidence: 0.97,
          ambiguous_word_count: 0,
          word_count: 4,
          review_recommended: false,
        },
      },
      {
        block_id: "audio-2",
        page: 1,
        bbox: [],
        type: "paragraph",
        text: "A question crosses a close speaker transition.",
        extraction_method: "whisper+word-speaker-alignment",
        confidence: 0.86,
        start: 12,
        end: 19,
        speaker: "SPEAKER_2",
        speaker_assignment: {
          method: "word_overlap",
          confidence: 0.58,
          ambiguous_word_count: 1,
          word_count: 7,
          review_recommended: true,
        },
      },
      {
        block_id: "audio-3",
        page: 1,
        bbox: [],
        type: "paragraph",
        text: "The first speaker responds.",
        extraction_method: "whisper+word-speaker-alignment",
        confidence: 0.92,
        start: 20,
        end: 30,
        speaker: "SPEAKER_1",
        speaker_assignment: {
          method: "word_overlap",
          confidence: 0.95,
          ambiguous_word_count: 0,
          word_count: 4,
          review_recommended: false,
        },
      },
    ],
  },
} satisfies Meta<typeof AudioSpeakerTimeline>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ReviewedVoices: Story = {};

export const MachineLabels: Story = {
  args: {
    voiceAssignments: {},
  },
};
