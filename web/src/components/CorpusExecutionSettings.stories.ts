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
import CorpusExecutionSettings from "./CorpusExecutionSettings.vue";
const meta = {
  title: "Corpus Builder/Settings/Execution",
  component: CorpusExecutionSettings,
  args: {
    generation: {
      num_ctx: 32768,
      temperature: 0,
      top_k: 0,
      top_p: 1,
      repeat_penalty: 1.1,
      think: "false",
    },
    stageLimits: {
      manifest_num_predict: 1800,
      segmentation_num_predict: 1200,
      reconciliation_num_predict: 1000,
      discourse_num_predict: 1600,
      quotation_num_predict: 1500,
      indexing_num_predict: 1200,
      segmentation_window_tokens: 5000,
    },
    stageTimeouts: {
      manifest: 300,
      segmentation: 300,
      reconciliation: 240,
      discourse: 240,
      quotation: 240,
      indexing: 180,
    },
    maxConcurrentRequests: 2,
    useProfileDefaults: false,
  },
} satisfies Meta<typeof CorpusExecutionSettings>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Overrides: Story = {};
export const ProfileDefaults: Story = { args: { useProfileDefaults: true } };
export const UnsafeContext: Story = {
  args: {
    generation: { num_ctx: 4096 },
    stageLimits: { segmentation_window_tokens: 5000, segmentation_num_predict: 1200 },
  },
};

export const TightMetadataDeadlines: Story = {
  args: {
    stageTimeouts: {
      manifest: 300,
      segmentation: 300,
      reconciliation: 240,
      discourse: 120,
      quotation: 120,
      indexing: 90,
    },
  },
};
