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
import UiField from "./UiField.vue";
const meta = {
  title: "Foundations/Forms/Field",
  component: UiField,
  render: (args) => ({
    components: { UiField },
    setup: () => ({ args }),
    template:
      '<UiField v-bind="args"><input class="control" :aria-invalid="Boolean(args.error)" value="Jacques Derrida" /></UiField>',
  }),
  args: { label: "Document author", hint: "Inherited by records unless explicitly overridden." },
} satisfies Meta<typeof UiField>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Invalid: Story = { args: { error: "Enter a document author.", hint: "" } };
export const WithPersistence: Story = { args: { persistence: "Saved in this browser" } };
