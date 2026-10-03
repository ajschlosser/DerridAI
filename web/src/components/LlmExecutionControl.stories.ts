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
import LlmExecutionControl from "./LlmExecutionControl.vue";
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const profiles: any[] = [
  {
    id: "primary",
    name: "Scholarly local",
    type: "ollama",
    model: "gemma-4-26B",
    max_concurrent_requests: 2,
  },
  {
    id: "second",
    name: "Second reader",
    type: "ollama",
    model: "qwen3",
    max_concurrent_requests: 1,
  },
  { id: "openai", name: "OpenAI", type: "openai", model: "gpt-5.6" },
];
const meta = {
  title: "Corpus Builder/LLM/Execution Control",
  component: LlmExecutionControl,
  args: {
    modelValue: "primary",
    modelOverride: "gemma-4-26B",
    profiles,
    task: "This model will propose metadata without changing source text.",
  },
} satisfies Meta<typeof LlmExecutionControl>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const OllamaAtCapacity: Story = {
  args: { concurrencyRisk: true, activeRequests: 2, concurrencyLimit: 2 },
};
export const OpenAiProfile: Story = { args: { modelValue: "openai", modelOverride: "gpt-5.6" } };
export const NoProfiles: Story = { args: { modelValue: "", profiles: [] } };
