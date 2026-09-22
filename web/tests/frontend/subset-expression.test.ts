/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import {
  describeExpression,
  fieldValueSuggestions,
  recordMatchesExpression,
  type SubsetExpressionItem,
} from "../../src/domain/subsetExpression";

const rule = (field: string, operator: string, value = "", join: "AND" | "OR" = "AND") =>
  ({ type: "rule", join, rule: { field, operator, value } }) as SubsetExpressionItem;
const glas = { record_id: "r1", work: "Glas", language: "fr", topics: ["mourning", "Hegel"] };
const margins = { record_id: "r2", work: "Margins", language: "en", topics: ["différance"] };

describe("subset expressions", () => {
  it("binds AND before OR", () => {
    // work = Margins AND language = fr  OR  work = Glas  →  (false AND …) OR true
    const items = [
      rule("work", "equals", "Margins"),
      rule("language", "equals", "fr"),
      rule("work", "equals", "Glas", "OR"),
    ];
    expect(recordMatchesExpression(glas, items, false)).toBe(true);
    expect(recordMatchesExpression(margins, items, false)).toBe(false);
  });

  it("evaluates a group as one condition with its own mode", () => {
    const group: SubsetExpressionItem = {
      type: "group",
      join: "AND",
      mode: "OR",
      rules: [
        { field: "topics", operator: "array_contains", value: "hegel" },
        { field: "topics", operator: "array_contains", value: "différance" },
      ],
    };
    expect(recordMatchesExpression(glas, [rule("language", "equals", "fr"), group], false)).toBe(
      true,
    );
    expect(recordMatchesExpression(margins, [rule("language", "equals", "fr"), group], false)).toBe(
      false,
    );
  });

  it("honours case sensitivity and matches nothing without conditions", () => {
    expect(recordMatchesExpression(glas, [rule("work", "equals", "glas")], false)).toBe(true);
    expect(recordMatchesExpression(glas, [rule("work", "equals", "glas")], true)).toBe(false);
    expect(recordMatchesExpression(glas, [], false)).toBe(false);
  });

  it("suggests distinct scalar values but none for long text fields", () => {
    expect(fieldValueSuggestions([glas, margins, glas], "topics")).toEqual([
      "différance",
      "Hegel",
      "mourning",
    ]);
    expect(fieldValueSuggestions([{ text: "a" }], "text")).toEqual([]);
  });

  it("describes the expression with the given labels", () => {
    const text = describeExpression(
      [rule("work", "equals", "Glas"), rule("topics", "exists", "", "OR")],
      {
        field: (key) => key.toUpperCase(),
        operator: (key) => `<${key}>`,
      },
    );
    expect(text).toBe("WORK <equals> “Glas” OR TOPICS <exists>");
  });
});
