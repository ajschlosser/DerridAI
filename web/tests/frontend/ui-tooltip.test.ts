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

  it("supports compact slotted content as the focus, click, and touch-friendly trigger", async () => {
    const ContentHost = {
      components: { UiTooltip },
      template: `<UiTooltip text="A reviewer decision is required." trigger-mode="content"><span class="status">Needs review</span></UiTooltip>`,
    };
    const wrapper = mount(ContentHost, { attachTo: document.body });
    const trigger = wrapper.get(".ui-tooltip-anchor");
    expect(trigger.attributes("tabindex")).toBe("0");
    expect(trigger.attributes("aria-label")).toBeUndefined();

    await trigger.trigger("focus");
    await nextTick();
    const bubble = document.querySelector<HTMLElement>('[role="tooltip"]')!;
    expect(bubble.hidden).toBe(false);
    expect(trigger.attributes("aria-describedby")).toBe(bubble.id);

    await trigger.trigger("keydown", { key: "Escape" });
    expect(bubble.hidden).toBe(true);
    await trigger.trigger("click");
    expect(bubble.hidden).toBe(false);
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
