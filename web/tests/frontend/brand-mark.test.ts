/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import BrandMark from "../../src/components/BrandMark.vue";

describe("BrandMark", () => {
  it("is decorative and does not duplicate the localized product name", () => {
    const wrapper = mount(BrandMark);
    const mark = wrapper.get(".brand-mark");

    expect(mark.attributes("aria-hidden")).toBe("true");
    expect(wrapper.get("img").attributes("alt")).toBe("");
  });
});
