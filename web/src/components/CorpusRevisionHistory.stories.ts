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
import CorpusRevisionHistory from "./CorpusRevisionHistory.vue";
const meta = {
  title: "Corpus Builder/Review/Revision History",
  component: CorpusRevisionHistory,
  args: {
    record: {
      record_id: "r-12",
      text: "Reviewed text",
      text_length: 13,
      source_block_ids: ["b1"],
      source_spans: [{ block_id: "b1", page: 4 }],
      text_revision_history: [
        {
          at: "2026-09-18T10:00:00Z",
          source: "automatic_cleanup",
          previous_length: 92,
          text_length: 83,
          diff: "...",
        },
        {
          at: "2026-09-18T10:04:00Z",
          source: "human",
          previous_length: 83,
          text_length: 86,
          diff: "...",
        },
      ],
      metadata_decisions: [
        { field: "discourse_role", value: "analysis", at: "2026-09-18T10:05:00Z", source: "human" },
      ],
    },
  },
} satisfies Meta<typeof CorpusRevisionHistory>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
