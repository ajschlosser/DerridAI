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
import { afterEach, describe, expect, it, vi } from "vitest";
import TopbarChrome from "../../src/components/shell/TopbarChrome.vue";
import TopbarHelp from "../../src/components/shell/TopbarHelp.vue";
import TopbarAccount from "../../src/components/shell/TopbarAccount.vue";

const languages = [
  { code: "en-US", name: "English", flag: "🇺🇸" },
  { code: "fr-CA", name: "Français", flag: "🇨🇦" },
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
    dispatchEvent() {
      return false;
    },
  }));
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  localStorage.removeItem("derridai.operations-dock-mode");
  delete document.documentElement.dataset.operationsDockMode;
  delete document.documentElement.dataset.operationsDockOpen;
  document.documentElement.style.removeProperty("--operations-dock-anchor-top");
  document.documentElement.style.removeProperty("--operations-dock-anchor-right");
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
    expect(wrapper.find("button[aria-label='Help']").exists()).toBe(true);
    expect(wrapper.get("button[aria-label='Interface language, English']").text()).toContain(
      "English",
    );
    expect(
      wrapper
        .findAll("button[aria-haspopup='menu']")
        .map((button) => button.text())
        .join(" "),
    ).not.toContain("Workspace");
    expect(wrapper.get("button[aria-haspopup='dialog']").attributes("aria-label")).toBe(
      "Account menu for aaron",
    );
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
    expect(
      wrapper
        .findAll("button[aria-haspopup='menu']")
        .map((button) => button.text())
        .join(" "),
    ).not.toContain("Workspace");
    wrapper.unmount();
  });

  it("defaults the operations dock to the top bar and starts it collapsed", async () => {
    stubViewport(false);
    document.body.innerHTML = `
      <aside id="operationProgressStack" class="operation-progress-stack">
        <button id="operationStackToggle" aria-expanded="true"></button>
      </aside>
    `;
    document.querySelector("#operationStackToggle")?.addEventListener("click", () => {
      document.querySelector("#operationProgressStack")?.classList.toggle("minimized");
    });
    const wrapper = mount(TopbarChrome, {
      props: { username: "aaron", role: "admin", languages, locale: "en-US" },
      attachTo: document.body,
    });
    await flushPromises();
    expect(document.documentElement.dataset.operationsDockMode).toBe("docked");
    expect(document.documentElement.dataset.operationsDockOpen).toBe("false");
    expect(document.querySelector("#operationProgressStack")?.classList.contains("minimized")).toBe(
      true,
    );
    expect(wrapper.get(".operations-docked-summary").attributes("aria-expanded")).toBe("false");
    wrapper.unmount();
  });

  it("opens and closes the docked operations dropdown from the top bar", async () => {
    stubViewport(false);
    localStorage.setItem("derridai.operations-dock-mode", "docked");
    document.body.innerHTML = `
      <aside id="operationProgressStack" class="operation-progress-stack minimized">
        <button id="operationStackToggle" aria-expanded="false"></button>
      </aside>
    `;
    document.querySelector("#operationStackToggle")?.addEventListener("click", () => {
      document.querySelector("#operationProgressStack")?.classList.toggle("minimized");
    });
    const wrapper = mount(TopbarChrome, {
      props: { username: "aaron", role: "admin", languages, locale: "en-US" },
      attachTo: document.body,
    });
    globalThis.dispatchEvent(
      new CustomEvent("derridai:operation-summary", {
        detail: {
          visible: true,
          title: "Operations",
          summary: "1 running",
          percent: 20,
          tone: "info",
          expanded: false,
        },
      }),
    );
    await flushPromises();
    await wrapper.get(".operations-docked-summary").trigger("click");
    expect(document.documentElement.dataset.operationsDockOpen).toBe("true");
    expect(document.querySelector("#operationProgressStack")?.classList.contains("minimized")).toBe(
      false,
    );
    await wrapper.get(".operations-docked-summary").trigger("click");
    expect(document.documentElement.dataset.operationsDockOpen).toBe("false");
    expect(document.querySelector("#operationProgressStack")?.classList.contains("minimized")).toBe(
      true,
    );
    wrapper.unmount();
  });

  it("double-clicking the docked summary undocks without also expanding it", async () => {
    vi.useFakeTimers();
    stubViewport(false);
    localStorage.setItem("derridai.operations-dock-mode", "docked");
    document.body.innerHTML = `
      <aside id="operationProgressStack" class="operation-progress-stack minimized">
        <button id="operationStackToggle" aria-expanded="false"></button>
      </aside>
    `;
    document.querySelector("#operationStackToggle")?.addEventListener("click", () => {
      document.querySelector("#operationProgressStack")?.classList.toggle("minimized");
    });
    const wrapper = mount(TopbarChrome, {
      props: { username: "aaron", role: "admin", languages, locale: "en-US" },
      attachTo: document.body,
    });
    globalThis.dispatchEvent(
      new CustomEvent("derridai:operation-summary", {
        detail: {
          visible: true,
          title: "Operations",
          summary: "1 running",
          percent: 20,
          tone: "info",
          expanded: false,
        },
      }),
    );
    await flushPromises();
    const summary = wrapper.get(".operations-docked-summary").element;
    summary.dispatchEvent(new MouseEvent("click", { bubbles: true, detail: 1 }));
    summary.dispatchEvent(new MouseEvent("click", { bubbles: true, detail: 2 }));
    summary.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, detail: 2 }));
    vi.runAllTimers();
    await flushPromises();
    expect(localStorage.getItem("derridai.operations-dock-mode")).toBe("floating");
    expect(document.documentElement.dataset.operationsDockMode).toBe("floating");
    expect(document.documentElement.dataset.operationsDockOpen).toBe("false");
    expect(document.querySelector("#operationProgressStack")?.classList.contains("minimized")).toBe(
      true,
    );
    wrapper.unmount();
  });

  it("switches mode from the dock's double-click event", async () => {
    stubViewport(false);
    localStorage.setItem("derridai.operations-dock-mode", "floating");
    const wrapper = mount(TopbarChrome, {
      props: { username: "aaron", role: "admin", languages, locale: "en-US" },
      attachTo: document.body,
    });
    globalThis.dispatchEvent(new CustomEvent("derridai:operation-mode-toggle"));
    await flushPromises();
    expect(localStorage.getItem("derridai.operations-dock-mode")).toBe("docked");
    expect(document.documentElement.dataset.operationsDockMode).toBe("docked");
    wrapper.unmount();
  });
});

describe("TopbarHelp", () => {
  it("opens a help dialog instead of sending a researcher to Response Library", async () => {
    const wrapper = mount(TopbarHelp, {
      props: { open: false, canFaq: false, canSettings: true },
      attachTo: document.body,
    });
    await wrapper.get("button[aria-label='Help']").trigger("click");
    expect(wrapper.emitted("update:open")).toEqual([[true]]);
    await wrapper.setProps({ open: true });
    expect(document.body.textContent).toContain("Using DerridAI");
    expect(document.body.textContent).not.toContain("Open Response Library");
    expect(document.body.textContent).toContain("Open Settings");
    wrapper.unmount();
  });

  it("offers Response Library only when that page is allowed", async () => {
    const wrapper = mount(TopbarHelp, {
      props: { open: true, canFaq: true, showTrigger: false },
      attachTo: document.body,
    });
    expect(document.body.textContent).toContain("Open Response Library");
    wrapper.unmount();
  });
});

describe("TopbarAccount", () => {
  it("shows the translated built-in role and signs out with UiButton", async () => {
    const wrapper = mount(TopbarAccount, {
      props: { username: "aaron", role: "admin", isAdmin: true },
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
