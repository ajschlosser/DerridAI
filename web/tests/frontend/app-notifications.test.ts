/* Copyright 2026 Aaron John Schlosser, PhD. */
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
