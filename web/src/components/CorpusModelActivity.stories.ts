import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusModelActivity from "./CorpusModelActivity.vue";

const meta = {
  title: "Corpus Builder/Status/Model Activity",
  component: CorpusModelActivity,
  args: {
    activity: {
      state: "working",
      task: "metadata",
      model: "qwen3:8b",
      provider: "ollama",
      seconds: 18,
      calls_in_flight: 1,
    },
  },
} satisfies Meta<typeof CorpusModelActivity>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Working: Story = {};

export const LoadingModel: Story = {
  args: {
    activity: {
      state: "loading_model",
      task: "segmentation",
      model: "gpt-oss:20b",
      provider: "ollama",
      seconds: 73,
      calls_in_flight: 1,
    },
  },
};

export const WaitingOnOtherStep: Story = {
  args: {
    activity: {
      state: "unknown",
      task: "other",
      model: "local-provider-model",
      provider: "local",
      seconds: 7,
      calls_in_flight: 1,
    },
  },
};

export const NarrowLongModelName: Story = {
  args: {
    activity: {
      state: "working",
      task: "manifest",
      model: "research-lab/very-long-local-model-name-with-quantization-profile",
      provider: "local",
      seconds: 128,
      calls_in_flight: 2,
    },
  },
  decorators: [
    (story) => ({
      components: { story },
      template: '<div style="max-width: 320px"><story /></div>',
    }),
  ],
};
