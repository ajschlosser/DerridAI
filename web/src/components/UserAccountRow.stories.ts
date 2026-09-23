/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import UserAccountRow from "./UserAccountRow.vue";
import type { AuthUser, RoleDefinition } from "../api/auth";

const roles: RoleDefinition[] = [
  {
    id: "admin",
    name: "Administrator",
    description: "Full application access.",
    locked: true,
    builtin: true,
    permissions: ["*"],
  },
  {
    id: "researcher",
    name: "Researcher",
    description: "Research access.",
    locked: false,
    builtin: true,
    permissions: ["page.dashboard"],
  },
  {
    id: "reviewer",
    name: "Reviewer",
    description: "Custom role.",
    locked: false,
    builtin: false,
    permissions: ["page.dashboard"],
  },
];

const user: AuthUser = {
  id: 12,
  username: "ada.researcher",
  role: "researcher",
  active: true,
  created_at: "2026-01-12T09:30:00Z",
  updated_at: "2026-01-12T09:30:00Z",
  last_login: "2026-05-20T16:10:00Z",
  login_count: 18,
  capabilities: ["page.dashboard"],
};

const meta = {
  title: "System/User Account Row",
  component: UserAccountRow,
  args: { user, roles, currentUserId: 1, disabled: false },
} satisfies Meta<typeof UserAccountRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ActiveResearcher: Story = {};
export const DisabledAccount: Story = {
  args: { user: { ...user, active: false }, disabled: false },
};
export const CurrentAdministrator: Story = {
  args: {
    user: { ...user, id: 1, username: "admin", role: "admin" },
    currentUserId: 1,
  },
};
