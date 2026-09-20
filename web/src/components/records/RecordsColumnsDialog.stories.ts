/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { onMounted, ref } from "vue";
import RecordsColumnsDialog from "./RecordsColumnsDialog.vue";

const meta = {
  title: "Records/Columns Dialog",
  component: RecordsColumnsDialog,
} satisfies Meta<typeof RecordsColumnsDialog>;
export default meta;
type Story = StoryObj<typeof RecordsColumnsDialog>;

const available = [
  {key: "__db_status", label: "DB status"},
  {key: "work", label: "Work"},
  {key: "page_start", label: "Page start"},
  {key: "needs_review", label: "Needs review"},
  {key: "text", label: "Extracted text"},
  {key: "speaker", label: "Speaker"},
  {key: "record_id", label: "Record ID"},
];

export const Open: Story = {
  render: () => ({
    components: {RecordsColumnsDialog},
    setup() {
      const selected = ref(["__db_status", "work", "text"]);
      const dialog = ref<{open: () => void} | null>(null);
      onMounted(() => dialog.value?.open());
      return {available, selected, dialog};
    },
    template: `<RecordsColumnsDialog ref="dialog" :available="available" v-model="selected" />`,
  }),
};
