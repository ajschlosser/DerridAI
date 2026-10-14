/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
