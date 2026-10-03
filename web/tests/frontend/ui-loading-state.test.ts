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
