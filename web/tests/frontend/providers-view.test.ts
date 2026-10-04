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
import ProvidersView from "../../src/views/ProvidersView.vue";

const saved = vi.fn();
const profile = () => ({
  id: "p1",
  name: "Local Ollama",
  type: "ollama",
  base_url: "http://ollama:11434",
  model: "qwen3.5:4b",
  max_concurrent_requests: 1,
});

vi.mock("../../src/domain/sharedProviderProfiles", () => ({
  getProviderProfilesForUi: () => [profile()],
  getProviderStatusesForUi: () => ({ p1: { available: true, models: [] } }),
  getProviderWarmupsForUi: () => ({}),
  getDefaultProviderProfileId: () => "p1",
  getWarmOnStartForUi: () => false,
  saveProviderProfilesForUi: (...args: unknown[]) => saved(...args),
  syncResearcherProviderProfiles: async () => undefined,
}));
vi.mock("../../src/domain/appBootstrap", () => ({ notifyToast: vi.fn() }));

async function mountView(query: Record<string, string> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/providers", name: "providers", component: { template: "<div />" } }],
  });
  await router.push({ name: "providers", query });
  await router.isReady();
  return {
    router,
    wrapper: mount(ProvidersView, { global: { plugins: [pinia, router] } }),
  };
}

describe("ProvidersView", () => {
  beforeEach(() => {
    saved.mockClear();
  });

  it("starts collapsed with no save bar, then reveals fields and saves only after an edit", async () => {
    const { wrapper } = await mountView();
    await flushPromises();
    const summary = wrapper.get(".provider-summary");
    expect(summary.attributes("aria-expanded")).toBe("false");
    expect(wrapper.find(".providers-save").exists()).toBe(false);
    expect(wrapper.text()).toContain("qwen3.5:4b");

    await summary.trigger("click");
    expect(summary.attributes("aria-expanded")).toBe("true");

    await wrapper.get(".provider-body input.control").setValue("Renamed");
    expect(wrapper.find(".providers-save").exists()).toBe(true);
    await wrapper.get(".providers-save .btn.primary").trigger("click");
    await vi.waitFor(() => expect(saved).toHaveBeenCalledOnce());
    expect(saved.mock.calls[0][0][0].name).toBe("Renamed");
    await vi.waitFor(() => expect(wrapper.find(".providers-save").exists()).toBe(false));
  });

  it("restores expanded providers from the URL and keeps panel state shareable", async () => {
    const { wrapper, router } = await mountView({ open: "p1" });
    await flushPromises();

    const summary = wrapper.get(".provider-summary");
    expect(summary.attributes("aria-expanded")).toBe("true");

    await summary.trigger("click");
    await flushPromises();
    expect(summary.attributes("aria-expanded")).toBe("false");
    expect(router.currentRoute.value.query.open).toBeUndefined();
  });

  it("discards edits", async () => {
    const { wrapper } = await mountView();
    await flushPromises();
    await wrapper.get(".provider-summary").trigger("click");
    await wrapper.get(".provider-body input.control").setValue("Renamed");
    await wrapper.get(".providers-save .btn:not(.primary)").trigger("click");
    expect(wrapper.find(".providers-save").exists()).toBe(false);
    expect(wrapper.get(".provider-title b").text()).toBe("Local Ollama");
  });
});
