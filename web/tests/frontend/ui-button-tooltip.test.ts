// Copyright 2026 Aaron John Schlosser, PhD.
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
