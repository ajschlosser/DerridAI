import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { CorpusBuild } from "../api/pdfCorpus";
import CorpusInitializationDialog from "./CorpusInitializationDialog.vue";

const build = {
  build_id: "build-demo",
  source_filename: "On Cosmopolitanism and Forgiveness.pdf",
  status: "running",
  stage: "segmenting",
  progress: 0.18,
  record_count: 0,
  accepted_count: 0,
} as CorpusBuild;
const meta: Meta<typeof CorpusInitializationDialog> = {
  title: "Corpus Builder/Build/Initialization Dialog",
  component: CorpusInitializationDialog,
  args: { build },
};
export default meta;
type Story = StoryObj<typeof CorpusInitializationDialog>;
export const Segmenting: Story = {};
export const Reconciling: Story = {
  args: { build: { ...build, stage: "reconciling", progress: 0.37 } as CorpusBuild },
};
