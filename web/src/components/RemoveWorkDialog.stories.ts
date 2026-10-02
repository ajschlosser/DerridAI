// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RemoveWorkDialog from "./RemoveWorkDialog.vue";
import { openRemoveWorkDialog } from "../composables/removeWorkDialog";

const meta = {
  title: "Works/Remove Work Dialog",
  component: RemoveWorkDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { RemoveWorkDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><RemoveWorkDialog /></div>`,
    methods: {
      open() {
        openRemoveWorkDialog({
          work: "Of Grammatology",
          files: [
            { id: "f1", name: "grammatology-1.jsonl", count: 120 },
            { id: "f2", name: "grammatology-2.jsonl", count: 8 },
          ],
          dbStore: "derrida",
          confirm: async () => undefined,
        });
      },
    },
  }),
} satisfies Meta<typeof RemoveWorkDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithVectorStore: Story = {};
