import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusAdvancedConfiguration from "./CorpusAdvancedConfiguration.vue";

const meta = {
  title: "Corpus Builder/Setup/Advanced Configuration",
  component: CorpusAdvancedConfiguration,
  args: {
    handsFree: {
      enabled: false,
      passes: 1,
      min_confidence: 0.8,
      unresolved: "best_guess",
      accept_records: true,
      publish: false,
    },
    generation: { num_ctx: 32768, temperature: 0.2 },
    stageLimits: {
      segmentation_window_tokens: 5000,
      segmentation_num_predict: 1200,
    },
    stageTimeouts: { segmentation: 300 },
    maxConcurrentRequests: 1,
    useProfileDefaults: true,
    disabled: false,
  },
} satisfies Meta<typeof CorpusAdvancedConfiguration>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ProfileDefaults: Story = {};

export const HandsFreeEnabled: Story = {
  args: {
    handsFree: {
      enabled: true,
      passes: 2,
      min_confidence: 0.9,
      unresolved: "leave",
      accept_records: true,
      publish: false,
    },
  },
};

export const CustomExecution: Story = {
  args: {
    useProfileDefaults: false,
    maxConcurrentRequests: 4,
    generation: { num_ctx: 65536, temperature: 0.1, top_p: 0.9 },
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
};
