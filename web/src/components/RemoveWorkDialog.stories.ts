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
import RemoveWorkDialog from "./RemoveWorkDialog.vue";
import { openRemoveWorkDialog } from "../composables/removeWorkDialog";

const meta = {
  title: "Works/Remove Work Dialog",
  component: RemoveWorkDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { RemoveWorkDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><RemoveWorkDialog /></div>`,
    methods: {
      open() {
        openRemoveWorkDialog({
          work: "Of Grammatology",
          files: [
            { id: "f1", name: "grammatology-1.jsonl", count: 120 },
            { id: "f2", name: "grammatology-2.jsonl", count: 8 },
          ],
          dbStore: "derrida",
          confirm: async () => undefined,
        });
      },
    },
  }),
} satisfies Meta<typeof RemoveWorkDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithVectorStore: Story = {};
