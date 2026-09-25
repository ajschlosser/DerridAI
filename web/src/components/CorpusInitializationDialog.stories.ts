import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusInitializationDialog from "./CorpusInitializationDialog.vue";

const build = {
  build_id: "build-demo",
  source_filename: "On Cosmopolitanism and Forgiveness.pdf",
  status: "running",
  stage: "segmenting",
  progress: 0.18,
  record_count: 0,
  accepted_count: 0,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
} as any;
const meta: Meta<typeof CorpusInitializationDialog> = {
  title: "Corpus Builder/Build/Initialization Dialog",
  component: CorpusInitializationDialog,
  args: { build },
};
export default meta;
type Story = StoryObj<typeof CorpusInitializationDialog>;
export const Segmenting: Story = {};
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
export const Reconciling: Story = {
  args: { build: { ...build, stage: "reconciling", progress: 0.37 } as any },
};
