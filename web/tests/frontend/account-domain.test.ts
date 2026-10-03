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
import { roleLabel, userInitials } from "../../src/domain/account";

const t = (key: string, fallback: string) =>
  ({ "role.admin": "Administrateur", "role.researcher": "Chercheur" })[key] || fallback;

describe("account display", () => {
  it("builds initials from the username", () => {
    expect(userInitials("aaron")).toBe("A");
    expect(userInitials("Aaron Schlosser")).toBe("AS");
    expect(userInitials("")).toBe("U");
  });

  it("translates built-in roles and leaves custom names as stored", () => {
    expect(roleLabel("admin", "Administrator", t)).toBe("Administrateur");
    expect(roleLabel("researcher", "Researcher", t)).toBe("Chercheur");
    expect(roleLabel("editor", "Corpus editor", t)).toBe("Corpus editor");
  });
});
