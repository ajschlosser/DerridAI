/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  SUBSET_PROFILES_LIMIT,
  SubsetProfilesImportError,
  exportSubsetProfiles,
  mergeSubsetProfiles,
  parseSubsetProfilesImport,
  type SubsetProfile,
} from "../../src/domain/subsetProfiles";

const derrida: SubsetProfile = {
  id: "p1",
  name: "Primary Derrida",
  caseSensitive: false,
  expression: [
    {
      type: "rule",
      join: "AND",
      rule: { field: "document_author", operator: "equals", value: "Jacques Derrida" },
    },
    {
      type: "group",
      join: "AND",
      mode: "OR",
      rules: [
        { field: "language", operator: "equals", value: "fr" },
        { field: "needs_review", operator: "falsy", value: "" },
      ],
    },
  ],
};
const file = (profiles: unknown[], extra: Record<string, unknown> = {}) =>
  JSON.stringify({ ...exportSubsetProfiles([]), profiles, ...extra });
const code = (fn: () => unknown) => {
  try {
    fn();
  } catch (error) {
    return error instanceof SubsetProfilesImportError ? error.code : "other";
  }
  return "none";
};

describe("subset filter profile export and import", () => {
  it("round-trips every saved profile, including grouped conditions and case sensitivity", () => {
    const exported = JSON.stringify(
      exportSubsetProfiles([derrida, { ...derrida, id: "p2", name: "Exact", caseSensitive: true }]),
    );
    const { profiles, skipped } = parseSubsetProfilesImport(exported);
    expect(skipped).toBe(0);
    expect(profiles).toEqual([
      derrida,
      { ...derrida, id: "p2", name: "Exact", caseSensitive: true },
    ]);
  });

  it("skips a profile whole when any condition is unreadable instead of dropping the condition", () => {
    const broken = {
      ...derrida,
      id: "bad",
      expression: [
        derrida.expression[0],
        { type: "rule", join: "AND", rule: { field: "work", operator: "sounds_like" } },
      ],
    };
    const { profiles, skipped } = parseSubsetProfilesImport(file([derrida, broken]));
    expect(profiles.map((p) => p.id)).toEqual(["p1"]);
    expect(skipped).toBe(1);
  });

  it("refuses files that are not a profile export", () => {
    expect(code(() => parseSubsetProfilesImport("{"))).toBe("not_json");
    expect(code(() => parseSubsetProfilesImport(JSON.stringify([derrida])))).toBe("wrong_format");
    expect(code(() => parseSubsetProfilesImport(file([derrida], { version: 99 })))).toBe(
      "newer_version",
    );
    expect(code(() => parseSubsetProfilesImport(file([{ name: "" }])))).toBe("no_profiles");
  });

  it("replaces a profile with the same id or name and adds the rest", () => {
    const saved = [derrida, { ...derrida, id: "p9", name: "French only" }];
    const incoming = [
      { ...derrida, caseSensitive: true },
      { ...derrida, id: "other", name: "french ONLY" },
      { ...derrida, id: "", name: "New" },
    ];
    const result = mergeSubsetProfiles(saved, incoming, () => "made");
    expect(result).toMatchObject({ added: 1, replaced: 2, dropped: 0 });
    expect(result.profiles.map((p) => [p.id, p.name, p.caseSensitive])).toEqual([
      ["p1", "Primary Derrida", true],
      ["p9", "french ONLY", false],
      ["made", "New", false],
    ]);
  });

  it("reports profiles past the storage limit instead of losing them silently", () => {
    const saved = Array.from({ length: SUBSET_PROFILES_LIMIT - 1 }, (_, i) => ({
      ...derrida,
      id: `s${i}`,
      name: `S${i}`,
    }));
    const incoming = [1, 2, 3].map((i) => ({ ...derrida, id: `n${i}`, name: `N${i}` }));
    const result = mergeSubsetProfiles(saved, incoming, () => "x");
    expect(result.profiles).toHaveLength(SUBSET_PROFILES_LIMIT);
    expect(result).toMatchObject({ added: 1, dropped: 2 });
  });
});
