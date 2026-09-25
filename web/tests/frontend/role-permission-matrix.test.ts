/* Copyright 2026 Aaron John Schlosser, PhD. */
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
