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

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import AudioSpeakerAssignments from "./AudioSpeakerAssignments.vue";

const meta = {
  title: "Corpus Builder/Setup/Audio Speaker Assignments",
  component: AudioSpeakerAssignments,
  args: {
    speakers: ["SPEAKER_1", "SPEAKER_2"],
    assignments: {
      SPEAKER_1: "Jacques Derrida",
      SPEAKER_2: "",
    },
    disabled: false,
  },
} satisfies Meta<typeof AudioSpeakerAssignments>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DetectedSpeakers: Story = {};

export const NamedSpeakers: Story = {
  args: {
    assignments: {
      SPEAKER_1: "Jacques Derrida",
      SPEAKER_2: "Interviewer",
    },
  },
};

export const Saving: Story = {
  args: {
    disabled: true,
  },
};
