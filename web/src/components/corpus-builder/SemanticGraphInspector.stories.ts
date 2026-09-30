/* Copyright 2026 Aaron John Schlosser, PhD. */
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
