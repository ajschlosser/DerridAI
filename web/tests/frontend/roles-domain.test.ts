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
import {
  categorySlug,
  expandPermissions,
  groupCapabilities,
  matchesCapabilityFilter,
  samePermissions,
} from "../../src/domain/roles";

describe("roles domain", () => {
  it("treats * as every capability when displaying a locked administrator role", () => {
    expect(expandPermissions(["*"], ["page.dashboard", "users.manage"])).toEqual([
      "page.dashboard",
      "users.manage",
    ]);
  });

  it("drops unknown ids and compares permission sets without regard to order", () => {
    expect(
      expandPermissions(["page.research", "ghost"], ["page.dashboard", "page.research"]),
    ).toEqual(["page.research"]);
    expect(samePermissions(["b", "a"], ["a", "b"])).toBe(true);
    expect(samePermissions(["a"], ["a", "b"])).toBe(false);
  });

  it("groups capabilities by category and matches a search against id, label, or description", () => {
    const grouped = groupCapabilities([
      {
        id: "page.research",
        category: "Pages",
        label: "Research",
        description: "Open Research.",
        configurable: true,
      },
      {
        id: "rag.run",
        category: "Research",
        label: "Run RAG",
        description: "Start jobs.",
        configurable: true,
      },
      {
        id: "page.dashboard",
        category: "Pages",
        label: "Dashboard",
        description: "Open the dashboard.",
        configurable: true,
      },
    ]);
    expect(grouped.map((group) => group.category)).toEqual(["Pages", "Research"]);
    expect(grouped[0]?.items).toHaveLength(2);
    expect(
      matchesCapabilityFilter(
        { id: "rag.run", label: "Run RAG", description: "Start jobs." },
        "rag",
      ),
    ).toBe(true);
    expect(
      matchesCapabilityFilter(
        { id: "rag.run", label: "Run RAG", description: "Start jobs." },
        "dashboard",
      ),
    ).toBe(false);
    expect(
      matchesCapabilityFilter(
        {
          id: "page.dashboard",
          label: "Dashboard",
          description: "Open the dashboard and researcher-safe overview widgets.",
        },
        "research",
      ),
    ).toBe(false);
    expect(categorySlug("Appearance & settings")).toBe("appearance_settings");
  });
});
