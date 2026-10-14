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
import ProviderTuningFields from "./ProviderTuningFields.vue";
import type { ProviderProfile } from "../../api/system";

const meta = {
  title: "Providers/Tuning fields",
  component: ProviderTuningFields,
  args: {
    profile: { id: "o1", name: "Local Ollama", type: "ollama" } as ProviderProfile,
    sharedLimit: 1,
    sharedEndpoint: false,
  },
} satisfies Meta<typeof ProviderTuningFields>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Ollama: Story = {};
export const SharedEndpoint: Story = { args: { sharedEndpoint: true } };
export const OpenAiCompatible: Story = {
  args: { profile: { id: "p1", name: "FreeLLM", type: "openai" } as ProviderProfile },
};
