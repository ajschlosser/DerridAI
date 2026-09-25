import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildReadiness from "./CorpusBuildReadiness.vue";

const meta = {
  title: "Corpus Builder/Setup/Build Readiness",
  component: CorpusBuildReadiness,
  args: {
    mediaKind: "pdf",
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
    warnings: ["Review source structure before building."],
  },
};

export const ConcurrentBuild: Story = {
  args: { activeBuildCount: 2 },
};

export const AudioSource: Story = {
  args: {
    mediaKind: "audio",
    sourceFilename: "seminar-session-04.flac",
    pageCount: 0,
    blockCount: 142,
    structureSummary: "",
  },
};

export const ImageSource: Story = {
  args: {
    mediaKind: "image",
    sourceFilename: "archive-scan-017.tiff",
    pageCount: 0,
    blockCount: 36,
    structureSummary: "",
  },
};

export const NarrowLongSource: Story = {
  args: {
    sourceFilename:
      "Cosmopolites de tous les pays, encore un effort — édition critique annotée et révisée.pdf",
    modelLabel: "modèle-local-avec-un-nom-particulièrement-long-pour-la-validation-responsive",
  },
  decorators: [
    (story) => ({
      components: { story },
      template: '<div style="max-width: 520px"><story /></div>',
    }),
  ],
};
