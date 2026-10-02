// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import SeparateWorksDialog from "./SeparateWorksDialog.vue";
import { openSeparateWorksDialog } from "../composables/separateWorksDialog";

const meta = {
  title: "Works/Separate Works Dialog",
  component: SeparateWorksDialog,
  parameters: { layout: "centered" },
  render: () => ({
    components: { SeparateWorksDialog },
    template: `<div><button class="btn" type="button" @click="open">Open</button><SeparateWorksDialog /></div>`,
    methods: {
      open() {
        openSeparateWorksDialog({
          sources: [
            {
              id: "f1",
              name: "collected.jsonl",
              recordCount: 130,
              groups: [
                { work: "Of Grammatology", count: 100, defaultChecked: true },
                { work: "Speech and Phenomena", count: 20, defaultChecked: true },
                { work: "Untitled work", count: 10, defaultChecked: false },
              ],
            },
          ],
          confirm: async () => undefined,
        });
      },
    },
  }),
} satisfies Meta<typeof SeparateWorksDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const MultiWorkFile: Story = {};
