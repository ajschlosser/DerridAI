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
import ResearchClaimReviewPanel from "./ResearchClaimReviewPanel.vue";

const meta: Meta<typeof ResearchClaimReviewPanel> = {
  title: "Research/Claim Review Panel",
  component: ResearchClaimReviewPanel,
  parameters: { layout: "padded" },
  args: {
    refreshAuthoritative: false,
    evidence: [
      {
        evidence_id: "E1",
        inline_citation: "(Derrida, 25)",
        record: { record_id: "r1", record_revision: 2 },
      },
      {
        evidence_id: "E2",
        inline_citation: "(Derrida, 77)",
        record: { record_id: "r2", record_revision: 1 },
      },
    ],
    provenance: {
      claims: [
        {
          claim_id: "c1",
          claim_text: "Unconditional hospitality exceeds the conditions that regulate it.",
          validation_status: "unvalidated",
        },
        {
          claim_id: "c2",
          claim_text: "The conditional laws of hospitality remain necessary in political life.",
          validation_status: "validated",
          validated_by: "reviewer",
        },
      ],
      support_bindings: [
        {
          support_binding_id: "s1",
          claim_id: "c1",
          record_id: "r1",
          record_revision: 2,
          relation: "supports",
          validation_status: "unvalidated",
          citation: { inline: "(Derrida, 25)", evidence_marker: "E1" },
        },
        {
          support_binding_id: "s2",
          claim_id: "c2",
          record_id: "r2",
          record_revision: 1,
          relation: "supports",
          validation_status: "validated",
          citation: { inline: "(Derrida, 77)", evidence_marker: "E2" },
        },
      ],
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const MissingSupport: Story = {
  args: {
    provenance: {
      claims: [
        {
          claim_id: "c3",
          claim_text: "A generated claim whose evidence binding was not retained.",
          validation_status: "unvalidated",
        },
      ],
      support_bindings: [],
    },
  },
};
