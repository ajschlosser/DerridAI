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
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/domain/helpTopics", () => ({
  visiblePageGuides: () => [],
  visibleGlossary: () => [],
  visibleStarters: () => [],
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

  it("restores glossary category state in the URL", async () => {
    const { wrapper, router } = await mountView();
    await flushPromises();

    const buttons = wrapper.findAll(".help-filter");
    const storage = buttons.find((button) => button.text().toLowerCase().includes("storage"));
    expect(storage).toBeTruthy();
    await storage!.trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.query.topic).toBe("storage");

    await wrapper.get("input[type=search]").setValue("breadcrumbs");
    await flushPromises();
    expect(router.currentRoute.value.query.topic).toBeUndefined();
  });

  it("opens shareable question anchors and keeps them keyboard-operable", async () => {
    const { wrapper, router } = await mountView();
    await flushPromises();

    await router.push({ name: "help", hash: "#help-question-breadcrumbs" });
    await flushPromises();

    const question = wrapper.get("#help-question-breadcrumbs");
    expect((question.element as HTMLDetailsElement).open).toBe(true);
    expect(question.get("summary").attributes("tabindex")).toBeUndefined();
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
