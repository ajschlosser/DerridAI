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
