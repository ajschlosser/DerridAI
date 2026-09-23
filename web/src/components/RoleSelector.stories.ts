/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RoleSelector from "./RoleSelector.vue";

const meta = {
  title: "System/Role Selector",
  component: RoleSelector,
  args: {
    label: "Roles",
    modelValue: "researcher",
    choices: [
      { id: "admin", name: "Administrator", kind: "Superuser", assigned: "1 account" },
      { id: "researcher", name: "Researcher", kind: "Default role", assigned: "4 accounts" },
      { id: "reviewer", name: "Reviewer", kind: "Custom role", assigned: "2 accounts" },
    ],
  },
} satisfies Meta<typeof RoleSelector>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Loading: Story = { args: { disabled: true } };
