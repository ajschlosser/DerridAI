/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CitationMenu from "../../src/components/CitationMenu.vue";

describe("CitationMenu", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("never pins the popover open with an inline display, so it can close again", async () => {
    const wrapper = mount(CitationMenu, { attachTo: document.body });
    const popover = wrapper.get("[role=menu]").element as HTMLElement;
    await wrapper.get("button[aria-haspopup='menu']").trigger("click");
    await popover.dispatchEvent(new Event("toggle"));
    expect(popover.style.display).toBe("");
    expect(popover.style.visibility).toBe("");
    wrapper.unmount();
  });

  it("emits the chosen citation kind", async () => {
    const wrapper = mount(CitationMenu, { attachTo: document.body });
    await wrapper.findAll("[role=menuitem]")[1].trigger("click");
    expect(wrapper.emitted("full")).toHaveLength(1);
    wrapper.unmount();
  });

  it("moves between items with the arrow keys and returns focus to the button on Escape", async () => {
    const wrapper = mount(CitationMenu, { attachTo: document.body });
    const menu = wrapper.get("[role=menu]");
    const [inline, full] = wrapper
      .findAll("[role=menuitem]")
      .map((item) => item.element as HTMLElement);
    inline.focus();
    await menu.trigger("keydown", { key: "ArrowDown" });
    expect(document.activeElement).toBe(full);
    await menu.trigger("keydown", { key: "ArrowDown" });
    expect(document.activeElement).toBe(inline);
    await menu.trigger("keydown", { key: "End" });
    expect(document.activeElement).toBe(full);
    await menu.trigger("keydown", { key: "Escape" });
    expect(document.activeElement).toBe(wrapper.get("button[aria-haspopup='menu']").element);
    wrapper.unmount();
  });
});
