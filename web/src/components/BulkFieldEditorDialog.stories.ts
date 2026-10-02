// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import BulkFieldEditorDialog from "./BulkFieldEditorDialog.vue";
import { openBulkFieldEditorDialog } from "../composables/bulkFieldEditorDialog";

const meta = {
  title: "Records/Bulk Field Editor Dialog",
  component: BulkFieldEditorDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { BulkFieldEditorDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><BulkFieldEditorDialog /></div>`,
    methods: {
      open() {
        openBulkFieldEditorDialog({
          title: "Bulk edit field",
          fixedCount: null,
          defaultScope: "active",
          selectedCount: 0,
          activeCount: 1280,
          currentWork: "Of Grammatology",
          allCount: 2220,
          fields: [
            { id: "speaker", label: "Speaker" },
            { id: "needs_review", label: "Needs review" },
          ],
          inspect: () => ({ targets: 1280, distinct: 1, only: "Derrida" }),
          apply: async () => true,
        });
      },
    },
  }),
} satisfies Meta<typeof BulkFieldEditorDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ActiveTab: Story = {};
