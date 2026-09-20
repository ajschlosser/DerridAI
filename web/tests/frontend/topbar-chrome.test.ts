/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import TopbarChrome from "../../src/components/shell/TopbarChrome.vue";
import TopbarHelp from "../../src/components/shell/TopbarHelp.vue";
import TopbarAccount from "../../src/components/shell/TopbarAccount.vue";

const languages = [
  {code: "en-US", name: "English", flag: "🇺🇸"},
  {code: "fr-CA", name: "Français", flag: "🇨🇦"},
];

function stubViewport(compact: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: compact && query.includes("650"),
    media: query,
    onchange: null,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
    dispatchEvent() { return false; },
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("TopbarChrome", () => {
  it("names Help, language, and the account menu", async () => {
    stubViewport(false);
    const wrapper = mount(TopbarChrome, {
      props: {
        username: "aaron",
        role: "admin",
        isAdmin: true,
        canFaq: true,
        languages,
        locale: "en-US",
      },
      attachTo: document.body,
    });
    await flushPromises();
    expect(wrapper.get("button[aria-label='Help']").exists()).toBe(true);
    expect(wrapper.get("button[aria-label='Interface language, English']").text()).toContain("English");
    expect(wrapper.findAll("button[aria-haspopup='menu']").map((button) => button.text()).join(" ")).not.toContain("Workspace");
    expect(wrapper.get("button[aria-haspopup='dialog']").attributes("aria-label")).toBe("Account menu for aaron");
    wrapper.unmount();
  });

  it("hides standalone chrome on a narrow viewport and keeps those tasks in the account menu", async () => {
    stubViewport(true);
    const wrapper = mount(TopbarChrome, {
      props: {
        username: "aaron",
        role: "admin",
        isAdmin: true,
        canFaq: true,
        languages,
        locale: "en-US",
      },
      attachTo: document.body,
    });
    await flushPromises();
    expect(wrapper.find("button[aria-label='Help']").exists()).toBe(false);
    expect(wrapper.find("button[aria-label='Interface language, English']").exists()).toBe(false);
    await wrapper.get("button[aria-haspopup='dialog']").trigger("click");
    const dialog = wrapper.get("[role=dialog]");
    expect(dialog.text()).toContain("Help");
    expect(dialog.text()).toContain("Interface language");
    expect(dialog.text()).not.toContain("Workspace");
    expect(dialog.text()).not.toContain("Open JSONL");
    wrapper.unmount();
  });

  it("does not offer workspace tools to a researcher", async () => {
    stubViewport(false);
    const wrapper = mount(TopbarChrome, {
      props: {
        username: "ria",
        role: "researcher",
        isAdmin: false,
        canFaq: false,
        languages,
        locale: "en-US",
      },
      attachTo: document.body,
    });
    await flushPromises();
    expect(wrapper.findAll("button[aria-haspopup='menu']").map((button) => button.text()).join(" ")).not.toContain("Workspace");
    wrapper.unmount();
  });
});

describe("TopbarHelp", () => {
  it("opens a help dialog instead of sending a researcher to Response Library", async () => {
    const wrapper = mount(TopbarHelp, {
      props: {open: false, canFaq: false, canSettings: true},
      attachTo: document.body,
    });
    await wrapper.get("button[aria-label='Help']").trigger("click");
    expect(wrapper.emitted("update:open")).toEqual([[true]]);
    await wrapper.setProps({open: true});
    expect(document.body.textContent).toContain("Using DerridAI");
    expect(document.body.textContent).not.toContain("Open Response Library");
    expect(document.body.textContent).toContain("Open Settings");
    wrapper.unmount();
  });

  it("offers Response Library only when that page is allowed", async () => {
    const wrapper = mount(TopbarHelp, {
      props: {open: true, canFaq: true, showTrigger: false},
      attachTo: document.body,
    });
    expect(document.body.textContent).toContain("Open Response Library");
    wrapper.unmount();
  });
});

describe("TopbarAccount", () => {
  it("shows the translated built-in role and signs out with UiButton", async () => {
    const wrapper = mount(TopbarAccount, {
      props: {username: "aaron", role: "admin", isAdmin: true},
      attachTo: document.body,
    });
    expect(wrapper.get("button[aria-haspopup='dialog']").text()).toContain("Administrator");
    await wrapper.get("button[aria-haspopup='dialog']").trigger("click");
    const signOut = wrapper.findAll("button").find((button) => button.text() === "Sign out");
    expect(signOut?.classes().join(" ")).not.toContain("btn");
    await signOut?.trigger("click");
    expect(wrapper.emitted("logout")).toHaveLength(1);
    wrapper.unmount();
  });
});
