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
import UiSelect from "./UiSelect.vue";

const meta = {
  title: "Foundations/Forms/Select",
  component: UiSelect,
  render: (args) => ({
    components: { UiSelect },
    setup: () => ({ args }),
    template: '<UiSelect v-bind="args" aria-label="Field type"><option value="text">Text</option><option value="choice">Controlled choice</option><option value="repeatable">Repeatable structure</option></UiSelect>',
  }),
  args: { modelValue: "text" },
} satisfies Meta<typeof UiSelect>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Invalid: Story = { args: { invalid: true } };
export const Disabled: Story = {
  render: (args) => ({
    components: { UiSelect },
    setup: () => ({ args }),
    template: '<UiSelect v-bind="args" aria-label="Field type" disabled><option value="text">Text</option><option value="choice">Controlled choice</option></UiSelect>',
  }),
};
