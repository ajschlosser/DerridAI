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
import { useAuthStore } from "../../src/stores/auth";

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
    queryClient.setDefaultOptions({ queries: { retry: false, staleTime: 30_000 } });
    authApi.listUsers.mockReset().mockResolvedValue({ users: [user(1, "root")] });
    authApi.listRoles.mockReset().mockResolvedValue({ roles, capabilities: [] });
  });

  it("shows loaded accounts while roles are pending and keeps mutations locked", async () => {
    let finish!: (value: { roles: typeof roles; capabilities: never[] }) => void;
    authApi.listRoles.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    const wrapper = await mountView();
    expect(wrapper.find(".user-list").text()).toContain("root");
    expect(wrapper.find("#new-username").attributes("disabled")).toBeDefined();
    finish({ roles, capabilities: [] });
    await flushPromises();
    expect(wrapper.find("#new-username").attributes("disabled")).toBeUndefined();
    wrapper.unmount();
  });

  it("withholds account counts before the first account read succeeds", async () => {
    authApi.listUsers.mockReturnValue(new Promise(() => {}));
    const wrapper = await mountView();
    expect(wrapper.text()).not.toContain("0 configured accounts");
    expect(wrapper.find(".users-loading").exists()).toBe(true);
    wrapper.unmount();
  });

  it("retains account DOM and draft on failed refresh and retries only accounts", async () => {
    const wrapper = await mountView();
    const row = wrapper.find(".user-row").element;
    await wrapper.find("#new-username").setValue("draft");
    authApi.listUsers.mockRejectedValueOnce(new Error("offline"));
    await queryClient.invalidateQueries({ queryKey: dataKey("users", "anonymous", "") });
    await flushPromises();
    expect(wrapper.find(".user-row").element).toBe(row);
    expect(wrapper.text()).toContain("The refresh failed. Previously loaded content is shown.");
    const retry = wrapper
      .find(".users-table-card")
      .findAll("button")
      .find((b) => b.text() === "Retry");
    expect(retry).toBeDefined();
    await retry!.trigger("click");
    await flushPromises();
    expect(authApi.listRoles).toHaveBeenCalledTimes(1);
    expect(wrapper.find(".user-row").element).toBe(row);
    expect((wrapper.find("#new-username").element as HTMLInputElement).value).toBe("draft");
    wrapper.unmount();
  });

  it("clears displayed accounts when the account refresh is forbidden", async () => {
    const wrapper = await mountView();
    authApi.listUsers.mockRejectedValue(Object.assign(new Error("forbidden"), { status: 403 }));
    await queryClient.invalidateQueries({ queryKey: dataKey("users", "anonymous", "") });
    await flushPromises();
    expect(wrapper.find(".user-row").exists()).toBe(false);
    wrapper.unmount();
  });

  it("does not show cached accounts from a different signed-in scope", async () => {
    const wrapper = await mountView();
    authApi.listUsers.mockReturnValue(new Promise(() => {}));
    useAuthStore().user = { id: 2, username: "second", role: "admin", capabilities: [] } as never;
    await flushPromises();
    expect(wrapper.find(".user-row").exists()).toBe(false);
    expect(wrapper.find(".users-loading").exists()).toBe(true);
    wrapper.unmount();
  });

  it("shows new data when its resource is invalidated, without any manual reload", async () => {
    const wrapper = await mountView();
    expect(wrapper.text()).toContain("root");
    expect(wrapper.text()).not.toContain("ann");

    authApi.listUsers.mockResolvedValue({ users: [user(1, "root"), user(2, "ann")] });
    // This is exactly what the data bridge does for a `resource.changed` event.
    await queryClient.invalidateQueries({ queryKey: dataKey("users", "anonymous", "") });
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
