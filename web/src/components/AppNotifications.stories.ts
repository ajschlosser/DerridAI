// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import AppNotifications from "./AppNotifications.vue";
import { toast } from "../composables/notifications";

const meta = {
  title: "Foundations/Feedback/Notifications",
  component: AppNotifications,
  parameters: { layout: "centered" },
  render: () => ({
    components: { AppNotifications },
    template: `<div>
      <button class="btn" type="button" @click="show('success')">Success</button>
      <button class="btn" type="button" @click="show('warning')">Warning</button>
      <button class="btn" type="button" @click="show('danger')">Error</button>
      <AppNotifications />
    </div>`,
    methods: {
      show(tone: "success" | "warning" | "danger") {
        toast(`A ${tone} notification that stays until it is dismissed.`, {
          tone,
          duration: 60_000,
        });
      },
    },
  }),
} satisfies Meta<typeof AppNotifications>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Tones: Story = {};
