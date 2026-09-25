import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResearchPipelineBar from "./ResearchPipelineBar.vue";
const meta: Meta<typeof ResearchPipelineBar> = {
  title: "Research/Pipeline Bar",
  component: ResearchPipelineBar,
  args: {
    selectedJobId: "rag-2",
    canManage: true,
    jobs: [
      {
        id: "rag-1",
        status: "running",
        prompt: "How does Derrida distinguish responsibility from duty?",
        stage_detail: "Reranking evidence",
        model: "qwen3",
      },
      {
        id: "rag-2",
        status: "queued",
        prompt: "Compare hospitality in Adieu and Of Hospitality",
        stage_detail: "Waiting for provider capacity",
        model: "phi4",
      },
      {
        id: "rag-3",
        status: "running",
        prompt: "Trace Derrida's use of the gift",
        stage_detail: "Generating answer",
        model: "gpt-oss",
      },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof ResearchPipelineBar>;
export const MultipleConcurrentRuns: Story = {};
