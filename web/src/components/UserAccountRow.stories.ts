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
