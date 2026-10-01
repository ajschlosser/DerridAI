import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBulkMetadataEditor from "./CorpusBulkMetadataEditor.vue";
const meta: Meta<typeof CorpusBulkMetadataEditor> = {
  title: "Corpus Builder/Review/Bulk Metadata Editor",
  component: CorpusBulkMetadataEditor,
  args: {
    selectedCount: 4,
    totalCount: 76,
    disabled: false,
    regionTypes: ["front_matter", "main_text", "notes", "back_matter"],
    discourseRoles: ["assertion", "analysis", "quotation", "paratext"],
    knownValues: {
      speaker: ["Author", "Simon Critchley"],
      topics: ["hospitality", "forgiveness", "cosmopolitanism"],
    },
  },
};
export default meta;
type Story = StoryObj<typeof CorpusBulkMetadataEditor>;
export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };
