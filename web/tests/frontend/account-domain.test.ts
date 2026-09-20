/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { roleLabel, userInitials } from "../../src/domain/account";

const t = (key: string, fallback: string) =>
  ({"role.admin": "Administrateur", "role.researcher": "Chercheur"}[key] || fallback);

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
