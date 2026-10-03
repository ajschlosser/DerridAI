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
import CorpusActionMenu from "./CorpusActionMenu.vue";

const items = [
  { id: "previous", label: "Combine with previous record" },
  {
    id: "next",
    label: "Combine with next record",
    reason: "There is no next record to combine with.",
  },
  { id: "slice", label: "Slice record" },
  { id: "preview", label: "Preview JSONL" },
];
const meta = {
  title: "Corpus Builder/Review/Action Menu",
  component: CorpusActionMenu,
  args: { label: "More actions", menuLabel: "More record actions", items, placement: "bottom" },
  // The menu opens below the button; leave room so the story shows it.
  decorators: [() => ({ template: '<div style="min-height:16rem;padding:1rem"><story /></div>' })],
} satisfies Meta<typeof CorpusActionMenu>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const AllAvailable: Story = {
  args: { items: items.map(({ id, label }) => ({ id, label })) },
};
export const OpensAbove: Story = {
  args: { placement: "top" },
  decorators: [() => ({ template: '<div style="padding-top:16rem"><story /></div>' })],
};
export const Disabled: Story = { args: { disabled: true } };
