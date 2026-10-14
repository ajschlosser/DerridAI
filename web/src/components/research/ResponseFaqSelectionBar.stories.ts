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
import ResponseFaqSelectionBar from "./ResponseFaqSelectionBar.vue";

const record = {
  record_id: "cache-1",
  question:
    "How does Derrida distinguish unconditional hospitality from the conditional laws of hospitality?",
  provider: "Ollama",
  model: "qwen3:14b",
  created_at: "2026-09-14T18:30:00Z",
  evidence_count: 8,
};
const meta = {
  title: "Research/Response Library/Current Response",
  component: ResponseFaqSelectionBar,
  args: { record, evidenceCount: 8, grade: 9.2 },
} satisfies Meta<typeof ResponseFaqSelectionBar>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const LongQuestion: Story = {
  args: {
    record: {
      ...record,
      question:
        "How does Derrida distinguish the unconditional structure of hospitality from the conditional laws that make hospitality politically and juridically practicable, and what follows from that distinction for the sovereignty of the host?",
    },
    evidenceCount: 14,
    grade: null,
  },
};
