/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

const runtime = vi.hoisted(() => ({
  persistPrefs: vi.fn(),
  flushWorkspacePrefs: vi.fn(async () => undefined),
  applyAppearance: vi.fn(),
  getProviderProfilesForUi: vi.fn(() => [{id: "p1", name: "Local", type: "ollama", model: "gemma", max_concurrent_requests: 1}]),
  getDefaultProviderProfileId: vi.fn(() => "p1"),
  navigateView: vi.fn(),
  toggleSidebar: vi.fn(),
  downloadFullBackup: vi.fn(),
  restoreFullBackup: vi.fn(),
  clearAllUpdates: vi.fn(),
  deleteAllDerridaiBrowserState: vi.fn(),
  backupContainsCredentials: vi.fn(() => false),
  getShellSnapshot: vi.fn(() => ({})),
  state: {
    storageReady: true,
    appConfig: {
      ui_color_theme: "green",
      ui_color_scheme: "system",
      ui_contrast: "system",
      default_provider_profile: "p1",
      default_review_preset: "text",
      default_llm_run_mode: "foreground",
      embedding_provider: "ollama",
      embedding_model: "bge-m3:latest",
      desktop_notifications: false,
    },
    ragConfig: {
      k: 64, fetch_k: 500, lambda_mult: 0.7, rrf_k: 60, rerank_top_n: 24, reranker: "cross_encoder",
      cross_encoder_model: "cross-encoder/ms-marco-MiniLM-L-6-v2", query_decomposition_num_predict: 768,
      response_language: "auto", evidence_record_char_limit: 12000, evidence_total_char_limit: 120000,
      locales: ["en", "fr"], search_types: ["similarity", "lexical", "mmr"], auto_grade: false,
    },
    health: {chroma: {path: "/data/chroma"}},
    providerStatuses: {p1: {available: true, checked_at: "2026-01-01T00:00:00Z"}},
    files: [],
    jobs: [],
    sidebarCollapsed: false,
    tableColumns: {},
    collapsedPanels: {},
    upsertIgnored: {},
  },
}));
vi.mock("../../src/runtime/runtime.js", () => ({...runtime, __v_isRef: false, __v_isReadonly: false, __v_isShallow: false, __v_skip: true, __v_raw: undefined}));

import SettingsView from "../../src/views/SettingsView.vue";
import { useAuthStore } from "../../src/stores/auth";
import { useI18nStore } from "../../src/stores/i18n";

async function mountView(role: "admin" | "researcher", query: Record<string, string> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  auth.user = {
    id: 1, username: "u", role,
    capabilities: role === "admin" ? [] : ["page.settings", "appearance.manage", "page.research", "page.dashboard"],
  } as never;
  const i18n = useI18nStore();
  i18n.languages = [{code: "en-US", name: "English", flag: "🇺🇸"}, {code: "fr-CA", name: "Français", flag: "🇨🇦"}] as never;
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {path: "/settings", name: "config", component: SettingsView},
      {path: "/", name: "home", component: {template: "<div>home</div>"}},
    ],
  });
  await router.push({path: "/settings", query});
  await router.isReady();
  const wrapper = mount({template: "<RouterView />"}, {attachTo: document.body, global: {plugins: [pinia, router]}});
  await flushPromises();
  return {wrapper, router, auth};
}

describe("SettingsView", () => {
  beforeEach(() => {
    runtime.flushWorkspacePrefs.mockClear();
    runtime.flushWorkspacePrefs.mockResolvedValue(undefined);
    runtime.state.appConfig.ui_color_theme = "green";
    runtime.state.appConfig.ui_color_scheme = "system";
    runtime.state.appConfig.ui_contrast = "system";
    runtime.state.ragConfig.k = 64;
    runtime.state.ragConfig.fetch_k = 500;
    runtime.state.ragConfig.locales = ["en", "fr"];
    runtime.state.ragConfig.search_types = ["similarity", "lexical", "mmr"];
  });

  it("keeps researcher accounts off administrative sections", async () => {
    const {wrapper} = await mountView("researcher");
    expect(wrapper.get("h1").text()).toContain("Settings");
    expect(wrapper.text()).toContain("Research workspace");
    expect(wrapper.text()).not.toContain("NUKE DerridAI workspace");
    expect(wrapper.text()).not.toContain("Save RAG defaults");
  });

  it("shows copyright and version without a git commit for researchers", async () => {
    const {wrapper} = await mountView("researcher", {section: "workspace"});
    expect(wrapper.text()).toContain("About DerridAI");
    expect(wrapper.text()).toContain("The New England Transcendental Club of California");
    expect(wrapper.text()).not.toContain("Build vitest");
  });

  it("shows the git commit on About for administrators", async () => {
    const {wrapper} = await mountView("admin", {section: "workspace"});
    expect(wrapper.text()).toContain("Build vitest");
  });

  it("deep-links an admin section from the URL", async () => {
    const {wrapper} = await mountView("admin", {section: "retrieval"});
    expect(wrapper.get("#settings-section-retrieval").isVisible()).toBe(true);
    expect(wrapper.get("#settings-nav-retrieval").attributes("aria-selected")).toBe("true");
  });

  it("preserves retrieval input after a validation failure", async () => {
    const {wrapper} = await mountView("admin", {section: "retrieval"});
    await wrapper.get("#settings-field-rag-k").setValue(12);
    await wrapper.get("#settings-field-rag-locale-en").setValue(false);
    await wrapper.get("#settings-field-rag-locale-fr").setValue(false);
    await wrapper.findAll("button").find(button => button.text().includes("Save RAG defaults"))?.trigger("click");
    await flushPromises();
    expect((wrapper.get("#settings-field-rag-k").element as HTMLInputElement).value).toBe("12");
    expect(wrapper.text()).toContain("Some retrieval defaults could not be saved");
    expect(runtime.flushWorkspacePrefs).not.toHaveBeenCalled();
  });

  it("marks appearance unsaved then reports a persistence failure without dropping the draft", async () => {
    runtime.flushWorkspacePrefs.mockRejectedValueOnce(new Error("IndexedDB preference persistence failed"));
    const {wrapper} = await mountView("admin", {section: "workspace"});
    const dark = wrapper.get("#settings-field-scheme");
    await dark.setValue("dark");
    await flushPromises();
    expect(wrapper.text()).toContain("Unsaved changes");
    await wrapper.findAll("button").find(button => button.text().includes("Save appearance"))?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Save failed");
    expect(wrapper.text()).toContain("IndexedDB preference persistence failed");
    expect((dark.element as HTMLSelectElement).value).toBe("dark");
  });

  it("warns before leaving with unsaved changes", async () => {
    const {wrapper, router} = await mountView("admin", {section: "workspace"});
    await wrapper.get("#settings-field-scheme").setValue("dark");
    await flushPromises();
    const pending = router.push("/");
    await flushPromises();
    expect(document.body.textContent || "").toContain("Discard unsaved settings");
    const cancel = Array.from(document.body.querySelectorAll("button")).find(button => button.textContent === "Cancel");
    cancel?.dispatchEvent(new MouseEvent("click", {bubbles: true}));
    await pending.catch(() => undefined);
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/settings");
  });
});
