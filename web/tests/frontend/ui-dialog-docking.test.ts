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

// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import UiDialog from "../../src/components/ui/UiDialog.vue";

describe("Optional dialog docking", () => {
  it("keeps the same input and focus when moving between dock and modal", async () => {
    const host = document.createElement("div");
    document.body.append(host);
    const wrapper = mount(UiDialog, {
      props: { title: "Build details", dockTarget: host },
      slots: { default: '<input aria-label="Model">' },
      attachTo: document.body,
    });
    try {
      await flushPromises();
      const input = host.querySelector("input")!;
      input.value = "pending-model";
      input.focus();
      expect(host.querySelector('[role="region"]')).not.toBeNull();
      expect(host.querySelector("[aria-modal]")).toBeNull();
      await wrapper.setProps({ dockTarget: null });
      await flushPromises();
      expect(document.querySelector('[role="dialog"] input')).toBe(input);
      expect(input.value).toBe("pending-model");
      expect(document.activeElement).toBe(input);
      await wrapper.setProps({ dockTarget: host });
      await flushPromises();
      expect(host.querySelector("input")).toBe(input);
      expect(document.activeElement).toBe(input);
    } finally {
      wrapper.unmount();
      host.remove();
    }
  });
  it("does not trap Tab or consume Escape outside a dock", async () => {
    const host = document.createElement("div"),
      outside = document.createElement("button");
    document.body.append(host, outside);
    const wrapper = mount(UiDialog, {
      props: { title: "Build details", dockTarget: host },
      slots: { default: '<input aria-label="Model">' },
      attachTo: document.body,
    });
    try {
      await flushPromises();
      outside.focus();
      outside.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }),
      );
      expect(wrapper.emitted("close")).toBeUndefined();
      const input = host.querySelector("input")!;
      input.focus();
      const tab = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
      input.dispatchEvent(tab);
      expect(tab.defaultPrevented).toBe(false);
      input.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }),
      );
      expect(wrapper.emitted("close")).toHaveLength(1);
    } finally {
      wrapper.unmount();
      host.remove();
      outside.remove();
    }
  });
  it("keeps default dialogs modal and restores their trigger on close", async () => {
    const trigger = document.createElement("button");
    document.body.append(trigger);
    trigger.focus();
    const wrapper = mount(UiDialog, {
      props: { title: "Default dialog" },
      attachTo: document.body,
    });
    await flushPromises();
    expect(document.querySelector('[role="dialog"]')?.getAttribute("aria-modal")).toBe("true");
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }),
    );
    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
    expect(document.activeElement).toBe(trigger);
    trigger.remove();
  });
});
