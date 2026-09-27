// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import UiTooltip from "../../src/components/ui/UiTooltip.vue";

// A pane that scrolls and clips, like the review panes around the record viewer.
const Host = {
  components: { UiTooltip },
  template: `<div class="pane" style="overflow:hidden;height:40px"><UiTooltip text="Characters include spaces." label="About sizes" /></div>`,
};

describe("UiTooltip", () => {
  it("renders its explanation at the page level, so a clipping pane cannot hide it", async () => {
    const wrapper = mount(Host, { attachTo: document.body });
    await wrapper.get("button").trigger("focus");
    await nextTick();
    const bubble = document.querySelector<HTMLElement>('[role="tooltip"]')!;
    expect(bubble.hidden).toBe(false);
    expect(bubble.textContent).toContain("Characters include spaces.");
    expect(wrapper.get(".pane").element.contains(bubble)).toBe(false);
    expect(bubble.parentElement).toBe(document.body);
    expect(wrapper.get("button").attributes("aria-describedby")).toBe(bubble.id);
    wrapper.unmount();
  });

  it("closes on Escape and on blur", async () => {
    const wrapper = mount(Host, { attachTo: document.body });
    const button = wrapper.get("button");
    await button.trigger("focus");
    await button.trigger("keydown", { key: "Escape" });
    expect(document.querySelector<HTMLElement>('[role="tooltip"]')!.hidden).toBe(true);
    await button.trigger("click");
    expect(document.querySelector<HTMLElement>('[role="tooltip"]')!.hidden).toBe(false);
    await button.trigger("blur");
    expect(document.querySelector<HTMLElement>('[role="tooltip"]')!.hidden).toBe(true);
    wrapper.unmount();
  });

  it("stays inside the open dialog that contains it", async () => {
    const InDialog = {
      components: { UiTooltip },
      template: `<dialog open><UiTooltip text="Inside." /></dialog>`,
    };
    const wrapper = mount(InDialog, { attachTo: document.body });
    await wrapper.get("button").trigger("focus");
    await nextTick();
    const bubble = document.querySelector<HTMLElement>('[role="tooltip"]')!;
    expect(bubble.parentElement?.tagName).toBe("DIALOG");
    wrapper.unmount();
  });
});
