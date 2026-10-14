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
import CorpusTextCleanupSummary from "./CorpusTextCleanupSummary.vue";
const meta = {
  title: "Corpus Builder/Review/Text Cleanup Summary",
  component: CorpusTextCleanupSummary,
  args: {
    summary: {
      enabled: true,
      records_changed: 31,
      changes: 74,
      removed_lines: 42,
      recurring_line_patterns: 5,
      rules: ["page_numbers", "repeated_short_lines", "paragraph_lines", "ocr_artifacts"],
    },
  },
} satisfies Meta<typeof CorpusTextCleanupSummary>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Applied: Story = {};
export const NoChanges: Story = {
  args: {
    summary: {
      enabled: true,
      records_changed: 0,
      changes: 0,
      removed_lines: 0,
      recurring_line_patterns: 0,
    },
  },
};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
