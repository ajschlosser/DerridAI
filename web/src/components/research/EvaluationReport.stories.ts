import type { Meta, StoryObj } from "@storybook/vue3-vite";
import EvaluationReport from "./EvaluationReport.vue";

const meta = {
  title: "Research/Evaluation Report",
  component: EvaluationReport,
  args: {
    report: {
      overall: 8,
      summary: "Strong source binding with one attribution risk.",
      analysis:
        "The response is useful and well grounded overall, but one interpretive transition should be qualified.",
      categories: {
        query_relevance: { score: 9, analysis: "Directly answers the question." },
        source_binding: { score: 9, analysis: "Claims are tied to supplied evidence." },
        claim_traceability: { score: 8, analysis: "Most propositions can be traced cleanly." },
        attribution_source_discrimination: {
          score: 7,
          analysis: "One attributed position could be more explicit.",
        },
        claim_evidence_fidelity: { score: 8, analysis: "Evidence supports the principal claims." },
        conceptual_precision: { score: 8, analysis: "Terminology is used carefully." },
        coverage: { score: 7, analysis: "A secondary thread is omitted." },
        interpretive_usefulness: { score: 9, analysis: "Synthesis is analytically useful." },
      },
      strengths: ["Clear source binding", "Good conceptual precision"],
      weaknesses: ["One compressed transition"],
      unsupported_or_risky_claims: ["Qualify the attribution in paragraph three"],
      raw_output: { example: true },
    },
  },
} satisfies Meta<typeof EvaluationReport>;
export default meta;
type Story = StoryObj<typeof meta>;
export const FullReport: Story = {};
