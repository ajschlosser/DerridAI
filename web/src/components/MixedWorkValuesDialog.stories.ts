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
import MixedWorkValuesDialog from "./MixedWorkValuesDialog.vue";
import { openMixedWorkValuesDialog } from "../composables/mixedWorkValuesDialog";

const meta = {
  title: "Works/Mixed Work Values Dialog",
  component: MixedWorkValuesDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { MixedWorkValuesDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><MixedWorkValuesDialog /></div>`,
    methods: {
      open() {
        openMixedWorkValuesDialog({
          work: "Of Grammatology",
          fieldLabel: "Publication year",
          recordCount: 12,
          values: [
            { text: "1967", files: ["grammatology-1.jsonl", "grammatology-2.jsonl"], count: 8 },
            {
              text: "1976",
              files: ["grammatology-3.jsonl", "a.jsonl", "b.jsonl", "c.jsonl"],
              count: 3,
            },
            { text: null, files: ["grammatology-4.jsonl"], count: 1 },
          ],
        });
      },
    },
  }),
} satisfies Meta<typeof MixedWorkValuesDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Variants: Story = {};
