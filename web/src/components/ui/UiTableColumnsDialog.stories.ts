/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { onMounted, ref } from "vue";
import UiTableColumnsDialog from "./UiTableColumnsDialog.vue";

const meta = {
  title: "UI/Table Columns Dialog",
  component: UiTableColumnsDialog,
} satisfies Meta<typeof UiTableColumnsDialog>;
export default meta;
type Story = StoryObj<typeof UiTableColumnsDialog>;

const available = [
  { key: "__db_status", label: "DB status" },
  { key: "work", label: "Work" },
  { key: "page_start", label: "Page start" },
  { key: "needs_review", label: "Needs review" },
  { key: "text", label: "Extracted text" },
  { key: "speaker", label: "Speaker" },
  { key: "record_id", label: "Record ID" },
];

const render = (withWidths: boolean) => () => ({
  components: { UiTableColumnsDialog },
  setup() {
    const selected = ref(["__db_status", "work", "text"]);
    const widths = ref(withWidths ? { __db_status: 12, work: 23, text: 65 } : null);
    const dialog = ref<{ open: () => void } | null>(null);
    onMounted(() => dialog.value?.open());
    return { available, selected, widths, dialog };
  },
  template: withWidths
    ? `<UiTableColumnsDialog ref="dialog" :available="available" v-model="selected" v-model:widths="widths" />`
    : `<UiTableColumnsDialog ref="dialog" :available="available" v-model="selected" />`,
});

/** Records: choose, order and size the columns. */
export const WithWidths: Story = { render: render(true) };
/** Search: choose and order only; the table sizes its own columns. */
export const ChooseAndOrder: Story = { render: render(false) };
