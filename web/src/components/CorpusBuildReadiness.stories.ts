import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildReadiness from "./CorpusBuildReadiness.vue";

const meta = {
  title: "Corpus/Build Readiness",
  component: CorpusBuildReadiness,
  args: {
    sourceFilename: "On Cosmopolitanism and Forgiveness.pdf",
    pageCount: 75,
    blockCount: 307,
    structureSummary: "Main text PDF 9 → printed p. 1",
    providerLabel: "Local Ollama",
    modelLabel: "qwen3.5:4b",
    enrichmentMode: "deep",
    targetChars: 1750,
    toleranceChars: 200,
    contextSafe: true,
    activeBuildCount: 0,
    canStart: true,
  },
} satisfies Meta<typeof CorpusBuildReadiness>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Ready: Story = {};
export const NeedsAttention: Story = {
  args: {
    canStart: false,
    contextSafe: false,
    warnings: ["Review document structure before building."],
  },
};
export const ConcurrentBuild: Story = { args: { activeBuildCount: 2 } };
