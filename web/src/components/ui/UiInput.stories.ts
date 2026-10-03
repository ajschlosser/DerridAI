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
import UiInput from "./UiInput.vue";

const meta = {
  title: "Foundations/Forms/Input",
  component: UiInput,
  render: (args) => ({
    components: { UiInput },
    setup: () => ({ args }),
    template: '<UiInput v-bind="args" aria-label="Document author" />',
  }),
  args: { modelValue: "Jacques Derrida" },
} satisfies Meta<typeof UiInput>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Invalid: Story = { args: { invalid: true } };
export const Disabled: Story = {
  render: (args) => ({
    components: { UiInput },
    setup: () => ({ args }),
    template: '<UiInput v-bind="args" aria-label="Document author" disabled />',
  }),
};
export const Number: Story = {
  args: { modelValue: 0.75, type: "number" },
  render: (args) => ({
    components: { UiInput },
    setup: () => ({ args }),
    template: '<UiInput v-bind="args" aria-label="Similarity threshold" min="0" max="1" step="0.05" />',
  }),
};
