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
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  system: {
    researcherProviders: vi.fn(),
    languages: vi.fn(),
    language: vi.fn(),
    languageContentPolicy: vi.fn(),
    generateLanguageContentPolicy: vi.fn(),
  },
  jobs: { list: vi.fn(), get: vi.fn(), cancel: vi.fn() },
  runtime: {
    notifyToast: vi.fn(),
    getDefaultProviderProfileId: vi.fn(() => ""),
    getProviderProfilesForUi: vi.fn((): Array<Record<string, unknown>> => []),
    registerExternalJob: vi.fn(),
    triggerOperations: vi.fn(),
  },
}));
vi.mock("../../src/api/system", () => ({ systemApi: api.system }));
vi.mock("../../src/api/jobs", () => ({ jobsApi: api.jobs }));
vi.mock("../../src/domain/sharedProviderProfiles", () => ({
  getDefaultProviderProfileId: api.runtime.getDefaultProviderProfileId,
  getProviderProfilesForUi: api.runtime.getProviderProfilesForUi,
}));
vi.mock("../../src/domain/jobsActions", () => ({
  registerExternalJob: api.runtime.registerExternalJob,
}));
vi.mock("../../src/runtime/runtime.js", () => ({
  notifyToast: api.runtime.notifyToast,
  getDefaultProviderProfileId: api.runtime.getDefaultProviderProfileId,
  getProviderProfilesForUi: api.runtime.getProviderProfilesForUi,
  registerExternalJob: api.runtime.registerExternalJob,
  triggerOperations: api.runtime.triggerOperations,
  __v_isRef: false,
  __v_isReadonly: false,
  __v_isShallow: false,
  __v_skip: true,
  __v_raw: undefined,
}));

const router = vi.hoisted(() => ({
  route: { query: {} as Record<string, string> },
  replace: vi.fn(),
}));

vi.mock("vue-router", () => ({
  useRoute: () => router.route,
  useRouter: () => ({ replace: router.replace }),
}));

import LanguagesView from "../../src/views/LanguagesView.vue";

const TERMS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"];

async function mountView() {
  setActivePinia(createPinia());
  const wrapper = mount(LanguagesView);
  await flushPromises();
  return wrapper;
}

