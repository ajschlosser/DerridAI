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
import AccessibleEmptyState from "./AccessibleEmptyState.vue";
const meta = {
  title: "Foundations/Feedback/Empty State",
  component: AccessibleEmptyState,
  args: {
    title: "No records yet",
    description: "Choose a work or change the search filters.",
    actionLabel: "Browse works",
    icon: "books",
  },
} satisfies Meta<typeof AccessibleEmptyState>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};

export const NeutralIcon: Story = {
  args: {
    title: "No saved responses",
    description: "Saved research responses will appear here.",
    icon: "spark",
    iconTone: "neutral",
  },
};

export const DatabaseRequired: Story = {
  args: {
    title: "Research needs a corpus database",
    description:
      "Create a vector collection from your loaded works, then return here to ask evidence-grounded questions.",
    actionLabel: "Create a collection",
    icon: "database",
  },
};
export const DatabaseRequiredWithoutAccess: Story = {
  args: {
    title: "Research needs a corpus database",
    description: "Ask an administrator to configure a corpus database or grant you access.",
    actionLabel: "",
    icon: "database",
  },
};
