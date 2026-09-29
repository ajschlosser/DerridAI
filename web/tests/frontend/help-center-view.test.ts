/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/domain/helpTopics", () => ({
  visibleHelp: (_isAdmin: boolean, query: string) => [
    {
      id: "navigation",
      title: "Navigation",
      entries:
        query && !"breadcrumbs".includes(query.toLowerCase())
          ? []
          : [
            {
              id: "breadcrumbs",
              question: "How do breadcrumbs work?",
              answer: "They reflect the current route.",
              impact: "Copied URLs reopen the same workspace.",
              },
            ],
    },
  ].filter((section) => section.entries.length),
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
    "help.result_count": "{count} results",
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

    expect(wrapper.get("input[type=search]").element.value).toBe("breadcrumbs");
    expect(wrapper.text()).toContain("How do breadcrumbs work?");

    await wrapper.get("input[type=search]").setValue("missing");
    await flushPromises();

    expect(router.currentRoute.value.query.q).toBe("missing");
    expect(wrapper.text()).toContain("No results");
  });
});
