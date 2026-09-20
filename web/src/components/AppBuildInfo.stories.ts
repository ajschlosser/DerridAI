// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import AppBuildInfo from "./AppBuildInfo.vue";

const meta = {
  title: "Foundations/Brand/Build Info",
  component: AppBuildInfo,
  parameters: {layout: "centered"},
  args: {showCopyright: true, showCommit: true, compact: false, landmark: false},
} satisfies Meta<typeof AppBuildInfo>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Compact: Story = {args: {compact: true, showCommit: false}};
export const VersionOnly: Story = {args: {showCopyright: false, showCommit: false}};
