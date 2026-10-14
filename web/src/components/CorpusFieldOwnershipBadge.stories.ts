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
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";
const meta: Meta<typeof CorpusFieldOwnershipBadge> = {
  title: "Corpus Builder/Review/Field Ownership Badge",
  component: CorpusFieldOwnershipBadge,
  args: { status: "inherited" },
};
export default meta;
type Story = StoryObj<typeof CorpusFieldOwnershipBadge>;
export const Inherited: Story = { args: { status: "inherited" } };
export const LlmInferred: Story = { args: { status: "model_inferred" } };
export const HumanOverride: Story = { args: { status: "human_override" } };
export const NeedsReview: Story = { args: { status: "unresolved" } };
