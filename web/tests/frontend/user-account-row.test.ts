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

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it } from "vitest";
import UserAccountRow from "../../src/components/UserAccountRow.vue";
import type { AuthUser, RoleDefinition } from "../../src/api/auth";

const roles: RoleDefinition[] = [
  {
    id: "admin",
    name: "Administrator",
    description: "Full access",
    locked: true,
    builtin: true,
    permissions: ["*"],
  },
  {
    id: "researcher",
    name: "Researcher",
    description: "Research",
    locked: false,
    builtin: true,
    permissions: [],
  },
];
const user: AuthUser = {
  id: 2,
  username: "ada",
  role: "researcher",
  active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  login_count: 1,
  capabilities: [],
};

describe("UserAccountRow", () => {
  it("gives repeated account actions distinct accessible names", () => {
    setActivePinia(createPinia());
    const wrapper = mount(UserAccountRow, { props: { user, roles } });
    expect(wrapper.get('select[aria-label="Role for ada"]')).toBeTruthy();
    expect(wrapper.get('button[aria-label="Reset password for ada"]')).toBeTruthy();
    expect(wrapper.get('button[aria-label="Disable ada"]')).toBeTruthy();
    expect(wrapper.get('button[aria-label="Delete ada"]')).toBeTruthy();
    expect(wrapper.get(".user-avatar").attributes("aria-hidden")).toBe("true");
  });

  it("prevents changes to the current administrator account", () => {
    setActivePinia(createPinia());
    const wrapper = mount(UserAccountRow, {
      props: { user: { ...user, id: 1 }, roles, currentUserId: 1 },
    });
    expect(wrapper.get("select").attributes("disabled")).toBeDefined();
    expect(wrapper.get('button[aria-label="Disable ada"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('button[aria-label="Delete ada"]').attributes("disabled")).toBeDefined();
  });
});
