// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import UiHealthChip from "../../src/components/ui/UiHealthChip.vue";
import UiStatusBadge from "../../src/components/ui/UiStatusBadge.vue";

describe("feedback tooltip primitives", () => {
  it("keeps an unexplained status badge non-interactive and free of native title help", () => {
    const wrapper = mount(UiStatusBadge, {
      props: { label: "Confirmed", tone: "success" },
    });
    expect(wrapper.get(".ui-status-badge").attributes("title")).toBeUndefined();
    expect(wrapper.find(".ui-tooltip-anchor").exists()).toBe(false);
  });

  it("exposes status help through the shared keyboard/touch tooltip contract", async () => {
    const wrapper = mount(UiStatusBadge, {
      attachTo: document.body,
      props: {
        label: "Needs review",
        tone: "warning",
        help: "A reviewer decision is required.",
      },
    });
    const badge = wrapper.get(".ui-status-badge");
    expect(badge.attributes("title")).toBeUndefined();

    const trigger = wrapper.get(".ui-tooltip-anchor");
    expect(trigger.text()).toContain("Needs review");
    expect(trigger.attributes("tabindex")).toBe("0");

    await trigger.trigger("focus");
    await nextTick();
    const bubble = document.querySelector<HTMLElement>('[role="tooltip"]')!;
    expect(bubble.hidden).toBe(false);
    expect(bubble.textContent).toContain("A reviewer decision is required.");

    await trigger.trigger("keydown", { key: "Escape" });
    expect(bubble.hidden).toBe(true);
    wrapper.unmount();
  });

  it("keeps the health state visible while moving compact detail out of native title", async () => {
    const wrapper = mount(UiHealthChip, {
      attachTo: document.body,
      props: {
        available: false,
        label: "Chroma unavailable",
        detail: "Connection refused.",
      },
    });
    const chip = wrapper.get(".ui-health-chip");
    expect(chip.text()).toContain("Chroma unavailable");
    expect(chip.attributes("data-available")).toBe("false");
    expect(chip.attributes("title")).toBeUndefined();

    const trigger = wrapper.get(".ui-tooltip-anchor");
    await trigger.trigger("click");
    await nextTick();
    const bubble = document.querySelector<HTMLElement>('[role="tooltip"]')!;
    expect(bubble.hidden).toBe(false);
    expect(bubble.textContent).toContain("Connection refused.");
    wrapper.unmount();
  });
});
