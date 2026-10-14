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
import { beforeAll, describe, expect, it } from "vitest";
import MessageDialogHost from "../../src/components/MessageDialogHost.vue";
import { openMessageDialog } from "../../src/composables/messageDialog";
import { useI18nStore } from "../../src/stores/i18n";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

function mountHost() {
  useI18nStore().dictionary = { "ui.notice": "Avis", "ui.ok": "D'accord", "ui.close": "Fermer" };
  return mount(MessageDialogHost, { attachTo: document.body });
}

describe("MessageDialogHost", () => {
  it("shows an alert dialog with localized defaults and resolves true on confirm", async () => {
    const wrapper = mountHost();
    const result = openMessageDialog({ message: "Saved.\nAll done." });
    await flushPromises();
    const dialog = wrapper.find("dialog");
    expect(dialog.attributes("role")).toBe("alertdialog");
    expect(dialog.attributes("open")).toBeDefined();
    expect(wrapper.find("h2").text()).toBe("Avis");
    expect(wrapper.find("button.primary").text()).toBe("D'accord");
    await wrapper.find("button.primary").trigger("click");
    await expect(result).resolves.toBe(true);
    wrapper.unmount();
  });

  it("resolves false on cancel or Escape and queues requests in order", async () => {
    const wrapper = mountHost();
    const first = openMessageDialog({ title: "First", message: "a", cancelLabel: "No" });
    const second = openMessageDialog({ title: "Second", message: "b" });
    await flushPromises();
    expect(wrapper.find("h2").text()).toBe("First");
    await wrapper.find("button:not(.primary):not(.icon-only)").trigger("click");
    await expect(first).resolves.toBe(false);
    await flushPromises();
    expect(wrapper.find("h2").text()).toBe("Second");
    await wrapper.find("dialog").trigger("cancel");
    await expect(second).resolves.toBe(false);
    await flushPromises();
    expect(wrapper.find("dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });

  it("marks danger confirmations as destructive", async () => {
    const wrapper = mountHost();
    const result = openMessageDialog({ message: "Delete?", tone: "danger", cancelLabel: "No" });
    await flushPromises();
    expect(wrapper.find("button.danger").exists()).toBe(true);
    await wrapper.find("button.danger").trigger("click");
    await expect(result).resolves.toBe(true);
    wrapper.unmount();
  });
});
