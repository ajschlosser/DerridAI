/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CompareDiff from "./CompareDiff.vue";
import { buildCompareRows } from "../../domain/compare";

const rows = buildCompareRows(
  { record_id: "r-a", work: "Glas", text: "the gift of death" },
  { record_id: "r-a", work: "Glas", text: "the gift of life" },
  "changed",
).map((row) => ({ ...row, label: row.key === "text" ? "Text" : row.key }));

const meta = {
  title: "Compare/Diff",
  component: CompareDiff,
  args: {
    rows,
    emptyLabel: "These records are identical across all compared fields.",
    changedLabel: "Changed",
    identicalLabel: "Identical",
    sideA: "Record A",
    sideB: "Record B",
  },
} satisfies Meta<typeof CompareDiff>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Changed: Story = {};
export const Identical: Story = { args: { rows: [] } };
