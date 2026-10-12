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
import ResearchAnswerContent from "./ResearchAnswerContent.vue";

const meta: Meta<typeof ResearchAnswerContent> = {
  title: "Research/Answer Content",
  component: ResearchAnswerContent,
  parameters: { layout: "padded" },
};
export default meta;
type Story = StoryObj<typeof ResearchAnswerContent>;

const answer = [
  "### Responsibility and attribution",
  "",
  "The author distinguishes the **speaker** from the position holder [[E1]].",
  "",
  "1. First claim draws on primary evidence [E1].",
  "2. Second claim requires separate support [E2].",
  "",
  "The citation [E9] is unresolved and therefore not interactive.",
].join("\n");

const evidence = [
  { evidence_id: "E1", inline_citation: "(Derrida 1997: 11)" },
  { evidence_id: "E2", inline_citation: "(Derrida 1999: 20–21)" },
];

export const Standalone: Story = { args: { answer, evidence } };
export const ThreadTurn: Story = {
  args: { answer, evidence, compact: true, readOnly: true },
};
export const MissingEvidence: Story = {
  args: { answer, evidence: [], compact: true, readOnly: true },
};
export const Narrow: Story = {
  args: { answer, evidence, compact: true, readOnly: true },
  parameters: { viewport: { defaultViewport: "mobile1" } },
};
