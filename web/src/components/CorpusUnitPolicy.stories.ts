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
import type { PdfAsset } from "../api/corpus";
import CorpusUnitPolicy from "./CorpusUnitPolicy.vue";

const asset = {
  asset_id: "pdf-essay",
  sha256: "abcdef1234567890abcdef",
  filename: "Of Hospitality.txt",
  created_at: "2026-09-23T08:00:00Z",
  page_count: 4,
  block_count: 42,
  ocr_pages: 0,
  warnings: [],
  metadata: {},
  media_kind: "text",
} as PdfAsset;

// The preview is fetched from the API; without a backend the story shows its error state.
const meta = {
  title: "Corpus Builder/Structure/Unit Policy",
  component: CorpusUnitPolicy,
  args: { asset, disabled: false, busy: false },
} satisfies Meta<typeof CorpusUnitPolicy>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const SentenceApplied: Story = {
  args: { asset: { ...asset, asset_id: "pdf-essay-s", unit_policy: { mode: "sentence" } } },
};
export const LockedDuringBuild: Story = { args: { disabled: true } };
