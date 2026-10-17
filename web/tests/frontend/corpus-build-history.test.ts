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

// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { CorpusBuild } from "../../src/api/pdfCorpus";
import CorpusBuildHistoryMenu from "../../src/components/CorpusBuildHistoryMenu.vue";
const builds = [
  {
    build_id: "b1",
    source_filename: "one.pdf",
    status: "running",
    record_count: 18,
    manifest: { title: "La Prisonnière" },
  },
  {
    build_id: "b2",
    source_filename: "two.pdf",
    status: "published",
    publication: { publication_id: "p1" },
    record_count: 100,
  },
] as CorpusBuild[];
const open = () =>
  mount(CorpusBuildHistoryMenu, {
    props: { builds, total: 5 },
    global: { stubs: { Teleport: true } },
  });
describe("Build history side panel", () => {
  it("searches titles, filters only active builds and closes after selection", async () => {
    const wrapper = open();
    await wrapper.get("button").trigger("click");
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("2 of 5 builds loaded");
    const active = wrapper
      .findAll("button")
      .find((button) => button.text().startsWith("Active ("))!;
    await active.trigger("click");
    expect(wrapper.findAll(".history-row")).toHaveLength(1);
    await wrapper.get("input").setValue("prisonnière");
    await wrapper.get(".history-row").trigger("click");
    expect(wrapper.emitted("select")?.[0]).toEqual([builds[0]]);
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(wrapper.emitted("openChange")).toEqual([[true], [false]]);
    wrapper.unmount();
  });
  it("retains loaded rows through errors and exposes paginated refresh actions", async () => {
    const wrapper = open();
    await wrapper.get("button").trigger("click");
    await wrapper.setProps({ error: "Refresh unavailable" });
    expect(wrapper.get('[role="alert"]').text()).toBe("Refresh unavailable");
    expect(wrapper.findAll(".history-row")).toHaveLength(2);
    const more = wrapper.findAll("button").find((button) => button.text() === "Load more builds")!;
    await more.trigger("click");
    expect(wrapper.emitted("loadMore")).toHaveLength(1);
    await wrapper.setProps({ loading: true });
    expect(
      wrapper
        .findAll("button")
        .find((button) => button.text() === "Load more builds")!
        .attributes("disabled"),
    ).toBeDefined();
    wrapper.unmount();
  });
  it("allows monitoring but prevents selection while an action is pending", async () => {
    const wrapper = open();
    await wrapper.get("button").trigger("click");
    await wrapper.setProps({ disabled: true });
    expect(wrapper.get(".history-row").attributes("disabled")).toBeDefined();
    await wrapper.get(".history-row").trigger("click");
    expect(wrapper.emitted("select")).toBeUndefined();
    expect(wrapper.get('[role="status"]').text()).toContain("Finish the current action");
    wrapper.unmount();
  });
});
