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

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const authApi = vi.hoisted(() => ({
  listUsers: vi.fn(),
  listRoles: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
}));
vi.mock("../../src/api/auth", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/auth")>("../../src/api/auth");
  return { ...actual, authApi };
});

import UsersView from "../../src/views/UsersView.vue";
import { queryClient } from "../../src/realtime/dataQuery";
import { dataKey } from "../../src/realtime/resourceKeys";

const user = (id: number, username: string) => ({
  id,
  username,
  role: "researcher",
  active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  last_login: null,
  login_count: 0,
});
const roles = [
  { id: "admin", name: "Administrator", description: "", locked: true, builtin: true },
  { id: "researcher", name: "Researcher", description: "", locked: false, builtin: true },
];

async function mountView() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/users", component: UsersView }],
  });
  await router.push("/users");
  await router.isReady();
  const wrapper = mount(UsersView, {
    attachTo: document.body,
    global: { plugins: [pinia, router, [VueQueryPlugin, { queryClient }]] },
  });
  await flushPromises();
  return wrapper;
}

describe("UsersView server state", () => {
  beforeEach(() => {
    queryClient.clear();
    authApi.listUsers.mockReset().mockResolvedValue({ users: [user(1, "root")] });
    authApi.listRoles.mockReset().mockResolvedValue({ roles, capabilities: [] });
  });

  it("shows new data when its resource is invalidated, without any manual reload", async () => {
    const wrapper = await mountView();
    expect(wrapper.text()).toContain("root");
    expect(wrapper.text()).not.toContain("ann");

    authApi.listUsers.mockResolvedValue({ users: [user(1, "root"), user(2, "ann")] });
    // This is exactly what the data bridge does for a `resource.changed` event.
    await queryClient.invalidateQueries({ queryKey: dataKey("users") });
    await flushPromises();

    expect(wrapper.text()).toContain("ann");
    wrapper.unmount();
  });

  it("reflects a local change immediately and keeps the list consistent with the server", async () => {
    authApi.createUser.mockResolvedValue({ user: user(2, "ann") });
    const wrapper = await mountView();
    await wrapper.find("#new-username").setValue("ann");
    await wrapper.find("#new-user-password").setValue("secret-pass");
    await wrapper.find("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("ann");
    wrapper.unmount();
  });
});
