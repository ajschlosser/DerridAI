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
import AppNotifications from "../../src/components/AppNotifications.vue";
import { toast, useNotifications } from "../../src/composables/notifications";
import { useI18nStore } from "../../src/stores/i18n";

describe("AppNotifications", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const { notifications, dismiss } = useNotifications();
    for (const item of [...notifications.value]) dismiss(item.id);
  });

  it("is a named live region that announces additions only", () => {
    const wrapper = mount(AppNotifications);
    const region = wrapper.get("section");
    expect(region.attributes("aria-label")).toBeTruthy();
    expect(region.attributes("aria-live")).toBe("polite");
    expect(region.attributes("aria-atomic")).toBe("false");
    expect(region.attributes("aria-relevant")).toBe("additions");
  });

  it("states the tone in text, not only in colour", async () => {
    useI18nStore();
    const wrapper = mount(AppNotifications);
    toast("Could not save", { tone: "danger", duration: null });
    await wrapper.vm.$nextTick();
    const item = wrapper.get(".notification");
    expect(item.get(".sr-only").text()).toMatch(/\S/);
    expect(item.get(".notification-icon").attributes("aria-hidden")).toBe("true");
  });

  it("dismisses a focused notification with Escape and has a labelled close button", async () => {
    const wrapper = mount(AppNotifications);
    toast("Saved", { tone: "success", duration: null });
    await wrapper.vm.$nextTick();
    expect(wrapper.get("button").attributes("aria-label")).toBeTruthy();
    await wrapper.get(".notification").trigger("keydown", { key: "Escape" });
    expect(wrapper.findAll(".notification")).toHaveLength(0);
  });
});