function pendingRead<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
function readDictionary(wrapper: ReturnType<typeof mount>, code = "en-US") {
  return (wrapper.vm as unknown as { load(code: string, reset: boolean): Promise<void> }).load(
    code,
    false,
  );
}
describe("researcher text policy card", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.system.researcherProviders.mockResolvedValue({ profiles: [] });
    api.system.languages.mockResolvedValue({
      languages: [{ code: "en-US", name: "English", flag: "🇺🇸" }],
    });
    api.system.language.mockResolvedValue({
      code: "en-US",
      name: "English",
      flag: "🇺🇸",
      dictionary: { "app.name": "DerridAI" },
    });
    api.system.languageContentPolicy.mockResolvedValue({
      status: "ready",
      blocked_terms: TERMS,
      contextual_terms: [],
    });
    api.jobs.list.mockResolvedValue({ jobs: [] });
    api.system.generateLanguageContentPolicy.mockReset();
    api.runtime.getProviderProfilesForUi.mockReset();
    api.runtime.getProviderProfilesForUi.mockReturnValue([]);
    api.runtime.getDefaultProviderProfileId.mockReturnValue("");
    router.replace.mockReset();
  });

  it("keeps the card to two columns, with the term badges inside the copy column", async () => {
    const wrapper = await mountView();
    const card = wrapper.get(".language-policy-card");
    // Exactly two children: the descriptive column and the provider/generate column. A third
    // child (the old full-width terms row) is what made the grid grow a row.
    expect([...card.element.children].map((child) => child.className)).toEqual([
      "language-policy-copy",
      "language-policy-actions",
    ]);

    const copy = wrapper.get(".language-policy-copy");
    const terms = copy.get(".language-policy-terms");
    expect(terms.findAll("li").map((li) => li.get("code").text())).toEqual(TERMS);
  });

  it("puts the badges right after the explanatory blurb, before the add/save editor", async () => {
    const wrapper = await mountView();
    const copy = wrapper.get(".language-policy-copy").element;
    const order = [
      ...copy.querySelectorAll("small, .language-policy-terms ul, .language-policy-add"),
    ].map((node) => node.className || node.tagName.toLowerCase());
    expect(order.indexOf("language-policy-add")).toBeGreaterThan(order.indexOf("ul"));
    const blurb = [...copy.children].findIndex((node) => node.tagName === "SMALL");
    const termsBlock = [...copy.children].findIndex((node) =>
      node.classList.contains("language-policy-terms"),
    );
    expect(termsBlock).toBe(blurb + 1);
  });

  it("keeps the provider and generate controls in the right column", async () => {
    const wrapper = await mountView();
    const actions = wrapper.get(".language-policy-actions");
    expect(actions.find("button.btn.primary").exists()).toBe(true);
    expect(wrapper.get(".language-policy-copy").find("button.btn.primary").exists()).toBe(false);
  });

  it("reports how the policy was generated, so a wrong-language cleanup is visible", async () => {
    api.system.languageContentPolicy.mockResolvedValue({
      status: "ready",
      blocked_terms: TERMS,
      contextual_terms: [],
      generation_report: { attempts: 2, removed_as_wrong_language: 7 },
    });
    const wrapper = await mountView();
    expect(wrapper.get(".language-policy-report").text()).toContain("2 attempt(s)");
    expect(wrapper.get(".language-policy-report").text()).toContain("removed 7 term(s)");
  });

  it("says which categories are still short so an administrator can top them up", async () => {
    api.system.languageContentPolicy.mockResolvedValue({
      status: "ready",
      blocked_terms: TERMS,
      contextual_terms: [],
      generation_report: {
        attempts: 3,
        removed_as_wrong_language: 0,
        short_categories: ["ableist_slurs"],
      },
    });
    const wrapper = await mountView();
    expect(wrapper.get(".language-policy-gap").text()).toMatch(/ableist slurs/i);
    api.system.languageContentPolicy.mockResolvedValue({
      status: "ready",
      blocked_terms: TERMS,
      contextual_terms: [],
      generation_report: { attempts: 1, removed_as_wrong_language: 0, short_categories: [] },
    });
    expect((await mountView()).find(".language-policy-gap").exists()).toBe(false);
  });

  it("sends the browser profile API key when generating a policy", async () => {
    api.runtime.getProviderProfilesForUi.mockReturnValue([
      {
        id: "openai-1",
        name: "OpenAI",
        type: "openai",
        model: "gpt-4.1",
        base_url: "https://api.openai.com/v1",
        api_key: "sk-browser-secret",
        max_concurrent_requests: 4,
      },
    ]);
    api.system.generateLanguageContentPolicy.mockResolvedValue({ id: "job-1", status: "queued" });
    const wrapper = await mountView();
    await wrapper.get(".language-policy-actions button.btn.primary").trigger("click");
    await flushPromises();
    expect(api.system.generateLanguageContentPolicy).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: "openai",
        model: "gpt-4.1",
        base_url: "https://api.openai.com/v1",
        api_key: "sk-browser-secret",
        provider_profile_id: "openai-1",
      }),
    );
  });

  it("shows no badge block before a policy exists", async () => {
    api.system.languageContentPolicy.mockResolvedValue({
      status: "missing",
      blocked_terms: [],
      contextual_terms: [],
    });
    const wrapper = await mountView();
    expect(wrapper.find(".language-policy-terms").exists()).toBe(false);
  });
  it("makes the dictionary usable before a delayed policy without claiming absence", async () => {
    const pending = pendingRead<unknown>();
    api.system.languageContentPolicy.mockReturnValueOnce(pending.promise);
    const wrapper = await mountView();
    expect(wrapper.find(".language-identity-card input").exists()).toBe(true);
    expect(wrapper.find(".language-policy-card .ui-loading-state").exists()).toBe(true);
    expect(wrapper.find(".language-policy-card").text()).not.toContain("policy is missing");
    pending.resolve({ code: "en-US", status: "missing", blocked_terms: [], contextual_terms: [] });
    await flushPromises();
    wrapper.unmount();
  });
  it("reports a policy read failure locally and retries only that read", async () => {
    api.system.languageContentPolicy.mockRejectedValueOnce(new Error("Policy offline"));
    const wrapper = await mountView();
    const dictionaryReads = api.system.language.mock.calls.length;
    expect(wrapper.get(".language-policy-card [role=alert]").text()).toContain("Policy offline");
    expect(wrapper.find(".language-identity-card").exists()).toBe(true);
    await wrapper.get(".language-policy-card [role=alert] button").trigger("click");
    await flushPromises();
    expect(api.system.language).toHaveBeenCalledTimes(dictionaryReads);
    expect(wrapper.find(".language-policy-card [role=alert]").exists()).toBe(false);
    wrapper.unmount();
  });
  it("retains the editor and edits made during a same-dictionary refresh", async () => {
    const wrapper = await mountView();
    const editor = wrapper.get(".language-identity-card").element;
    const pending = pendingRead<unknown>();
    api.system.language.mockReturnValueOnce(pending.promise);
    const operation = readDictionary(wrapper);
    await flushPromises();
    expect(wrapper.get(".language-identity-card").element).toBe(editor);
    await wrapper.get(".language-identity-card input").setValue("Unsaved name");
    pending.resolve({ code: "en-US", name: "Server name", dictionary: { "app.name": "DerridAI" } });
    await operation;
    await flushPromises();
    expect((wrapper.get(".language-identity-card input").element as HTMLInputElement).value).toBe(
      "Unsaved name",
    );
    wrapper.unmount();
  });
  it("retains a loaded dictionary through failure with local retry", async () => {
    const wrapper = await mountView();
    api.system.language.mockRejectedValueOnce(new Error("Dictionary offline"));
    await readDictionary(wrapper);
    await flushPromises();
    expect(wrapper.find(".language-identity-card").exists()).toBe(true);
    expect(wrapper.get(".language-read-error").text()).toContain("Dictionary offline");
    await wrapper.get(".language-read-error button").trigger("click");
    await flushPromises();
    expect(wrapper.find(".language-read-error").exists()).toBe(false);
    wrapper.unmount();
  });
  it("clears previous dictionary and policy while a new locale loads and rejects older results", async () => {
    const wrapper = await mountView();
    const old = pendingRead<unknown>();
    api.system.language.mockReturnValueOnce(old.promise);
    const previous = readDictionary(wrapper, "fr-CA");
    await flushPromises();
    expect(wrapper.find(".language-identity-card").exists()).toBe(false);
    api.system.language.mockResolvedValueOnce({
      code: "de-DE",
      name: "German",
      dictionary: { "app.name": "DerridAI" },
    });
    await readDictionary(wrapper, "de-DE");
    old.resolve({ code: "fr-CA", name: "French", dictionary: {} });
    await previous;
    await flushPromises();
    expect(wrapper.get(".language-editor-hero").text()).toContain("German");
    wrapper.unmount();
  });
  it("withholds initial counts and empty claims until bootstrap succeeds and can retry", async () => {
    const pending = pendingRead<unknown>();
    api.system.language.mockReturnValueOnce(pending.promise);
    const wrapper = await mountView();
    expect(wrapper.find(".language-workspace-stats").exists()).toBe(false);
    expect(wrapper.find(".language-empty-list").exists()).toBe(false);
    pending.reject(new Error("Bootstrap offline"));
    await flushPromises();
    expect(wrapper.get(".language-read-error").text()).toContain("Bootstrap offline");
    await wrapper.get(".language-read-error button").trigger("click");
    await flushPromises();
    expect(wrapper.find(".language-workspace-stats").exists()).toBe(true);
    expect(wrapper.find(".language-identity-card").exists()).toBe(true);
    wrapper.unmount();
  });
});
