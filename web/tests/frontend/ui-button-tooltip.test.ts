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
import UiButton from "../../src/components/ui/UiButton.vue";

describe("UiButton help", () => {
  it("keeps disabled reasons reachable without native title", async () => {
    const wrapper = mount(UiButton, {
      attachTo: document.body,
      props: {
        label: "Unavailable",
        disabled: true,
        disabledReason: "Resolve the active operation first.",
      },
    });
    expect(wrapper.get("button").attributes("title")).toBeUndefined();
    const trigger = wrapper.get(".ui-tooltip-anchor");
    expect(trigger.attributes("tabindex")).toBe("0");
    await trigger.trigger("focus");
    await nextTick();
    const bubble = document.querySelector<HTMLElement>('[role="tooltip"]')!;
    expect(bubble.hidden).toBe(false);
    expect(bubble.textContent).toContain("Resolve the active operation first.");
    wrapper.unmount();
  });

  it("uses the actual icon-only button as the keyboard focus target", async () => {
    const wrapper = mount(UiButton, {
      attachTo: document.body,
      props: { label: "Refresh", icon: "refresh", iconOnly: true },
    });
    expect(wrapper.get("button").attributes("aria-label")).toBe("Refresh");
    expect(wrapper.get("button").attributes("title")).toBeUndefined();
    expect(wrapper.get(".ui-tooltip-anchor").attributes("tabindex")).toBeUndefined();
    await wrapper.get("button").trigger("focus");
    await nextTick();
    const bubble = document.querySelector<HTMLElement>('[role="tooltip"]')!;
    expect(bubble.hidden).toBe(false);
    expect(bubble.textContent).toContain("Refresh");
    wrapper.unmount();
  });
});
