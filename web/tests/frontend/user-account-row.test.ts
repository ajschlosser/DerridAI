/* Copyright 2026 Aaron John Schlosser, PhD. */
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
