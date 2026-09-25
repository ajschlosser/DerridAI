import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusHandsFreeSettings from "./CorpusHandsFreeSettings.vue";

const policy = {
  enabled: true,
  passes: 2,
  min_confidence: 0.82,
  unresolved: "leave" as const,
  accept_records: true,
  publish: false,
};

const meta = {
  title: "Corpus Builder/Setup/Hands-Free Settings",
  component: CorpusHandsFreeSettings,
  args: {
    modelValue: policy,
  },
} satisfies Meta<typeof CorpusHandsFreeSettings>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Enabled: Story = {};

export const DisabledMode: Story = {
  args: {
    modelValue: { ...policy, enabled: false },
  },
};

export const ConservativeReview: Story = {
  args: {
    modelValue: {
      enabled: true,
      passes: 1,
      min_confidence: 0.95,
      unresolved: "leave",
      accept_records: false,
      publish: false,
    },
  },
};

export const AutoPublish: Story = {
  args: {
    modelValue: {
      enabled: true,
      passes: 3,
      min_confidence: 0.9,
      unresolved: "best_guess",
      accept_records: true,
      publish: true,
    },
  },
};

export const DisabledControls: Story = {
  args: {
    disabled: true,
  },
};

export const EmbeddedWithoutEnable: Story = {
  args: {
    showEnable: false,
  },
};

export const Narrow: Story = {
  decorators: [
    (story) => ({
      components: { story },
      template: '<div style="max-width: 360px"><story /></div>',
    }),
  ],
};
