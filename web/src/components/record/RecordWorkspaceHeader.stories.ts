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
import RecordWorkspaceHeader from "./RecordWorkspaceHeader.vue";
const meta = {
  title: "Record Workspace/Workspace Header",
  component: RecordWorkspaceHeader,
  args: {
    work: "Adieu to Emmanuel Levinas",
    author: "Jacques Derrida",
    year: 1999,
    pages: "pp. 20–21",
    recordId: "adieu-00042",
    position: "42 of 318",
    evidenceSelected: true,
    canEdit: true,
    canEvidence: true,
    canReview: true,
    canUpsert: true,
    canLlm: true,
    canHistory: true,
    canPdf: true,
    hasHistory: true,
    hasPrevious: true,
    hasNext: true,
  },
} satisfies Meta<typeof RecordWorkspaceHeader>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const ReadOnlyResearcher: Story = {
  args: {
    canEdit: false,
    canReview: false,
    canUpsert: false,
    canLlm: false,
    canHistory: false,
    canPdf: false,
    evidenceSelected: false,
  },
};

export const LongWorkTitle: Story = {
  args: {
    work: "The Beast and the Sovereign, Volume II: Seminar of Jacques Derrida, 2002–2003 — Session on Robinson Crusoe, sovereignty, and the living",
    pages: "pp. 247–263",
  },
};
