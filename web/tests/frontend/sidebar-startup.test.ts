import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

// The runtime's bootstrap (IndexedDB restore, provider fetch, health, jobs) can take seconds.
// Navigation must be complete from the moment a user signs in, not after that finishes.
const NAV = [
  ["home", "Home", "Overview"],
  ["global", "Search", "Research"],
  ["rag", "Research", "Research"],
  ["faq", "Response Library", "Research"],
  ["works", "Works", "Corpora"],
  ["list", "Records", "Corpora"],
  ["record", "Record View", "Corpora"],
  ["annotations", "Annotations", "Corpora"],
  ["compare", "Compare", "Corpora"],
  ["vector", "Corpus Data", "Corpora"],
  ["pdf", "Corpus Builder", "Build"],
  ["responsecache", "System Data", "System"],
  ["providers", "LLM Providers", "System"],
  ["schemas", "Metadata schemas", "System"],
  ["config", "Settings", "System"],
].map(([id, label, section]) => ({ id, label, icon: "record", section }));

const runtime = vi.hoisted(() => ({
  getNavItems: vi.fn(),
  getShellSnapshot: vi.fn(),
  bootstrapRuntime: vi.fn(),
  setUserContext: vi.fn(),
  setShellRefreshHook: vi.fn(),
  setUrlSyncHook: vi.fn(),
  pauseRuntime: vi.fn(),
  navigateView: vi.fn(),
  triggerBack: vi.fn(),
  triggerForward: vi.fn(),
  toggleSidebar: vi.fn(),
  state: {},
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
        path: "/system-data/pipelines",
        name: "system-data-pipelines",
        component: page,
        meta: {
          navId: "responsecache",
          navSection: "System",
          titleKey: "pipelines.title",
          titleFallback: "Pipeline Studio",
          breadcrumbParentKey: "runtime.system_data",
          breadcrumbParentFallback: "System Data",
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
  wrapper.findAll(".shell-nav-row .nav-tooltip-wrap > button");
const pageLabels = (wrapper: ReturnType<typeof mount>) => pageButtons(wrapper).map((b) => b.text());

describe("sidebar at sign-in", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    runtime.getNavItems.mockReturnValue(NAV);
    runtime.getShellSnapshot.mockReturnValue({});
    runtime.bootstrapRuntime.mockReturnValue(new Promise(() => {})); // never finishes
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
        "System Data",
        "LLM Providers",
        "Settings",
        "Users & roles",
        "Roles & permissions",
        "Manage languages",
        "Metadata memory",
        "Operations",
      ]),
    );
    expect(labels).not.toContain("Record View");

    const headings = wrapper.findAll(".shell-nav-section h2").map((node) => node.text());
    expect(headings).toEqual(expect.arrayContaining(["Research", "Corpora", "Build", "System"]));
    const compare = pageButtons(wrapper).find((button) => button.text() === "Compare");
    expect(compare?.element.closest(".shell-nav-section")?.querySelector("h2")?.textContent).toBe(
      "Corpora",
    );
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

  it("renders route-aware clickable breadcrumbs for nested workspaces", async () => {
    const { wrapper, router } = await signIn("admin");
    await router.push("/system-data/pipelines");
    await flushPromises();

    const crumbs = wrapper.find(".vue-breadcrumb-path");
    expect(crumbs.text()).toContain("DerridAI");
    expect(crumbs.text()).toContain("System");
    expect(crumbs.text()).toContain("System Data");
    expect(crumbs.text()).toContain("Pipeline Studio");

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
    expect(pageButtons(wrapper).find((button) => button.text() === "System Data")?.attributes("aria-current")).toBe(
      "page",
    );
  });

  it("filters navigation without hiding its information architecture", async () => {
    const { wrapper } = await signIn("admin");
    const input = wrapper.get(".shell-nav-search input");
    await input.setValue("compare");

    expect(pageLabels(wrapper)).toContain("Compare");
    expect(pageLabels(wrapper)).not.toContain("Corpus Builder");
    expect(wrapper.findAll(".shell-nav-section h2").map((node) => node.text())).toContain("Corpora");
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
