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
import CorpusJsonlPreviewDialog from "./CorpusJsonlPreviewDialog.vue";
const jsonl =
  '{"record_id":"derrida-test-00012","text":"A reviewed passage.","region_type":"main_text","primary_text":true,"discourse_role":"analysis"}';
const meta = {
  title: "Corpus Builder/Review/JSONL Preview",
  component: CorpusJsonlPreviewDialog,
  args: { open: true, jsonl, validationErrors: [], unresolvedFields: [], wouldPublish: true },
} satisfies Meta<typeof CorpusJsonlPreviewDialog>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Ready: Story = {};
export const Blocked: Story = {
  args: {
    wouldPublish: false,
    validationErrors: ["reported_position requires a position_holder"],
    unresolvedFields: ["position_holder"],
  },
};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
