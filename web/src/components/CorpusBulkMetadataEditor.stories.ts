import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { CorpusRecord } from "../api/pdfCorpus";
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
    records: [
      {
        record_id: "r1",
        region_type: "main_text",
        speaker: "Derrida",
        topics: ["hospitality", "forgiveness"],
      },
      {
        record_id: "r2",
        region_type: "front_matter",
        speaker: "Simon Critchley",
        topics: ["cosmopolitanism"],
      },
    ] as CorpusRecord[],
  },
};
export default meta;
type Story = StoryObj<typeof CorpusBulkMetadataEditor>;
export const Default: Story = {};
export const Disabled: Story = { args: { disabled: true } };
