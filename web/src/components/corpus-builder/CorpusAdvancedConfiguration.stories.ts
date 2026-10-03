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
import CorpusAdvancedConfiguration from "./CorpusAdvancedConfiguration.vue";

const meta = {
  title: "Corpus Builder/Setup/Advanced Configuration",
  component: CorpusAdvancedConfiguration,
  args: {
    handsFree: {
      enabled: false,
      passes: 1,
      min_confidence: 0.8,
      unresolved: "best_guess",
      accept_records: true,
      publish: false,
    },
    generation: { num_ctx: 32768, temperature: 0.2 },
    stageLimits: {
      segmentation_window_tokens: 5000,
      segmentation_num_predict: 1200,
    },
    stageTimeouts: { segmentation: 300 },
    maxConcurrentRequests: 1,
    useProfileDefaults: true,
    disabled: false,
  },
} satisfies Meta<typeof CorpusAdvancedConfiguration>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ProfileDefaults: Story = {};

export const HandsFreeEnabled: Story = {
  args: {
    handsFree: {
      enabled: true,
      passes: 2,
      min_confidence: 0.9,
      unresolved: "leave",
      accept_records: true,
      publish: false,
    },
  },
};

export const CustomExecution: Story = {
  args: {
    useProfileDefaults: false,
    maxConcurrentRequests: 4,
    generation: { num_ctx: 65536, temperature: 0.1, top_p: 0.9 },
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
