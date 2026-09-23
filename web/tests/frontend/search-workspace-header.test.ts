/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import SearchWorkspaceHeader from "../../src/components/search/SearchWorkspaceHeader.vue";

describe("Search workspace header", () => {
  it("uses the shared page header and emits a scope change", async () => {
    const wrapper = mount(SearchWorkspaceHeader, {
      props: {
        scope: "loaded",
        totalLoaded: 12,
        databaseCount: 2,
        selectedEvidence: 1,
        canUseLoaded: true,
      },
    });
    expect(wrapper.find(".ui-page-header").exists()).toBe(true);
    expect(wrapper.get("#search-page-title").text()).toBe("Search");
    await wrapper.get('[aria-pressed="false"]').trigger("click");
    expect(wrapper.emitted("update:scope")?.[0]).toEqual(["database"]);
  });

  it("disables loaded-record scope for researcher accounts", () => {
    const wrapper = mount(SearchWorkspaceHeader, {
      props: {
        scope: "database",
        researcher: true,
        canUseLoaded: false,
        totalLoaded: 0,
        databaseCount: 1,
      },
    });
    expect(wrapper.get('[aria-pressed="false"]').attributes("disabled")).toBeDefined();
  });
});
