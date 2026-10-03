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
import { useLayoutStore } from "../../src/stores/workspace";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

// The runtime's bootstrap (IndexedDB restore, provider fetch, health, jobs) can take seconds.
// Navigation must be complete from the moment a user signs in, not after that finishes.
const NAV = [
  ["home", "Home", "Overview"],
  ["rag", "Research", "Research"],
  ["faq", "Response Library", "Research"],
  ["global", "Search", "Corpora"],
  ["works", "Works", "Corpora"],
  ["list", "Records", "Corpora"],
  ["record", "Record View", "Corpora"],
  ["annotations", "Annotations", "Corpora"],
  ["compare", "Compare", "Corpora"],
  ["pdf", "Corpus Builder", "Corpus Management"],
  ["vector", "Corpus Data", "Corpus Management"],
  ["schemas", "Metadata schemas", "Corpus Management"],
  ["providers", "LLM Providers", "AI & Automation"],
  ["responsecache", "System Data", "System"],
  ["config", "Settings", "System"],
].map(([id, label, section]) => ({ id, label, icon: "record", section }));

const navigation = vi.hoisted(() => ({ navigateTo: vi.fn() }));
vi.mock("../../src/domain/sharedNavigation", () => navigation);

const runtime = vi.hoisted(() => ({
  getNavItems: vi.fn(),
  getShellSnapshot: vi.fn(),
  bootstrapRuntime: vi.fn(),
  setUserContext: vi.fn(),
  setShellRefreshHook: vi.fn(),
  setUrlSyncHook: vi.fn(),
  pauseRuntime: vi.fn(),
  syncFromLocation: vi.fn(),
  repaintAfterLocationChange: vi.fn(),
  viewForPath: vi.fn(),
  toggleSidebar: vi.fn(),
  state: {} as Record<string, unknown>,
}));
vi.mock("../../src/runtime/runtime.js", () => ({
  ...runtime,
  __v_isRef: false,
  __v_isReadonly: false,
  __v_isShallow: false,
  __v_skip: true,
  __v_raw: undefined,
}));

import App from "../../src/App.vue";
import { useAuthStore } from "../../src/stores/auth";
import { useI18nStore } from "../../src/stores/i18n";
import { useShellStore } from "../../src/stores/shell";
import { requestCorpusFiles } from "../../src/services/corpusFiles";

function testRouter() {
  const page = { template: "<div/>" };
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/",
        name: "home",
        component: page,
        meta: {
          navId: "home",
          navSection: "Overview",
          titleKey: "nav.home",
          titleFallback: "Home",
        },
      },
      {
        path: "/search",
        name: "global",
        component: page,
        meta: {
          navId: "global",
          navSection: "Corpora",
          titleKey: "nav.search",
          titleFallback: "Search",
        },
      },
      {
        path: "/system-data/overview",
        name: "system-data-overview",
        component: page,
        meta: {
          navId: "responsecache",
          navSection: "System",
          titleKey: "runtime.system_overview",
          titleFallback: "Overview",
          breadcrumbParentKey: "runtime.system_data",
          breadcrumbParentFallback: "System Data",
        },
      },
      {
        path: "/system-data/databases",
        name: "system-data-databases",
        component: page,
        meta: {
          navId: "responsecache",
          navSection: "System",
          titleKey: "runtime.system_databases",
          titleFallback: "Databases",
          breadcrumbParentKey: "runtime.system_data",
          breadcrumbParentFallback: "System Data",
        },
      },
      {
        path: "/pipelines",
        name: "pipelines",
        component: page,
        meta: {
          navId: "pipelines",
          navSection: "AI & Automation",
          titleKey: "pipelines.title",
          titleFallback: "Pipeline Studio",
        },
      },
      {
        path: "/settings/:section",
        name: "settings-section",
        component: page,
        meta: {
          navId: "config",
          navSection: "System",
          titleKey: "nav.config",
          titleFallback: "Settings",
        },
      },
      { path: "/:rest(.*)*", component: page },
    ],
  });
}

