/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import MixedValueInspect from "./MixedValueInspect.vue";

const meta = {
  title: "Works/Mixed Value Inspect",
  component: MixedValueInspect,
  args: {field: "publisher", fieldLabel: "Publisher", count: 3, compact: false},
} satisfies Meta<typeof MixedValueInspect>;
export default meta;
type Story = StoryObj<typeof MixedValueInspect>;
export const Default: Story = {};
export const Compact: Story = {args: {compact: true, count: 2}};
