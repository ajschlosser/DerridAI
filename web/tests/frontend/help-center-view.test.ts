/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/domain/helpTopics", () => ({
  visiblePageGuides: () => [],
  visibleGlossary: () => [],
  visibleHelp: (_isAdmin: boolean, query: string) => {
    if (query && !"breadcrumbs".includes(query.toLowerCase())) return [];
    return [
      {
        id: "navigation",
        title: "Navigation",
        entries: [
          {
            id: "breadcrumbs",
            question: "How do breadcrumbs work?",
            answer: "They reflect the current route.",
            impact: "Copied URLs reopen the same workspace.",
          },
        ],
      },
    ];
  },
}));

import HelpCenterView from "../../src/views/HelpCenterView.vue";
import { useI18nStore } from "../../src/stores/i18n";
import { useAuthStore } from "../../src/stores/auth";

async function mountView(query: Record<string, string> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  const auth = useAuthStore();
  auth.initialized = true;
  auth.user = { id: 1, username: "u", role: "admin", capabilities: [] } as never;
  useI18nStore().dictionary = {
    "help.title": "Help center",
    "help.intro": "Learn how DerridAI works.",
    "help.search": "Search help",
    "help.results_found": "{count} matches",
    "help.expand_all": "Expand all",
    "help.collapse_all": "Collapse all",
    "help.clear_search": "Clear search",
    "help.no_results": "No results for {query}",
    "help.impact_heading": "What this changes",
  };

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/help", name: "help", component: { template: "<div />" } }],
  });
  await router.push({ name: "help", query });
  await router.isReady();

  return {
    router,
    wrapper: mount(HelpCenterView, { global: { plugins: [pinia, router] } }),
  };
}

describe("HelpCenterView URL state", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("restores search from the URL and updates the shareable query", async () => {
    const { wrapper, router } = await mountView({ q: "breadcrumbs" });
    await flushPromises();

    const searchInput = wrapper.get("input[type=search]").element as HTMLInputElement;
    expect(searchInput.value).toBe("breadcrumbs");
    expect(wrapper.text()).toContain("How do breadcrumbs work?");

    await wrapper.get("input[type=search]").setValue("missing");
    await flushPromises();

    expect(router.currentRoute.value.query.q).toBe("missing");
    expect(wrapper.text()).toContain("No results");
  });

  it("highlights matches, expands all, and clears the search from the field", async () => {
    const { wrapper, router } = await mountView({ q: "bread" });
    await flushPromises();

    expect(wrapper.get("mark").text()).toBe("bread");
    expect(wrapper.get("#help-search-status").text()).toBe("1 matches");
    expect((wrapper.get("details").element as HTMLDetailsElement).open).toBe(true);

    await wrapper.get(".help-search-clear").trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.query.q).toBeUndefined();
    expect(wrapper.find("mark").exists()).toBe(false);
    expect((wrapper.get("details").element as HTMLDetailsElement).open).toBe(false);

    await wrapper.get(".help-toggle-all").trigger("click");
    expect((wrapper.get("details").element as HTMLDetailsElement).open).toBe(true);
  });
});
