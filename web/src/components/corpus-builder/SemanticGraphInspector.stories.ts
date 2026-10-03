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
import type { SemanticGraphViewRelation } from "../../api/corpus";
import SemanticGraphInspector from "./SemanticGraphInspector.vue";

const node = (id: string, label: string) => ({
  id,
  type: "concept",
  label,
  aliases: ["trace"],
  mention_count: 42,
  record_count: 7,
  degree: 5,
});
const relation = (
  id: string,
  kind: SemanticGraphViewRelation["relation_kind"],
  status: SemanticGraphViewRelation["authority_status"],
): SemanticGraphViewRelation => ({
  id,
  source: "n1",
  target: "n2",
  predicate: "critiques",
  relation_kind: kind,
  authority_status: status,
  count: 3,
  direction: "outgoing" as const,
  other_id: "n2",
  other_label: "Presence",
  other_type: "concept",
  record_ids: ["r1"],
  record_count: 2,
  supporting_fields: ["position_holder"],
  derivation_method: "field_assertion_projection",
  evidence_ref_count: 2,
  observed_verbs: [],
});

const meta = {
  title: "Corpus Builder/Review/Semantic Graph Inspector",
  component: SemanticGraphInspector,
  args: {
    selectedNode: node("n1", "Différance"),
    focusDetail: {
      node: node("n1", "Différance"),
      relations: [
        relation("a", "semantic", "human_confirmed"),
        relation("b", "semantic", "disputed"),
        relation("c", "observational", "unreviewed"),
      ],
      relations_total: 3,
    },
    selectedEdges: [],
    nodesById: new Map(),
    focusId: "",
    hueClass: () => "hue-1",
  },
} satisfies Meta<typeof SemanticGraphInspector>;

export default meta;
type Story = StoryObj<typeof meta>;

export const FocusedEntity: Story = {};
export const NothingSelected: Story = { args: { selectedNode: null, focusDetail: null } };
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
