// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import UiLoadingState from "../../src/components/ui/UiLoadingState.vue";

describe("UiLoadingState", () => {
  it("exposes one polite status with localized caller-provided copy", () => {
    const wrapper = mount(UiLoadingState, {
      props: {
        label: "Chargement des œuvres",
        detail: "Vérification de la base de données locale.",
      },
    });

    expect(wrapper.get('[role="status"]').attributes("aria-live")).toBe("polite");
    expect(wrapper.get('[role="status"]').attributes("aria-atomic")).toBe("true");
    expect(wrapper.text()).toContain("Chargement des œuvres");
    expect(wrapper.text()).toContain("Vérification de la base de données locale.");
    expect(wrapper.findAll(".ui-loading-skeleton")).toHaveLength(0);
  });

  it("keeps skeleton geometry decorative and bounded by the requested count", () => {
    const wrapper = mount(UiLoadingState, {
      props: { label: "Loading work cards", variant: "skeleton", skeletonCount: 4 },
    });

    expect(wrapper.get(".ui-loading-skeletons").attributes("aria-hidden")).toBe("true");
    expect(wrapper.findAll(".ui-loading-skeleton")).toHaveLength(4);
    expect(wrapper.findAll(".ui-loading-indicator")).toHaveLength(1);
  });
});
