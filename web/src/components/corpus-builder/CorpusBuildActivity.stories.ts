import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildActivity from "./CorpusBuildActivity.vue";

const build = {
  build_id: "build-live",
  status: "running",
  stage: "enriching",
  progress: 0.64,
  record_count: 42,
  build_events: [
    { at: "2026-09-30T18:00:00Z", stage: "preparing", status: "running", progress: 0.02 },
    { at: "2026-09-30T18:01:00Z", stage: "structure", status: "running", progress: 0.12 },
    {
      at: "2026-09-30T18:03:00Z",
      stage: "constructing_records",
      status: "running",
      progress: 0.36,
    },
    { at: "2026-09-30T18:05:00Z", stage: "enriching", status: "running", progress: 0.64 },
  ],
} as never;

const meta = {
  title: "Corpus Builder/Build/Activity",
  component: CorpusBuildActivity,
  args: { build },
} satisfies Meta<typeof CorpusBuildActivity>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Live: Story = {};