async function signIn(role: "admin" | "researcher" = "admin") {
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  const i18n = useI18nStore();
  i18n.languages = [{ code: "en-US", name: "English", flag: "🇺🇸" }] as never;
  auth.initialized = true;
  const router = testRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [pinia, router], stubs: { RouterView: true } } });
  auth.user = {
    id: 1,
    username: "u",
    role,
    capabilities: role === "admin" ? [] : ["page.research", "page.search"],
  } as never;
  await flushPromises();
  return { wrapper, auth, shell: useShellStore(), router };
}

const pageButtons = (wrapper: ReturnType<typeof mount>) =>
  wrapper.findAll(".shell-sidebar .nav-tooltip-wrap > button");
const pageLabels = (wrapper: ReturnType<typeof mount>) => pageButtons(wrapper).map((b) => b.text());

describe("sidebar at sign-in", () => {
  beforeEach(() => {
    useLayoutStore().sidebarCollapsed = false;
    vi.clearAllMocks();
    localStorage.clear();
    runtime.getNavItems.mockReturnValue(NAV);
    runtime.getShellSnapshot.mockReturnValue({});
    runtime.bootstrapRuntime.mockReturnValue(new Promise(() => {})); // never finishes
  });

  it("opens the shared corpus picker through the explicit shell command", async () => {
    const { wrapper } = await signIn();
    const input = wrapper.get("#fileInput").element as HTMLInputElement;
    const click = vi.spyOn(input, "click").mockImplementation(() => undefined);

    requestCorpusFiles();

    expect(click).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("is complete and intent-grouped before the runtime bootstrap finishes", async () => {
    const { wrapper, shell } = await signIn();

    expect(runtime.bootstrapRuntime).toHaveBeenCalled();
    expect(shell.ready).toBe(false);
    const labels = pageLabels(wrapper);
    expect(labels).toEqual(
      expect.arrayContaining([
        "Home",
        "Search",
        "Research",
        "Works",
        "Records",
        "Compare",
        "Corpus Data",
        "Corpus Builder",
        "Metadata schemas",
        "LLM Providers",
        "Pipeline Studio",
        "Metadata memory",
        "System Data",
        "Users & roles",
        "Manage languages",
        "Operations",
        "Help center",
        "Settings",
      ]),
    );
    expect(labels).not.toContain("Record View");

    const headings = wrapper.findAll(".shell-nav-section h2").map((node) => node.text());
    expect(headings).toEqual(
      expect.arrayContaining([
        "Research",
        "Corpora",
        "Corpus Management",
        "AI & Automation",
        "System",
      ]),
    );
    const compare = pageButtons(wrapper).find((button) => button.text() === "Compare");
    expect(compare?.element.closest(".shell-nav-section")?.querySelector("h2")?.textContent).toBe(
      "Corpora",
    );
    expect(
      wrapper
        .findAll(".shell-navigation .nav-tooltip-wrap > button")
        .every((button) => !button.element.closest(".ui-tooltip")),
    ).toBe(true);

    useLayoutStore().sidebarCollapsed = true;
    await flushPromises();
    expect(wrapper.findAll(".shell-navigation .ui-tooltip-anchor")).not.toHaveLength(0);
  });

  it("forgets the menu on sign-out so the next user never sees stale navigation", async () => {
    const { auth, shell } = await signIn();
    expect(shell.navReady).toBe(true);
    auth.user = null;
    await flushPromises();
    expect(shell.navReady).toBe(false);
    expect(shell.snapshot.nav).toEqual([]);
  });

  it("recomputes the menu for a session that already exists at page load", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const auth = useAuthStore();
    useI18nStore().languages = [{ code: "en-US", name: "English", flag: "🇺🇸" }] as never;
    auth.initialized = true;
    auth.user = { id: 1, username: "u", role: "admin", capabilities: [] } as never;
    const router = testRouter();
    await router.push("/");
    await router.isReady();
    const wrapper = mount(App, {
      global: { plugins: [pinia, router], stubs: { RouterView: true } },
    });
    await flushPromises();
    expect(pageLabels(wrapper)).toContain("Corpus Builder");
    expect(runtime.bootstrapRuntime).toHaveBeenCalled();
  });

  it("renders route-aware clickable breadcrumbs for nested System Data workspaces", async () => {
    const { wrapper, router } = await signIn("admin");
    await router.push("/system-data/databases");
    await flushPromises();

    const crumbs = wrapper.find(".vue-breadcrumb-path");
    expect(crumbs.text()).toContain("DerridAI");
    expect(crumbs.text()).toContain("System");
    expect(crumbs.text()).toContain("System Data");
    expect(crumbs.text()).toContain("Databases");

    const links = crumbs.findAll("a").map((link) => ({
      text: link.text(),
      href: link.attributes("href"),
    }));
    expect(links).toEqual(
      expect.arrayContaining([
        { text: "DerridAI", href: "/" },
        { text: "System", href: "/system-data/overview" },
        { text: "System Data", href: "/system-data/overview" },
      ]),
    );
    expect(
      pageButtons(wrapper)
        .find((button) => button.text() === "System Data")
        ?.attributes("aria-current"),
    ).toBe("page");
  });

  it("treats Pipeline Studio as a first-class AI & Automation workspace", async () => {
    const { wrapper, router } = await signIn("admin");
    await router.push("/pipelines");
    await flushPromises();

    const crumbs = wrapper.find(".vue-breadcrumb-path");
    expect(crumbs.text()).toContain("DerridAI");
    expect(crumbs.text()).toContain("AI & Automation");
    expect(crumbs.text()).toContain("Pipeline Studio");
    expect(crumbs.text()).not.toContain("System Data");

    expect(
      pageButtons(wrapper)
        .find((button) => button.text() === "Pipeline Studio")
        ?.attributes("aria-current"),
    ).toBe("page");
    expect(
      wrapper
        .findAll(".shell-nav-group-toggle")
        .find((button) => button.text() === "AI & Automation")
        ?.attributes("aria-expanded"),
    ).toBe("true");
  });

  it("does not link breadcrumb items to the current workspace", async () => {
    const { wrapper, router } = await signIn("admin");
    await router.push("/system-data/overview");
    await flushPromises();

    const crumbs = wrapper.find(".vue-breadcrumb-path");
    expect(crumbs.text()).toContain("System");
    expect(crumbs.text()).toContain("System Data");
    expect(crumbs.text()).toContain("Overview");
    expect(crumbs.findAll("a").map((link) => link.text())).toEqual(["DerridAI"]);
  });

  it("places Settings breadcrumbs under System on direct loads", async () => {
    const { wrapper, router } = await signIn("admin");
    await router.push("/settings/preferences");
    await flushPromises();

    const crumbs = wrapper.find(".vue-breadcrumb-path");
    expect(crumbs.text()).toContain("System");
    expect(crumbs.text()).toContain("Settings");
    expect(crumbs.text()).toContain("Preferences");
    expect(crumbs.findAll("a").map((link) => link.text())).toEqual([
      "DerridAI",
      "System",
      "Settings",
    ]);
  });

  it("filters navigation without hiding its information architecture", async () => {
    const { wrapper } = await signIn("admin");
    const input = wrapper.get(".shell-nav-search input");
    await input.setValue("compare");

    expect(pageLabels(wrapper)).toContain("Compare");
    expect(pageLabels(wrapper)).not.toContain("Corpus Builder");
    expect(wrapper.findAll(".shell-nav-section h2").map((node) => node.text())).toContain(
      "Corpora",
    );
    await wrapper.get(".shell-nav-search-clear").trigger("click");
    expect((input.element as HTMLInputElement).value).toBe("");
    expect(pageLabels(wrapper)).toContain("Corpus Builder");
  });

  it("remembers collapsed groups while keeping the active group expanded", async () => {
    const { wrapper, router } = await signIn("admin");
    const groupToggle = (label: string) =>
      wrapper.findAll(".shell-nav-group-toggle").find((button) => button.text() === label);
    const corpora = groupToggle("Corpora");
    expect(corpora).toBeTruthy();
    expect(groupToggle("Research")?.attributes("aria-expanded")).toBe("true");
    expect(corpora?.attributes("aria-expanded")).toBe("true");
    expect(groupToggle("Corpus Management")?.attributes("aria-expanded")).toBe("false");
    expect(groupToggle("AI & Automation")?.attributes("aria-expanded")).toBe("false");
    expect(groupToggle("System")?.attributes("aria-expanded")).toBe("false");

    await corpora!.trigger("click");
    expect(corpora!.attributes("aria-expanded")).toBe("false");
    expect(
      JSON.parse(localStorage.getItem("derridai.ui.navigationCollapsedGroups") || "[]"),
    ).toContain("Corpora");

    await router.push("/search");
    await flushPromises();
    expect(corpora!.attributes("aria-expanded")).toBe("true");
  });

  it("persists favorites and recent destinations as optional navigation shortcuts", async () => {
    const { wrapper } = await signIn("admin");
    const compareRow = wrapper
      .findAll(".shell-nav-row")
      .find((row) => row.find(".nav-tooltip-wrap > button").text() === "Compare");
    expect(compareRow).toBeTruthy();

    await compareRow!.get(".shell-nav-favorite").trigger("click");
    expect(JSON.parse(localStorage.getItem("derridai.ui.navigationFavorites") || "[]")).toContain(
      "compare",
    );

    await compareRow!.get(".nav-tooltip-wrap > button").trigger("click");
    expect(JSON.parse(localStorage.getItem("derridai.ui.navigationRecents") || "[]")[0]).toBe(
      "compare",
    );
  });

  it("marks the route-active item for assistive tech and labels page controls", async () => {
    const { wrapper } = await signIn();
    const home = pageButtons(wrapper).find((button) => button.text() === "Home");
    const research = pageButtons(wrapper).find((button) => button.text() === "Research");
    expect(home?.attributes("aria-current")).toBe("page");
    expect(research?.attributes("aria-current")).toBeUndefined();
    for (const button of pageButtons(wrapper)) expect(button.attributes("aria-label")).toBeTruthy();
  });

  it("keeps the collapse toggle and navigation filter operable by assistive tech", async () => {
    const { wrapper } = await signIn();
    const toggle = wrapper.get(".sidebar-toggle");
    expect(toggle.attributes("aria-label")).toBeTruthy();
    expect(toggle.attributes("aria-pressed")).toBe("false");
    expect(wrapper.get(".shell-nav-search input").attributes("type")).toBe("search");
  });
});

describe("router and runtime stay in agreement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    runtime.getNavItems.mockReturnValue(NAV);
    runtime.getShellSnapshot.mockReturnValue({});
    runtime.bootstrapRuntime.mockReturnValue(new Promise(() => {}));
    runtime.viewForPath.mockReturnValue(undefined);
    delete runtime.state.view; // mutate in place: the App module holds the same object
  });

  type UrlSyncHook = (href: string, options: { replace?: boolean }) => void;
  const installedHook = () => runtime.setUrlSyncHook.mock.calls.at(-1)?.[0] as UrlSyncHook;

  it("resyncs the runtime from the router when a navigation it requested is refused", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { wrapper, router } = await signIn();
    router.beforeEach((to) => (to.path === "/search" ? false : true));

    installedHook()("/search", {});
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/");
    expect(runtime.syncFromLocation).toHaveBeenCalledTimes(1);
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
    wrapper.unmount();
  });

  it("does not resync when the requested navigation succeeds", async () => {
    const { wrapper, router } = await signIn();

    installedHook()("/search", {});
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/search");
    expect(runtime.syncFromLocation).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it("follows the router when a route change lands on a different runtime view", async () => {
    const { wrapper, router } = await signIn();
    runtime.state.view = "home";
    runtime.viewForPath.mockImplementation((path: string) =>
      path === "/search" ? "global" : "home",
    );

    await router.push("/search");
    expect(runtime.repaintAfterLocationChange).toHaveBeenCalledTimes(1);

    runtime.state.view = "global";
    await router.push("/search?q=again");
    expect(runtime.repaintAfterLocationChange).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("lets a sidebar click resync a runtime view that has drifted from the URL", async () => {
    const { wrapper } = await signIn();
    runtime.state.view = "global"; // runtime drifted; the URL is still "/"

    await pageButtons(wrapper)
      .find((b) => b.text() === "Home")
      ?.trigger("click");

    expect(navigation.navigateTo).toHaveBeenCalledWith("home", { href: "/" });
    wrapper.unmount();
  });

  it("ignores a click on the destination the runtime and router already agree on", async () => {
    const { wrapper } = await signIn();
    runtime.state.view = "home";

    await pageButtons(wrapper)
      .find((b) => b.text() === "Home")
      ?.trigger("click");

    expect(navigation.navigateTo).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
