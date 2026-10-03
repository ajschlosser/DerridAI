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
import UiCheckbox from "./UiCheckbox.vue";

const meta = {
  title: "Foundations/Forms/Checkbox",
  component: UiCheckbox,
  args: {
    modelValue: true,
    label: "Require evidence",
    description: "The model must bind this value to an exact source span.",
  },
} satisfies Meta<typeof UiCheckbox>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };
export const Invalid: Story = { args: { invalid: true } };
export const LongFrenchCopy: Story = {
  args: {
    label: "Exiger des preuves pour chaque valeur proposée",
    description:
      "La valeur doit être reliée à un passage source précis afin que la décision puisse être vérifiée pendant la révision.",
  },
};
