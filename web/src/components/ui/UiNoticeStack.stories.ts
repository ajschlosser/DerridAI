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
import UiNoticeStack from "./UiNoticeStack.vue";

const meta = {
  title: "UI/Notice Stack",
  component: UiNoticeStack,
  args: {
    label: "Messages",
    items: [{ id: "one", tone: "info", text: "The source was added: 2,509 units." }],
  },
} satisfies Meta<typeof UiNoticeStack>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Single: Story = {};

export const EveryTone: Story = {
  args: {
    items: [
      { id: "e", tone: "error", text: "The provider refused the request (HTTP 401)." },
      { id: "w", tone: "warning", text: "2 of 6 records (33.3%) appear unusable." },
      { id: "i", tone: "info", text: "Metadata enrichment continued without the text touch-up." },
      { id: "s", tone: "success", text: "Record accepted. Moving to the next record." },
    ],
  },
};

export const ProvenanceWarnings: Story = {
  args: {
    label: "Build warnings",
    mode: "acknowledge",
    limit: 3,
    items: Array.from({ length: 6 }, (_, n) => ({
      id: `w${n}`,
      tone: "warning" as const,
      text: `cosmopolitanism-0000${n + 1}: LLM text touch-up failed; metadata enrichment continued.`,
    })),
  },
};
