import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResearchResultPresentation from "./ResearchResultPresentation.vue";

const meta: Meta<typeof ResearchResultPresentation> = {
  title: "Research/Result Presentation",
  component: ResearchResultPresentation,
  parameters: { layout: "fullscreen" },
};
export default meta;
type Story = StoryObj<typeof ResearchResultPresentation>;

const result = {
  prompt: "How does Derrida distinguish responsibility from programmable rule-following?",
  answer:
    "Responsibility begins where a decision cannot be reduced to a rule or program (Derrida 1999: 20–21).\n\nA responsible decision must still answer to inherited norms while passing through an irreducible ordeal of undecidability (Derrida 1999: 24).",
  provider: "Ollama",
  model: "qwen3:14b",
  elapsed_seconds: 12.42,
  evidence: [
    {
      evidence_id: "E1",
      inline_citation: "(Derrida 1999: 20–21)",
      full_citation: "Derrida, Jacques. Example citation.",
      collection: "derrida-en",
      rerank_score: 0.931,
      record: {
        record_id: "gift-020",
        work: "The Gift of Death",
        page_start: 20,
        page_end: 21,
        speaker: "Derrida",
        position_holder: "Derrida",
        stance: "develops",
        discourse_role: "argument",
        proposition_status: "asserted",
        text: "A retained evidence passage demonstrating the claim and its provenance.",
      },
    },
    {
      evidence_id: "E2",
      inline_citation: "(Derrida 1999: 24)",
      full_citation: "Derrida, Jacques. Example citation.",
      collection: "derrida-en",
      rerank_score: 0.902,
      record: {
        record_id: "gift-024",
        work: "The Gift of Death",
        page_start: 24,
        speaker: "Derrida",
        position_holder: "Derrida",
        stance: "qualifies",
        discourse_role: "argument",
        proposition_status: "asserted",
        text: "A second evidence passage for inspecting the source binding.",
      },
    },
  ],
};

export const Completed: Story = { args: { result, activeEvidenceIndex: 0, canGrade: true } };
export const SecondEvidenceSelected: Story = {
  args: { result, activeEvidenceIndex: 1, canGrade: true },
};
