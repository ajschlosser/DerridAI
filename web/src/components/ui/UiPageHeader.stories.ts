/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiButton from "./UiButton.vue";
import UiPageHeader from "./UiPageHeader.vue";

const meta = {
  title: "UI/Page header",
  component: UiPageHeader,
  args: {
    kicker: "Corpus exploration",
    title: "Records",
    description: "Review loaded records, keep provenance visible, and act on a precise selection.",
    actionsLabel: "Records actions",
  },
  render: (args) => ({
    components: { UiButton, UiPageHeader },
    setup() {
      return { args };
    },
    template: `
      <UiPageHeader v-bind="args">
        <template #actions>
          <UiButton label="Columns" icon="list" />
          <UiButton label="Import" icon="upload" variant="primary" />
        </template>
        <template #meta>
          <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">
            <strong>1,248 <small>visible records</small></strong>
            <strong>27 <small>needs review</small></strong>
            <strong>4 <small>selected</small></strong>
          </div>
        </template>
      </UiPageHeader>
    `,
  }),
} satisfies Meta<typeof UiPageHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
