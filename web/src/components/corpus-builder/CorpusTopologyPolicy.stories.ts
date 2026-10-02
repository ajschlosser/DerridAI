import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusTopologyPolicy from "./CorpusTopologyPolicy.vue";

const meta = {
  title: "Corpus Builder/Setup/Topology Policy",
  component: CorpusTopologyPolicy,
  args: {
    modelValue: {
      mode: "source_units",
      source_units_per_record: 1,
      records_per_page: 4,
    },
    syntheticPagesAvailable: true,
    disabled: false,
  },
} satisfies Meta<typeof CorpusTopologyPolicy>;

export default meta;
type Story = StoryObj<typeof meta>;

export const FixedSourceUnits: Story = {};
export const SemanticWithAuthoritativePages: Story = {
  args: {
    modelValue: {
      mode: "semantic",
      source_units_per_record: 1,
      records_per_page: null,
    },
    syntheticPagesAvailable: false,
  },
};
