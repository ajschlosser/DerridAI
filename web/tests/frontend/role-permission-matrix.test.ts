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
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it } from "vitest";
import RolePermissionMatrix from "../../src/components/RolePermissionMatrix.vue";
import type { CapabilityDefinition } from "../../src/api/auth";

const capabilities: CapabilityDefinition[] = [
  {
    id: "page.dashboard",
    category: "Pages",
    label: "Dashboard",
    description: "Open the dashboard.",
    configurable: true,
  },
  {
    id: "page.research",
    category: "Pages",
    label: "Research",
    description: "Open Research.",
    configurable: true,
  },
  {
    id: "users.manage",
    category: "Administration",
    label: "Manage users",
    description: "Administrator-only.",
    configurable: false,
  },
];

function mountMatrix(props: Record<string, unknown> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(RolePermissionMatrix, {
    props: { capabilities, modelValue: ["page.dashboard"], disabled: false, filter: "", ...props },
    global: { plugins: [pinia] },
  });
}

describe("RolePermissionMatrix", () => {
  it("emits the updated permission list when a configurable row is toggled", async () => {
    const wrapper = mountMatrix();
    const research = wrapper.findAll("input[type=checkbox]")[1];
    await research?.setValue(true);
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual([
      "page.dashboard",
      "page.research",
    ]);
  });

  it("enables every configurable capability in a category from the group action", async () => {
    const wrapper = mountMatrix({ modelValue: [] });
    const enablePages = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Enable all in Pages"));
    expect(enablePages).toBeTruthy();
    await enablePages!.trigger("click");
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual([
      "page.dashboard",
      "page.research",
    ]);
  });

  it("keeps administrator-only rows disabled and marked", () => {
    const wrapper = mountMatrix();
    const adminOnly = wrapper.findAll("input[type=checkbox]")[2];
    expect(adminOnly?.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("Administrator only");
  });

  it("filters visible rows by the search string", async () => {
    const wrapper = mountMatrix({ filter: "research" });
    await flushPromises();
    expect(wrapper.text()).toContain("Research");
    expect(wrapper.text()).not.toContain("Dashboard");
  });
});
