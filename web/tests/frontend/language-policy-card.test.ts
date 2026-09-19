import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  system: {
    researcherProviders: vi.fn(),
    languages: vi.fn(),
    language: vi.fn(),
    languageContentPolicy: vi.fn(),
  },
  jobs: { list: vi.fn(), get: vi.fn(), cancel: vi.fn() },
}));
vi.mock("../../src/api/system", () => ({ systemApi: api.system }));
vi.mock("../../src/api/jobs", () => ({ jobsApi: api.jobs }));
vi.mock("../../src/runtime/runtime.js", () => ({
  notifyToast: vi.fn(), getDefaultProviderProfileId: () => "", getProviderProfilesForUi: () => [], registerExternalJob: vi.fn(), triggerOperations: vi.fn(),
  __v_isRef: false, __v_isReadonly: false, __v_isShallow: false, __v_skip: true, __v_raw: undefined,
}));

import LanguagesView from "../../src/views/LanguagesView.vue";

const TERMS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"];

async function mountView() {
  setActivePinia(createPinia());
  const wrapper = mount(LanguagesView);
  await flushPromises();
  return wrapper;
}

describe("researcher text policy card", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.system.researcherProviders.mockResolvedValue({ profiles: [] });
    api.system.languages.mockResolvedValue({ languages: [{ code: "en-US", name: "English", flag: "🇺🇸" }] });
    api.system.language.mockResolvedValue({ code: "en-US", name: "English", flag: "🇺🇸", dictionary: { "app.name": "DerridAI" } });
    api.system.languageContentPolicy.mockResolvedValue({ status: "ready", blocked_terms: TERMS, contextual_terms: [] });
    api.jobs.list.mockResolvedValue({ jobs: [] });
  });

  it("keeps the card to two columns, with the term badges inside the copy column", async () => {
    const wrapper = await mountView();
    const card = wrapper.get(".language-policy-card");
    // Exactly two children: the descriptive column and the provider/generate column. A third
    // child (the old full-width terms row) is what made the grid grow a row.
    expect([...card.element.children].map(child => child.className)).toEqual(["language-policy-copy", "language-policy-actions"]);

    const copy = wrapper.get(".language-policy-copy");
    const terms = copy.get(".language-policy-terms");
    expect(terms.findAll("li").map(li => li.get("code").text())).toEqual(TERMS);
  });

  it("puts the badges right after the explanatory blurb, before the add/save editor", async () => {
    const wrapper = await mountView();
    const copy = wrapper.get(".language-policy-copy").element;
    const order = [...copy.querySelectorAll("small, .language-policy-terms ul, .language-policy-add")].map(node => node.className || node.tagName.toLowerCase());
    expect(order.indexOf("language-policy-add")).toBeGreaterThan(order.indexOf("ul"));
    const blurb = [...copy.children].findIndex(node => node.tagName === "SMALL");
    const termsBlock = [...copy.children].findIndex(node => node.classList.contains("language-policy-terms"));
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
      status: "ready", blocked_terms: TERMS, contextual_terms: [],
      generation_report: { attempts: 2, removed_as_wrong_language: 7 },
    });
    const wrapper = await mountView();
    expect(wrapper.get(".language-policy-report").text()).toContain("2 attempt(s)");
    expect(wrapper.get(".language-policy-report").text()).toContain("removed 7 term(s)");
  });

  it("says which categories are still short so an administrator can top them up", async () => {
    api.system.languageContentPolicy.mockResolvedValue({
      status: "ready", blocked_terms: TERMS, contextual_terms: [],
      generation_report: { attempts: 3, removed_as_wrong_language: 0, short_categories: ["ableist_slurs"] },
    });
    const wrapper = await mountView();
    expect(wrapper.get(".language-policy-gap").text()).toMatch(/ableist slurs/i);
    api.system.languageContentPolicy.mockResolvedValue({ status: "ready", blocked_terms: TERMS, contextual_terms: [], generation_report: { attempts: 1, removed_as_wrong_language: 0, short_categories: [] } });
    expect((await mountView()).find(".language-policy-gap").exists()).toBe(false);
  });

  it("shows no badge block before a policy exists", async () => {
    api.system.languageContentPolicy.mockResolvedValue({ status: "missing", blocked_terms: [], contextual_terms: [] });
    const wrapper = await mountView();
    expect(wrapper.find(".language-policy-terms").exists()).toBe(false);
  });
});
