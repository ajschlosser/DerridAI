// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import MessageDialogHost from "./MessageDialogHost.vue";
import { openMessageDialog } from "../composables/messageDialog";

const meta = {
  title: "Foundations/Feedback/Message Dialog",
  component: MessageDialogHost,
  parameters: { layout: "centered" },
  render: () => ({
    components: { MessageDialogHost },
    template: `<div><button class="btn" type="button" @click="open">Open</button><MessageDialogHost /></div>`,
    methods: {
      open() {
        void openMessageDialog({
          title: "Delete this record?",
          message: "This cannot be undone.",
          tone: "danger",
          confirmLabel: "Delete",
          cancelLabel: "Cancel",
        });
      },
    },
  }),
} satisfies Meta<typeof MessageDialogHost>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Confirmation: Story = {};
