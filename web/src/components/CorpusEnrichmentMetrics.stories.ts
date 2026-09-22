/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusEnrichmentMetrics from "./CorpusEnrichmentMetrics.vue";
import { pdfCorpusApi } from "../api/pdfCorpus";

const model = {
  proposals: 261,
  reviews: 39,
  autofilled: 12,
  acceptance_rate: 0.91,
  brier_score: 0.101,
  correction_rate: 0,
  rejection_rate: 0.1,
  autofill_precision: null,
  stability: null,
  touched_share: 0.15,
  grounded_rate: 0.38,
  ms_per_accepted_field: 88100,
  precision_at_threshold: [{ threshold: 0.9, reviews: 20, precision: 0.88, coverage: 0.94 }],
  learning_curve: [],
  acceptance_ci: { rate: 0.91, low: 0.76, high: 0.96, n: 39 },
  substantive_error_rate: { rate: 0, low: 0, high: 0.09, n: 39 },
  autofill_precision_ci: { rate: null, low: null, high: null, n: 0 },
  spot_checks_still_needed: 13,
  correction_severity: {},
  supported_rate: 0.63,
  supported_checked: 27,
  repeat_rate: null,
  proposals_after_a_rejection: 0,
  review_seconds_per_decision: 2,
  seconds_to_first_useful_value: 20,
  autofill_suspensions: 0,
  autofill_resumptions: 0,
};

const meta = {
  title: "Corpus Builder/Review/Enrichment Measurements",
  component: CorpusEnrichmentMetrics,
  args: { buildId: "demo" },
  decorators: [
    () => ({
      setup() {
        pdfCorpusApi.enrichmentMetrics = async () => ({
          models: { "gemma4-12b-it-qat-derridAI": model },
          inter_model_agreement: { compared: 0, agreement: null },
          unresolved_remaining: 194,
          runs: ["r1"],
          concurrency: { limit: 1, working: 0 },
        });
      },
      template: "<div style='max-width:1100px'><story /></div>",
    }),
  ],
} satisfies Meta<typeof CorpusEnrichmentMetrics>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Loaded: Story = {};
export const FrenchLengthStress: Story = { parameters: { locale: "fr-CA" } };
