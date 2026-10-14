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
