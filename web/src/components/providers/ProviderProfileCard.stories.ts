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
import ProviderProfileCard from "./ProviderProfileCard.vue";
import type { ProviderProfile } from "../../api/system";

const ollama = {
  id: "o1",
  name: "Local Ollama",
  type: "ollama",
  base_url: "http://ollama:11434",
  model: "qwen3.5:4b",
  max_concurrent_requests: 1,
} as ProviderProfile;

const meta = {
  title: "Providers/Profile card",
  component: ProviderProfileCard,
  decorators: [
    () => ({ template: '<ul style="list-style:none;margin:0;padding:0"><story /></ul>' }),
  ],
  args: {
    profile: ollama,
    models: [],
    tone: "ready",
    statusText: "Ready - 3 models",
    isDefault: true,
    expanded: false,
    busy: "",
    revealed: false,
    canRemove: true,
    sharedLimit: 1,
    sharedEndpoint: false,
  },
} satisfies Meta<typeof ProviderProfileCard>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Collapsed: Story = {};
export const Expanded: Story = { args: { expanded: true } };
export const OpenAiCompatible: Story = {
  args: {
    expanded: true,
    isDefault: false,
    tone: "error",
    statusText: "Connection refused",
    profile: {
      id: "p1",
      name: "FreeLLM",
      type: "openai",
      base_url: "https://api.example.com/v1",
      model_mode: "auto",
      api_key: "sk-example",
    } as ProviderProfile,
  },
};
