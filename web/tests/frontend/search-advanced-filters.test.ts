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
import SearchAdvancedFilters from "../../src/components/search/SearchAdvancedFilters.vue";

const base = {
  fields: [{ key: "work", label: "Work", kind: "text" as const }],
  schemas: [
    {
      id: "default",
      name: "Default",
      description: "",
      builtin: true,
      field_count: 1,
      groups: [] as string[],
      hash: "h",
    },
  ],
  schemaId: "default",
  associatedSchemaId: "default",
  field: "work",
  op: "eq",
  value: "Adieu",
  ops: [["eq", "search.op_eq", "is"] as [string, string, string]],
  suggestions: ["Adieu"],
};

describe("Search advanced filters", () => {
  it("labels the first applied condition Where and the composer And", () => {
    const wrapper = mount(SearchAdvancedFilters, {
      props: {
        ...base,
        filters: [
          {
            id: "f1",
            field: "work",
            field_label: "Work",
            op: "eq",
            op_label: "is",
            value: "Adieu",
          },
        ],
      },
    });
    const joins = wrapper.findAll(".search-rule-join").map((node) => node.text());
    expect(joins[0]).toBe("Where");
    expect(joins[1]).toBe("And");
  });

  it("emits add from the composer", async () => {
    const wrapper = mount(SearchAdvancedFilters, { props: { ...base, filters: [] } });
    await wrapper.get(".search-add-filter").trigger("click");
    expect(wrapper.emitted("add")).toHaveLength(1);
  });
});
