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
import { ref } from "vue";
import SubsetCondition from "./SubsetCondition.vue";

const meta = {
  title: "Records/Subset Condition",
  component: SubsetCondition,
} satisfies Meta<typeof SubsetCondition>;
export default meta;
type Story = StoryObj<typeof SubsetCondition>;

const fields = [
  { key: "work", label: "Work" },
  { key: "exists_flag", label: "Needs review" },
];
const render = (operator: string, value: string) => () => ({
  components: { SubsetCondition },
  setup() {
    const state = { field: ref("work"), operator: ref(operator), value: ref(value) };
    return { ...state, fields, suggestions: ["Glas", "Margins of Philosophy"] };
  },
  template: `<SubsetCondition v-model:field="field" v-model:operator="operator" v-model:value="value" :fields="fields" :suggestions="suggestions" position="item 1" />`,
});

export const WithValue: Story = { render: render("equals", "Glas") };
/** Presence and truth tests take no value, so the value box is disabled. */
export const Valueless: Story = { render: render("exists", "") };
