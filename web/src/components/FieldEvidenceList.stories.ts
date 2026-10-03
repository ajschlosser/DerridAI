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
import FieldEvidenceList from "./FieldEvidenceList.vue";
const evidence = {
  position_holder: {
    block_ids: ["p00031-b0004", "p00031-b0005"],
    confidence: 0.94,
    reason: "The passage explicitly attributes the proposition to Heidegger.",
  },
  stance: {
    block_ids: ["p00031-b0007"],
    confidence: 0.82,
    reason: "Derrida marks a qualification of the reported position.",
  },
};
const meta = {
  title: "Corpus Builder/Review/Field Evidence List",
  component: FieldEvidenceList,
  args: { evidence, selectedField: "position_holder" },
} satisfies Meta<typeof FieldEvidenceList>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Selected: Story = {};
export const Empty: Story = { args: { evidence: {}, selectedField: "" } };
