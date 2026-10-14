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
import CorpusBulkMetadataEditor from "./CorpusBulkMetadataEditor.vue";
const meta: Meta<typeof CorpusBulkMetadataEditor> = {
  title: "Corpus Builder/Review/Bulk Metadata Editor",
  component: CorpusBulkMetadataEditor,
  args: {
    selectedCount: 4,
    totalCount: 76,
    disabled: false,
    regionTypes: ["front_matter", "main_text", "notes", "back_matter"],
    discourseRoles: ["assertion", "analysis", "quotation", "paratext"],
    knownValues: {
      speaker: ["Derrida", "Simon Critchley"],
      topics: ["hospitality", "forgiveness", "cosmopolitanism"],
    },
  },
};
export default meta;
type Story = StoryObj<typeof CorpusBulkMetadataEditor>;
export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };
