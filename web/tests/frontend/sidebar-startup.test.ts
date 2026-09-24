import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

// The runtime's bootstrap (IndexedDB restore, provider fetch, health, jobs) can take seconds.
// The sidebar must be complete from the moment a user signs in, not after that finishes.
const NAV = [
  ["home", "Home", "Overview"], ["global", "Search", "Corpus"], ["works", "Works", "Corpus"],
  ["record", "Record View", "Corpus"], ["rag", "Research", "Research"], ["annotations", "Annotations", "Corpus"],
  ["config", "Settings", "System"], ["list", "Records", "Corpus"], ["pdf", "Corpus Builder", "Tools"],
  ["compare", "Compare", "Tools"], ["vector", "Vector Stores", "Storage"], ["faq", "Response Library", "Research"],
  ["providers", "LLM Providers", "System"],
].map(([id, label, section]) => ({ id, label, icon: "record", section }));

const runtime = vi.hoisted(() => ({
  getNavItems: vi.fn(),
  getShellSnapshot: vi.fn(),
  bootstrapRuntime: vi.fn(),
  setUserContext: vi.fn(),
  setShellRefreshHook: vi.fn(),
  setUrlSyncHook: vi.fn(),
  pauseRuntime: vi.fn(),
  triggerOperations: vi.fn(),
  navigateView: vi.fn(),
  state: {},
}));
vi.mock("../../src/runtime/runtime.js", () => ({ ...runtime, __v_isRef: false, __v_isReadonly: false, __v_isShallow: false, __v_skip: true, __v_raw: undefined }));

import App from "../../src/App.vue";
import { useAuthStore } from "../../src/stores/auth";
import { useI18nStore } from "../../src/stores/i18n";
import { useShellStore } from "../../src/stores/shell";

async function signIn(role: "admin" | "researcher" = "admin") {
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  const i18n = useI18nStore();
  i18n.languages = [{ code: "en-US", name: "English", flag: "🇺🇸" }] as never;
  auth.initialized = true;
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/:rest(.*)*", component: { template: "<div/>" } }] });
  await router.push("/");
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [pinia, router], stubs: { RouterView: true } } });
  auth.user = { id: 1, username: "u", role, capabilities: role === "admin" ? [] : ["page.research", "page.search"] } as never;
  await flushPromises();
  return { wrapper, auth, shell: useShellStore() };
}

const sidebarLabels = (wrapper: ReturnType<typeof mount>) => ({
  primary: wrapper.findAll(".shell-primary-nav button").map(b => b.text()),
  more: wrapper.findAll(".shell-more-tools-list button").map(b => b.text()),
});

describe("sidebar at sign-in", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    runtime.getNavItems.mockReturnValue(NAV);
    runtime.getShellSnapshot.mockReturnValue({});
    runtime.bootstrapRuntime.mockReturnValue(new Promise(() => {})); // never finishes
  });

  it("is complete before the runtime bootstrap finishes, with no Operations click", async () => {
    const { wrapper, shell } = await signIn();

    expect(runtime.bootstrapRuntime).toHaveBeenCalled();
    expect(shell.ready).toBe(false);
    const { primary, more } = sidebarLabels(wrapper);
    expect(primary).toContain("Home");
    expect(primary).toContain("Research");
    expect(more).toEqual(expect.arrayContaining(["Records", "Corpus Builder", "Compare", "Vector Stores", "Response Library", "LLM Providers"]));
    expect(more).toEqual(expect.arrayContaining(["Users & roles", "Roles & permissions", "Manage languages", "Metadata memory"]));
  });

  it("forgets the menu on sign-out so the next user never sees a stale or partial one", async () => {
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
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/:rest(.*)*", component: { template: "<div/>" } }] });
    await router.push("/");
    await router.isReady();
    const wrapper = mount(App, { global: { plugins: [pinia, router], stubs: { RouterView: true } } });
    await flushPromises();
    expect(sidebarLabels(wrapper).more).toContain("Corpus Builder");
    expect(runtime.bootstrapRuntime).toHaveBeenCalled();
  });

  it("opens More tools by default for administrators", async () => {
    const { wrapper } = await signIn("admin");
    expect((wrapper.get(".shell-more-tools").element as HTMLDetailsElement).open).toBe(true);
  });

  it("remembers a user's choice to close More tools", async () => {
    const first = await signIn("admin");
    const details = first.wrapper.get(".shell-more-tools").element as HTMLDetailsElement;
    details.open = false;
    await first.wrapper.get(".shell-more-tools").trigger("toggle");
    expect(localStorage.getItem("derridai.ui.moreToolsOpen")).toBe("0");

    const second = await signIn("admin");
    expect((second.wrapper.get(".shell-more-tools").element as HTMLDetailsElement).open).toBe(false);
  });

  it("does not store a preference when the menu opens by default", async () => {
    await signIn("admin");
    expect(localStorage.getItem("derridai.ui.moreToolsOpen")).toBeNull();
  });

  it("marks the active nav item for assistive tech and gives every item an accessible name", async () => {
    const { wrapper } = await signIn();
    const buttons = wrapper.findAll(".shell-primary-nav button");
    const home = buttons.find(b => b.text() === "Home");
    const research = buttons.find(b => b.text() === "Research");
    expect(home?.attributes("aria-current")).toBe("page");
    expect(research?.attributes("aria-current")).toBeUndefined();
    for (const button of buttons) expect(button.attributes("aria-label")).toBe(button.text());
  });

  it("keeps the collapse toggle and more-tools disclosure operable by assistive tech", async () => {
    const { wrapper } = await signIn();
    const toggle = wrapper.get(".sidebar-toggle");
    expect(toggle.attributes("aria-label")).toBeTruthy();
    expect(toggle.attributes("aria-pressed")).toBe("false");
    const summary = wrapper.get(".shell-more-tools summary");
    expect(summary.attributes("aria-expanded")).toBe("true");
  });
});
