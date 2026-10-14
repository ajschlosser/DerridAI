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
import CorpusProviderSwitcher from "./CorpusProviderSwitcher.vue";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const profiles: any[] = [
  {
    id: "gemma26",
    name: "Gemma 4 26B",
    type: "ollama",
    model: "hf.co/unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS",
  },
  { id: "qwen27", name: "Qwen 27B", type: "ollama", model: "Qwen3.8-27B" },
];
const meta = {
  title: "Corpus Builder/Enrichment/Provider Switcher",
  component: CorpusProviderSwitcher,
  args: {
    profiles,
    activeProfileId: "gemma26",
    activeModel: profiles[0].model,
    history: [
      {
        at: "2026-09-18T12:00:00Z",
        provider_profile_id: "qwen27",
        model: "Qwen3.8-27B",
        metadata_completed: 0,
      },
      {
        at: "2026-09-18T12:20:00Z",
        provider_profile_id: "gemma26",
        model: profiles[0].model,
        metadata_completed: 12,
      },
    ],
  },
} satisfies Meta<typeof CorpusProviderSwitcher>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };
