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
import { beforeEach, describe, expect, it, vi } from "vitest";

const timing = vi.hoisted(() => ({
  afterPaint: null as (() => void) | null,
  runAfterNextPaint: vi.fn((task: () => void) => {
    timing.afterPaint = task;
  }),
}));

vi.mock("../../src/domain/interactionTiming", () => ({
  runAfterNextPaint: timing.runAfterNextPaint,
}));

import SidebarNavigator from "../../src/components/shell/SidebarNavigator.vue";

describe("SidebarNavigator interaction priority", () => {
  beforeEach(() => {
    localStorage.clear();
    timing.afterPaint = null;
    timing.runAfterNextPaint.mockClear();
  });

  it("emits navigation before persisting recents and defers storage until after paint", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const wrapper = mount(SidebarNavigator, {
      props: {
        collapsed: false,
        groups: [
          {
            id: "Research",
            section: "Research",
            items: [{ id: "rag", label: "Research", icon: "spark", active: false }],
          },
        ],
      },
    });

    await wrapper.get("button[aria-label='Research']").trigger("click");

    expect(wrapper.emitted("navigate")?.[0]).toEqual(["rag"]);
    expect(timing.runAfterNextPaint).toHaveBeenCalledTimes(1);
    expect(setItem).not.toHaveBeenCalled();

    timing.afterPaint?.();

    expect(setItem).toHaveBeenCalledTimes(1);
    expect(setItem.mock.calls[0]?.[0]).toBe("derridai.ui.navigationRecents");

    setItem.mockRestore();
  });
  it("keeps sidebar personalization isolated when the signed-in account changes", async () => {
    const wrapper = mount(SidebarNavigator, {
      props: {
        collapsed: false,
        storageScope: "admin:1",
        groups: [
          {
            id: "Research",
            section: "Research",
            items: [
              { id: "rag", label: "Research", icon: "spark", active: false },
              { id: "faq", label: "Response Library", icon: "books", active: false },
            ],
          },
        ],
      },
    });

    await wrapper.get("button[aria-label='Research']").trigger("click");
    timing.afterPaint?.();
    expect(
      JSON.parse(localStorage.getItem("derridai.ui.navigationRecents.admin:1") || "[]"),
    ).toEqual(["rag"]);
    expect(localStorage.getItem("derridai.ui.navigationRecents")).toBeNull();

    await wrapper.setProps({ storageScope: "admin:2" });
    timing.afterPaint = null;
    await wrapper.get("button[aria-label='Response Library']").trigger("click");
    timing.afterPaint?.();

    expect(
      JSON.parse(localStorage.getItem("derridai.ui.navigationRecents.admin:2") || "[]"),
    ).toEqual(["faq"]);
    expect(
      JSON.parse(localStorage.getItem("derridai.ui.navigationRecents.admin:1") || "[]"),
    ).toEqual(["rag"]);
  });

});
