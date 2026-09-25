import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusRecordSizingSettings from "./CorpusRecordSizingSettings.vue";
const meta = {
  title: "Corpus Builder/Settings/Record Sizing",
  component: CorpusRecordSizingSettings,
  args: {
    modelValue: {
      preferred_record_chars: 1750,
      record_length_tolerance: 200,
      long_record_chars: 3500,
      absolute_record_chars: 6000,
    },
  },
} satisfies Meta<typeof CorpusRecordSizingSettings>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };
export const WiderResearchChunks: Story = {
  args: {
    modelValue: {
      preferred_record_chars: 2400,
      record_length_tolerance: 250,
      long_record_chars: 4200,
      absolute_record_chars: 7000,
    },
  },
};
