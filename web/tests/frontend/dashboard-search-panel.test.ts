/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import DashboardSearchPanel from "../../src/components/dashboard/DashboardSearchPanel.vue";

const props = {
  query: "hospitality",
  mode: "traditional" as const,
  works: [{ work: "Of Hospitality", count: 12, year: "1997" }],
};

describe("DashboardSearchPanel", () => {
  it("submits a labelled query, selected work, and selected retrieval mode", async () => {
    const wrapper = mount(DashboardSearchPanel, { props });
    expect(wrapper.get("label span").text()).toBe("Search query");
    await wrapper.get("select").setValue("Of Hospitality");
    await wrapper.findAll("button").at(1)!.trigger("click");
    await wrapper.get("form").trigger("submit");
    expect(wrapper.emitted("submit")?.at(0)).toEqual(["hospitality", "Of Hospitality", "database"]);
  });
});
