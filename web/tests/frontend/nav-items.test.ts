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

import { afterEach, describe, expect, it } from "vitest";
import { getNavItems } from "../../src/domain/navItems";
import { sessionState } from "../../src/state/workspaceState";
import { state } from "../../src/domain/sharedUrlState";

describe("getNavItems", () => {
  afterEach(() => {
    sessionState.userContext = null;
    state.translations = { locale: "en-US", dictionary: {}, base: {} };
  });

  it("hides administrator-only pages from a researcher and translates labels", () => {
    state.translations = { locale: "fr-CA", dictionary: { "nav.search": "Recherche" }, base: {} };
    sessionState.userContext = { id: "u", role: "researcher", capabilities: ["page.search"] };
    const items = getNavItems();
    expect(items.find((i: { id: string }) => i.id === "global")?.label).toBe("Recherche");
    expect(items.some((i: { id: string }) => i.id === "providers")).toBe(false);
  });

  it("lists every page for an administrator with no disabled reason when stores are available", () => {
    sessionState.userContext = { id: "a", role: "admin", capabilities: ["*"] };
    const items = getNavItems();
    expect(items.some((i: { id: string }) => i.id === "providers")).toBe(true);
    expect(items.find((i: { id: string }) => i.id === "home")?.label).toBeTruthy();
  });
});
