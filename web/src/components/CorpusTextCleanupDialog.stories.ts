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
import CorpusTextCleanupDialog from "./CorpusTextCleanupDialog.vue";
const meta = {
  title: "Corpus Builder/Review/Text Cleanup",
  component: CorpusTextCleanupDialog,
  args: {
    text: "CHAPTER ONE\n12\nThis is philoso-\nphical text.\n\n\nCHAPTER ONE\n13\nMore text.",
    recurringLines: ["CHAPTER ONE"],
  },
} satisfies Meta<typeof CorpusTextCleanupDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
