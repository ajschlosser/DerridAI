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
