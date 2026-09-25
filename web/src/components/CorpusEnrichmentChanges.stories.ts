import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusEnrichmentChanges from "./CorpusEnrichmentChanges.vue";

const baseRecord = {
  speaker: "Derrida",
  position_holder: "Levinas",
  stance: "critical",
  metadata_field_status: {
    speaker: { status: "model_inferred" },
    position_holder: { status: "unresolved" },
    stance: { status: "model_inferred" },
  },
  metadata_enrichment_history: [
    {
      run_id: "run-2",
      pass: 2,
      model: "qwen3:8b",
      added_fields: ["speaker"],
      replaced: [{ field: "stance", previous: "descriptive", value: "critical" }],
      disputes: [
        {
          field: "position_holder",
          existing: "Kant",
          proposed: "Levinas",
          candidates: [
            {
              candidate_id: "candidate-current",
              value: "Kant",
              source: "current",
              pass: 1,
            },
            {
              candidate_id: "candidate-model",
              value: "Levinas",
              source: "llm",
              model: "qwen3:8b",
              pass: 2,
              confidence: 0.74,
            },
          ],
        },
      ],
      informational: [
        {
          kind: "agreement",
          field: "speaker",
          confidence: 0.93,
          model: "qwen3:8b",
          pass: 2,
          reason: "The second pass agreed with the current source-bound value.",
        },
      ],
    },
  ],
};

const meta = {
  title: "Corpus Builder/Review/Enrichment Changes",
  component: CorpusEnrichmentChanges,
  args: {
    record: baseRecord,
  },
} satisfies Meta<typeof CorpusEnrichmentChanges>;

export default meta;
type Story = StoryObj<typeof meta>;

export const MixedChanges: Story = {};

export const Busy: Story = {
  args: {
    busy: true,
  },
};

export const ProtectedSuggestion: Story = {
  args: {
    record: {
      speaker: "Derrida",
      metadata_field_status: {
        speaker: { status: "human_confirmed" },
      },
      metadata_enrichment_history: [
        {
          pass: 3,
          informational: [
            {
              kind: "protected_suggestion",
              field: "speaker",
              authoritative_value: "Derrida",
              proposed_value: "Levinas",
              confidence: 0.81,
              model: "qwen3:8b",
              pass: 3,
              reason:
                "The model proposal was retained as information and did not overwrite the human decision.",
            },
          ],
        },
      ],
    },
  },
};

export const NarrowLongValues: Story = {
  args: {
    record: {
      position_holder:
        "A deliberately long position-holder value used to verify wrapping rather than truncation",
      metadata_field_status: {
        position_holder: { status: "unresolved" },
      },
      metadata_enrichment_history: [
        {
          disputes: [
            {
              field: "position_holder",
              existing:
                "A very long current interpretation that should remain legible at narrow widths",
              proposed:
                "An alternative interpretation with enough text to exercise the compact candidate layout",
            },
          ],
        },
      ],
    },
  },
  decorators: [
    (story) => ({
      components: { story },
      template: '<div style="max-width: 360px"><story /></div>',
    }),
  ],
};
