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
  fields: [
    {
      key: "work",
      label: "Work",
      kind: "text" as const,
      cardinality: "scalar" as const,
      controlledValues: [],
      strict: false,
      input: "text" as const,
      filterable: true,
    },
  ],
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

  it("renders strict controlled fields as selects", () => {
    const wrapper = mount(SearchAdvancedFilters, {
      props: {
        ...base,
        filters: [],
        fields: [
          {
            key: "role_alias",
            label: "Role",
            kind: "choice" as const,
            cardinality: "scalar" as const,
            controlledValues: ["author", "critic"],
            strict: true,
            input: "select" as const,
            filterable: true,
          },
        ],
        field: "role_alias",
        value: "author",
        suggestions: ["author", "critic"],
      },
    });
    const control = wrapper.get(".search-filter-value-control");
    expect(control.element.tagName).toBe("SELECT");
    expect(control.findAll("option").map((option) => option.attributes("value"))).toEqual([
      "",
      "author",
      "critic",
    ]);
  });

  it("renders numeric schema fields with numeric input semantics", () => {
    const wrapper = mount(SearchAdvancedFilters, {
      props: {
        ...base,
        filters: [],
        fields: [
          {
            key: "conceptual_score",
            label: "Conceptual score",
            kind: "number" as const,
            cardinality: "scalar" as const,
            controlledValues: [],
            strict: false,
            input: "number" as const,
            filterable: true,
          },
        ],
        field: "conceptual_score",
        value: "0.7",
        suggestions: [],
      },
    });
    const control = wrapper.get(".search-filter-value-control");
    expect(control.element.tagName).toBe("INPUT");
    expect(control.attributes("type")).toBe("number");
    expect(control.attributes("step")).toBe("any");
  });
});
