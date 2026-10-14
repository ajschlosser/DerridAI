/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResearchThreadList from "./ResearchThreadList.vue";

const meta: Meta<typeof ResearchThreadList> = {
  title: "Research/Thread List",
  component: ResearchThreadList,
  args: {
    selectedJobId: "rag-2",
    canManage: true,
    jobs: [
      {
        id: "rag-1",
        status: "running",
        prompt: "How does Derrida distinguish responsibility from duty?",
        stage_detail: "Reranking evidence",
      },
      {
        id: "rag-2",
        status: "completed",
        prompt: "Compare hospitality in Adieu and Of Hospitality",
        source_collection: "derrida",
        finished_at: new Date(Date.now() - 3600_000).toISOString(),
      },
      {
        id: "rag-3",
        status: "failed",
        prompt: "Trace Derrida's use of the gift",
        source_collection: "derrida",
        finished_at: new Date(Date.now() - 86400_000).toISOString(),
      },
    ],
  },
};
export default meta;
type Story = StoryObj<typeof ResearchThreadList>;
export const RunningAndRecent: Story = {};
export const Empty: Story = { args: { jobs: [] } };
