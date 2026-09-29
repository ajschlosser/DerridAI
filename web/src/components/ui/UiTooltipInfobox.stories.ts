// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UiTooltipInfobox from "./UiTooltipInfobox.vue";

const meta = {
  title: "UI/Tooltip infobox",
  component: UiTooltipInfobox,
  args: {
    title: "Rerank candidates",
    description: "Stage details remain available while you inspect the diagram.",
    rows: [
      { label: "Status", value: "Completed" },
      { label: "In → out", value: "8 → 2" },
      { label: "Duration", value: "240 ms" },
    ],
  },
} satisfies Meta<typeof UiTooltipInfobox>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
