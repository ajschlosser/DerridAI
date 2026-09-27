/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import UiCombobox from "../../src/components/ui/UiCombobox.vue";

const mountCombo = (modelValue: string, multiple = false) =>
  mount(UiCombobox, {
    props: {
      modelValue,
      options: ["affirm", "describe", "neutral"],
      recommended: ["Describe"],
      recommendedLabel: "Suggested",
      label: "Stance",
      multiple,
    },
  });

describe("choice combobox suggested value", () => {
  it("marks the field itself with the star when its value is the suggestion", () => {
    const wrapper = mountCombo("describe");
    const badge = wrapper.find('[data-testid="combo-value-recommended"]');
    expect(badge.text()).toContain("★");
    expect(wrapper.find("input").attributes("aria-describedby")).toBe(badge.attributes("id"));
  });

  it("drops the star once the reviewer picks something else", () => {
    const wrapper = mountCombo("neutral");
    expect(wrapper.find('[data-testid="combo-value-recommended"]').exists()).toBe(false);
    expect(wrapper.find("input").attributes("aria-describedby")).toBeUndefined();
  });
});
