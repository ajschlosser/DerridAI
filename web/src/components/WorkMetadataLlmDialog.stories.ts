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
import WorkMetadataLlmDialog from "./WorkMetadataLlmDialog.vue";
import { openWorkMetadataLlmDialog } from "../composables/workMetadataLlmDialog";

const profiles = [
  {
    id: "local",
    name: "Local Ollama",
    type: "ollama",
    model: "gemma3",
    max_concurrent_requests: 1,
  },
  {
    id: "hosted",
    name: "Hosted",
    type: "openai",
    model: "gpt-4.1",
    max_concurrent_requests: 4,
  },
];

const meta = {
  title: "Works/Work Metadata LLM Dialog",
  component: WorkMetadataLlmDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { WorkMetadataLlmDialog },
    template: `<div><button class="btn" type="button" @click="open(true)">Open</button> <button class="btn" type="button" @click="open(false)">Open without profiles</button><WorkMetadataLlmDialog /></div>`,
    methods: {
      open(withProfiles: boolean) {
        openWorkMetadataLlmDialog({
          scopeCount: 8,
          scopeSummary: "6 Book · 2 Article",
          sample: [
            { work: "Of Grammatology", sourceTypeLabel: "Book" },
            { work: "Writing and Difference", sourceTypeLabel: "Book" },
            { work: "Différance", sourceTypeLabel: "Article" },
          ],
          profiles: withProfiles ? (profiles as never) : [],
          defaultProfileId: "hosted",
          start: async () => undefined,
          manageProviders: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof WorkMetadataLlmDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithProviders: Story = {};
