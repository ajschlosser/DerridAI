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
import RecordContextReader from "./RecordContextReader.vue";

// Context is fetched from the API; without a backend the story shows the record alone.
const meta = {
  title: "Corpus Builder/Review/Record Context Reader",
  component: RecordContextReader,
  args: {
    buildId: "b1",
    recordId: "r3",
    text: "Hospitality is culture itself and not simply one ethic among others.",
    showContext: true,
  },
} satisfies Meta<typeof RecordContextReader>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const ContextOff: Story = { args: { showContext: false } };
