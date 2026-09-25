import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusFieldPolicyBadges from "./CorpusFieldPolicyBadges.vue";

const schemaField = {
  field_id: "field-position-holder",
  name: "position_holder",
  semantic_compatibility_id: "derridai.position_holder",
  label: "Position holder",
  type: "text" as const,
  group: "provenance",
  values: [],
  strict: false,
  instruction: "Identify whose position is represented.",
  definitions_heading: "",
  evidence: true,
  assess: true,
  review: true,
  retrieval_profile: {
    enabled: true,
    max_items: 6,
    min_similarity: 0.72,
    include_corrections: true,
    include_confirmed_absence: true,
  },
  pos_tags: [],
  ner_tags: [],
};

const meta = {
  title: "Corpus Builder/Review/Field Policy Badges",
  component: CorpusFieldPolicyBadges,
  args: {
    field: "position_holder",
    schemaField,
  },
} satisfies Meta<typeof CorpusFieldPolicyBadges>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SchemaManaged: Story = {};

export const CoreRequired: Story = {
  args: {
    field: "discourse_role",
    coreRequired: true,
    schemaField: {
      ...schemaField,
      field_id: "field-discourse-role",
      name: "discourse_role",
      semantic_compatibility_id: "derridai.discourse_role",
      label: "Discourse role",
      retrieval_profile: {
        ...schemaField.retrieval_profile,
        enabled: false,
        max_items: 0,
      },
    },
  },
};

export const OptionalNoMemory: Story = {
  args: {
    field: "custom_note",
    schemaField: {
      ...schemaField,
      field_id: "field-custom-note",
      name: "custom_note",
      semantic_compatibility_id: null,
      label: "Custom note",
      evidence: false,
      assess: false,
      review: false,
      retrieval_profile: {
        enabled: false,
        max_items: 0,
        min_similarity: 0,
        include_corrections: false,
        include_confirmed_absence: false,
      },
    },
  },
};

export const Narrow: Story = {
  decorators: [
    (story) => ({
      components: { story },
      template: '<div style="max-width: 240px"><story /></div>',
    }),
  ],
};
