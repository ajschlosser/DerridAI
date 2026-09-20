/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordsWorkspaceHeader from "./RecordsWorkspaceHeader.vue";

const meta = {
  title: "Records/Workspace Header",
  component: RecordsWorkspaceHeader,
  args: {
    fileName: "ear-of-the-other_corpus-subset-primary.jsonl",
    matched: 206,
    total: 206,
    flagged: 0,
    selected: 3,
  },
} satisfies Meta<typeof RecordsWorkspaceHeader>;
export default meta;
type Story = StoryObj<typeof RecordsWorkspaceHeader>;
export const Default: Story = {};
export const Empty: Story = {args: {fileName: "", matched: 0, total: 0, flagged: 0, selected: 0}};
