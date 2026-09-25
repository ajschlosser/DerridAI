import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildStageNotice from "./CorpusBuildStageNotice.vue";

const meta = {
  title: "Corpus Builder/Status/Build Stage Notice",
  component: CorpusBuildStageNotice,
  args: { stage: "semantic segmentation" },
} satisfies Meta<typeof CorpusBuildStageNotice>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Segmenting: Story = {};

export const DocumentStructure: Story = {
  args: { stage: "document structure" },
};

export const StageNotReported: Story = {
  args: { stage: undefined },
};

export const NarrowLongStage: Story = {
  args: {
    stage:
      "Validation de la provenance, des limites sémantiques et des métadonnées attribuées aux passages",
  },
  decorators: [
    () => ({
      template: '<div style="max-width: 320px"><story /></div>',
    }),
  ],
};
