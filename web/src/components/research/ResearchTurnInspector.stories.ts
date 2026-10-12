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
import ResearchTurnInspector from "./ResearchTurnInspector.vue";

const meta: Meta<typeof ResearchTurnInspector> = {
  title: "Research/Turn Inspector",
  component: ResearchTurnInspector,
  parameters: { layout: "padded" },
};
export default meta;
type Story = StoryObj<typeof ResearchTurnInspector>;

export const WithEvidence: Story = {
  args: {
    instanceId: "story-turn-1",
    contextLabel: "Turn 1",
    researcher: true,
    job: { id: "job-story" } as never,
    result: {
      answer: "The author distinguishes the speaker from the position holder [[E1]].",
      provider: "ollama",
      model: "example-model",
      evidence: [
        {
          evidence_id: "E1",
          collection: "corpus",
          inline_citation: "Author 1997: 97",
          record: {
            record_id: "r1",
            text: "The source does not assert presence.",
            speaker: "Author",
            position_holder: "Other Thinker",
            work: "Example Work",
            edition: "First edition",
            printed_page_start: "97",
            physical_page_start: 112,
            record_revision: 3,
          },
        },
      ],
      claim_provenance: {
        claims: [
          {
            claim_id: "c1",
            claim_text: "The speaker is distinguished from the position holder.",
            validation_status: "validated",
          },
        ],
        support_bindings: [
          {
            support_binding_id: "b1",
            claim_id: "c1",
            record_id: "r1",
            record_revision: 2,
            relation: "supports",
            citation: { evidence_marker: "E1" },
            validation_status: "stale",
          },
        ],
      },
    },
  },
};

export const NoEvidenceOrClaims: Story = {
  args: {
    instanceId: "story-turn-2",
    contextLabel: "Turn 2",
    result: { answer: "No supported answer could be produced.", evidence: [] },
  },
};
