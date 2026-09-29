import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResearchAnswerWorkspace from "./ResearchAnswerWorkspace.vue";

const meta: Meta<typeof ResearchAnswerWorkspace> = {
  title: "Research/Answer Workspace",
  component: ResearchAnswerWorkspace,
  parameters: { layout: "padded" },
};
export default meta;
type Story = StoryObj<typeof ResearchAnswerWorkspace>;
export const Empty: Story = { args: { job: null, result: null } };
export const Running: Story = {
  args: {
    job: {
      id: "run-1",
      status: "running",
      prompt: "How are ethics and mortality linked?",
      stage: "rerank",
      stage_detail: "Reranking 64 candidate passages",
    },
  },
};
export const RunningWithDraft: Story = {
  args: {
    job: {
      id: "run-1",
      status: "running",
      prompt: "How are ethics and mortality linked?",
      stage: "generation",
      stage_detail: "Generating the answer",
    },
    draft: {
      jobId: "run-1",
      text: "Derrida treats mortality not simply as an ontological property of Dasein but as a relation to the other that",
      gap: false,
      final: false,
    },
  },
};
export const Completed: Story = {
  args: {
    job: {
      id: "run-2",
      status: "completed",
      prompt: "How are ethics and mortality linked?",
      provider: "ollama",
      model: "phi4:14b",
    },
    result: {
      prompt: "How are ethics and mortality linked?",
      provider: "ollama",
      model: "phi4:14b",
      elapsed_seconds: 18.74,
      evidence: [{ evidence_id: "E0" }, { evidence_id: "E1" }],
      answer:
        "Derrida treats mortality not simply as an ontological property of Dasein but as a relation to the other that intensifies responsibility. The ethical demand appears through the other's exposure to death and therefore cannot be reduced to a self-relation of anticipation.\n\nThe contrast matters because Derrida does not simply replace Heidegger with Levinas. He tracks the tension between singular mortality, substitution, and responsibility while preserving the difficulty of assigning these positions without remainder.\n\n**Works Cited**\n\n1. Derrida, Jacques. Adieu to Emmanuel Levinas.",
    },
  },
};

export const FormattingStress: Story = {
  args: {
    job: {
      id: "run-formatting",
      status: "completed",
      prompt: "How does undecidability condition responsibility?",
      provider: "ollama",
      model: "qwen3:14b",
    },
    result: {
      prompt: "How does undecidability condition responsibility?",
      provider: "ollama",
      model: "qwen3:14b",
      evidence: [
        { evidence_id: "E1", inline_citation: "(Derrida 1995: 24)" },
        { evidence_id: "E2", inline_citation: "(Derrida 1999: 20–21)" },
      ],
      answer:
        "**Responsibility does not begin with the mechanical application of a rule. It requires a decision where calculation reaches its limit.**\n\n**A decision worthy of the name** must pass through undecidability **(Derrida **1995**: 24)** while still answering to inherited norms.\n\n### Consequences\n\n1. Citation typography remains part of the reading line (Derrida 1999: 20–21).\n2. Local **emphasis remains local** instead of changing an entire paragraph.\n\n**Works Cited**\n\n1. Derrida, Jacques. The Gift of Death.",
    },
  },
};
