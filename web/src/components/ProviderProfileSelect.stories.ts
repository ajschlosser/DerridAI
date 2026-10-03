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
import ProviderProfileSelect from "./ProviderProfileSelect.vue";
const profiles = [
  {
    id: "ollama-local",
    name: "Local Ollama",
    type: "ollama",
    model: "qwen3:8b",
    base_url: "http://localhost:11434",
    max_concurrent_requests: 2,
  },
  {
    id: "openai-compatible",
    name: "OpenAI-compatible",
    type: "openai",
    model: "gpt-4.1-mini",
    base_url: "https://api.example.test/v1",
    max_concurrent_requests: 4,
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
] as any;
const meta = {
  title: "Providers/Inputs/Profile Select",
  component: ProviderProfileSelect,
  args: { modelValue: "ollama-local", profiles, defaultProfileId: "ollama-local" },
} satisfies Meta<typeof ProviderProfileSelect>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Empty: Story = { args: { modelValue: "", profiles: [] } };
