import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import CorpusConfigurationNav from "./CorpusConfigurationNav.vue";

const meta = {
  title: "Corpus Builder/Setup/Configuration Navigation",
  component: CorpusConfigurationNav,
  render: (args) => ({
    components: { CorpusConfigurationNav },
    setup: () => {
      const value = ref(args.modelValue);
      return { args, value };
    },
    template: `
      <div>
        <CorpusConfigurationNav v-bind="args" v-model="value" />
        <div
          v-for="id in ['source', 'structure', 'enrichment', 'metadata', 'advanced']"
          :id="'corpus-config-panel-' + id"
          :key="id"
          role="tabpanel"
          :aria-labelledby="'corpus-config-tab-' + id"
          :hidden="value !== id"
        >
          {{ id }}
        </div>
      </div>
    `,
  }),
  args: {
    modelValue: "source",
    hasSource: true,
    structureAvailable: true,
  },
} satisfies Meta<typeof CorpusConfigurationNav>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Source: Story = {};

export const Enrichment: Story = {
  args: { modelValue: "enrichment" },
};

export const NoSource: Story = {
  args: {
    modelValue: "source",
    hasSource: false,
    structureAvailable: false,
  },
};

export const FrenchLengthStress: Story = {
  parameters: { locale: "fr-CA" },
  args: { modelValue: "metadata" },
};
