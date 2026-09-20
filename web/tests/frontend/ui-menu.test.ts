/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import UiMenu from "../../src/components/ui/UiMenu.vue";

const items = [
  {id: "open", label: "Open JSONL"},
  {id: "merge", label: "Merge tabs", reason: "Load at least two JSONL tabs to merge them."},
  {id: "export", label: "Export"},
];
const mountMenu = () => mount(UiMenu, {props: {label: "Workspace", items}, attachTo: document.body});
const key = (wrapper: ReturnType<typeof mount>, selector: string, k: string) =>
  wrapper.get(selector).trigger("keydown", {key: k});

describe("UiMenu", () => {
  it("is a menu button that opens with a click and focuses an item", async () => {
    const wrapper = mountMenu();
    const trigger = wrapper.get("button[aria-haspopup='menu']");
    expect(trigger.attributes("aria-expanded")).toBe("false");
    await trigger.trigger("click");
    expect(trigger.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get("[role=menu]").attributes("aria-label")).toBe("Workspace");
    expect(document.activeElement?.textContent).toContain("Open JSONL");
    wrapper.unmount();
  });

  it("moves with the arrows and closes on Escape", async () => {
    const wrapper = mountMenu();
    const trigger = wrapper.get("button[aria-haspopup='menu']");
    await trigger.trigger("click");
    await key(wrapper, "[role=menu]", "ArrowDown");
    expect(document.activeElement?.textContent).toContain("Merge tabs");
    await key(wrapper, "[role=menu]", "Escape");
    expect(wrapper.find("[role=menu]").exists()).toBe(false);
    expect(document.activeElement).toBe(trigger.element);
    wrapper.unmount();
  });

  it("keeps an unavailable action focusable and does not run it", async () => {
    const wrapper = mountMenu();
    await wrapper.get("button[aria-haspopup='menu']").trigger("click");
    const unavailable = wrapper.findAll("[role=menuitem]")[1];
    expect(unavailable.attributes("aria-disabled")).toBe("true");
    await unavailable.trigger("click");
    expect(wrapper.emitted("select")).toBeUndefined();
    expect(wrapper.find("[role=menu]").exists()).toBe(true);
    wrapper.unmount();
  });

  it("uses menuitemradio when items carry checked", async () => {
    const wrapper = mount(UiMenu, {
      props: {
        label: "English",
        ariaLabel: "Interface language, English",
        items: [
          {id: "en-US", label: "English", checked: true},
          {id: "fr-CA", label: "Français", checked: false},
        ],
      },
      attachTo: document.body,
    });
    expect(wrapper.get("button[aria-haspopup='menu']").attributes("aria-label")).toBe("Interface language, English");
    await wrapper.get("button[aria-haspopup='menu']").trigger("click");
    const radios = wrapper.findAll("[role=menuitemradio]");
    expect(radios).toHaveLength(2);
    expect(radios[0].attributes("aria-checked")).toBe("true");
    await radios[1].trigger("click");
    expect(wrapper.emitted("select")).toEqual([["fr-CA"]]);
    wrapper.unmount();
  });
});
