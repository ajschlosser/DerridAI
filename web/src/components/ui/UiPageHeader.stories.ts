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
import UiButton from "./UiButton.vue";
import UiPageHeader from "./UiPageHeader.vue";

const meta = {
  title: "UI/Page header",
  component: UiPageHeader,
  args: {
    kicker: "Corpus exploration",
    title: "Records",
    description: "Review loaded records, keep provenance visible, and act on a precise selection.",
    actionsLabel: "Records actions",
  },
  render: (args) => ({
    components: { UiButton, UiPageHeader },
    setup() {
      return { args };
    },
    template: `
      <UiPageHeader v-bind="args">
        <template #actions>
          <UiButton label="Columns" icon="list" />
          <UiButton label="Import" icon="upload" variant="primary" />
        </template>
        <template #meta>
          <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">
            <strong>1,248 <small>visible records</small></strong>
            <strong>27 <small>needs review</small></strong>
            <strong>4 <small>selected</small></strong>
          </div>
        </template>
      </UiPageHeader>
    `,
  }),
} satisfies Meta<typeof UiPageHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
