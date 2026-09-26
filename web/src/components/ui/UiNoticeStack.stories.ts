/* Copyright 2026 Aaron John Schlosser, PhD. */
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
