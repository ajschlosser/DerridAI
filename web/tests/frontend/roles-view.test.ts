/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const notifications = vi.hoisted(() => ({
  notify: vi.fn(),
}));
vi.mock("../../src/composables/notifications", () => ({ ...notifications }));

const authApi = vi.hoisted(() => ({
  listRoles: vi.fn(),
  listUsers: vi.fn(),
  createRole: vi.fn(),
  updateRolePermissions: vi.fn(),
  deleteRole: vi.fn(),
}));
vi.mock("../../src/api/auth", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/auth")>("../../src/api/auth");
  return { ...actual, authApi };
});

import RolesView from "../../src/views/RolesView.vue";
import { useAuthStore } from "../../src/stores/auth";
import { useI18nStore } from "../../src/stores/i18n";

const capabilities = [
  {
    id: "page.dashboard",
    category: "Pages",
    label: "Dashboard",
    description: "Open the dashboard.",
    configurable: true,
  },
  {
    id: "page.research",
    category: "Pages",
    label: "Research",
    description: "Open Research.",
    configurable: true,
  },
  {
    id: "users.manage",
    category: "Administration",
    label: "Manage users",
    description: "Administrator-only.",
    configurable: false,
  },
];
const roles = [
  {
    id: "admin",
    name: "Administrator",
    description: "Full access.",
    locked: true,
    builtin: true,
    permissions: ["*"],
  },
  {
    id: "researcher",
    name: "Researcher",
    description: "Default non-admin.",
    locked: false,
    builtin: true,
    permissions: ["page.dashboard", "page.research"],
  },
  {
    id: "reviewer",
    name: "Reviewer",
    description: "Custom review role.",
    locked: false,
    builtin: false,
    permissions: ["page.dashboard"],
  },
];

async function mountView(translations: Record<string, string> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  useAuthStore().user = { id: 1, username: "admin", role: "admin", capabilities: [] } as never;
  useI18nStore().dictionary = translations;
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/roles", name: "roles", component: RolesView },
      { path: "/users", name: "users", component: { template: "<div>users</div>" } },
    ],
  });
  await router.push("/roles");
  await router.isReady();
  const wrapper = mount(
    { template: "<RouterView />" },
    { attachTo: document.body, global: { plugins: [pinia, router] } },
  );
  await flushPromises();
  return { wrapper, router };
}

describe("RolesView", () => {
  beforeEach(() => {
    notifications.notify.mockClear();
    authApi.listRoles.mockResolvedValue({ roles, capabilities });
    authApi.listUsers.mockResolvedValue({
      users: [
        {
          id: 1,
          username: "admin",
          role: "admin",
          active: true,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          login_count: 1,
          capabilities: [],
        },
        {
          id: 2,
          username: "ada",
          role: "reviewer",
          active: true,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          login_count: 1,
          capabilities: [],
        },
      ],
    });
    authApi.updateRolePermissions.mockImplementation(
      async (_role: string, permissions: string[]) => ({
        role: "researcher",
        permissions,
        roles: roles.map((item) => (item.id === "researcher" ? { ...item, permissions } : item)),
        capabilities,
      }),
    );
    authApi.createRole.mockResolvedValue({
      role: {
        id: "editor",
        name: "Editor",
        description: "",
        locked: false,
        builtin: false,
        permissions: ["page.dashboard"],
      },
      roles: [
        ...roles,
        {
          id: "editor",
          name: "Editor",
          description: "",
          locked: false,
          builtin: false,
          permissions: ["page.dashboard"],
        },
      ],
      capabilities,
    });
    authApi.deleteRole.mockResolvedValue({
      deleted: "reviewer",
      roles: roles.filter((item) => item.id !== "reviewer"),
      capabilities,
    });
  });

  it("localizes built-in role descriptions", async () => {
    const { wrapper } = await mountView({
      "roles.admin_description": "Accès administratif entièrement localisé.",
    });
    await wrapper
      .findAll(".role-selector button")
      .find((button) => button.text().includes("Administrator"))
      ?.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Accès administratif entièrement localisé.");
    expect(wrapper.text()).not.toContain("Full access.");
  });

  it("shows the administrator role as locked full access with every capability checked", async () => {
    const { wrapper } = await mountView();
    const admin = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Administrator"));
    await admin?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Full access");
    expect(wrapper.text()).toContain("Administrator access is fixed");
    const checked = wrapper
      .findAll("input[type=checkbox]")
      .filter((input) => (input.element as HTMLInputElement).checked);
    expect(checked).toHaveLength(capabilities.length);
    expect(
      wrapper
        .findAll("input[type=checkbox]")
        .every((input) => input.attributes("disabled") !== undefined),
    ).toBe(true);
  });

  it("saves only after a permission change and records the dirty state", async () => {
    const { wrapper } = await mountView();
    expect(wrapper.text()).toContain("Saved");
    const save = wrapper.findAll("button").find((button) => button.text() === "Save");
    expect(save?.attributes("disabled")).toBeDefined();
    const research = wrapper.findAll("input[type=checkbox]")[1];
    await research?.setValue(false);
    await flushPromises();
    expect(wrapper.text()).toContain("Unsaved changes");
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "Save")
      ?.trigger("click");
    await flushPromises();
    expect(authApi.updateRolePermissions).toHaveBeenCalledWith("researcher", ["page.dashboard"]);
    expect(notifications.notify).toHaveBeenCalled();
  });

  it("creates a role from the dialog and selects it", async () => {
    const { wrapper } = await mountView();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("Create role"))
      ?.trigger("click");
    await flushPromises();
    const name = document.querySelector<HTMLInputElement>("#newRoleName");
    expect(name).toBeTruthy();
    name!.value = "Editor";
    name!.dispatchEvent(new Event("input", { bubbles: true }));
    await flushPromises();
    const submit = [...document.querySelectorAll("button")]
      .filter(
        (button) =>
          (button.textContent || "").includes("Create role") &&
          !(button as HTMLButtonElement).disabled,
      )
      .at(-1);
    submit?.click();
    await flushPromises();
    expect(authApi.createRole).toHaveBeenCalled();
    expect(wrapper.text()).toContain("Editor");
  });

  it("refuses to delete a custom role that still has assigned users", async () => {
    const { wrapper } = await mountView();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("Reviewer"))
      ?.trigger("click");
    await flushPromises();
    const remove = wrapper.findAll("button").find((button) => button.text() === "Delete role");
    expect(remove?.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("1 account uses this role");
  });

  it("keeps role actions locked when account assignments could not be loaded", async () => {
    authApi.listUsers.mockRejectedValueOnce(new Error("Account list unavailable"));
    const { wrapper } = await mountView();
    expect(wrapper.text()).toContain("The request could not be completed. Try again.");
    expect(wrapper.text()).not.toContain("Account list unavailable");
    const create = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Create role"));
    expect(create?.attributes("disabled")).toBeDefined();
    expect(
      wrapper
        .findAll(".role-selector button")
        .every((button) => button.attributes("disabled") !== undefined),
    ).toBe(true);
    expect(
      wrapper
        .findAll("input[type=checkbox]")
        .every((input) => input.attributes("disabled") !== undefined),
    ).toBe(true);
  });
});
