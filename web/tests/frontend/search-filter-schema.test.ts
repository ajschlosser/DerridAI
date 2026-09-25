/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, beforeEach } from "vitest";
import {
  chosenFilterSchemaId,
  defaultFilterSchemaId,
  filterFieldsFromSchema,
  filterOpsForKind,
  resolveSearchFilterFields,
  saveFilterSchemaOverride,
} from "../../src/domain/searchFilterSchema";
import type { MetadataSchema } from "../../src/api/metadataSchemas";

const schema = {
  id: "notes",
  name: "Notes",
  fields: [
    { name: "speaker", label: "Speaker", type: "text" },
    { name: "year", label: "Year", type: "number" },
    { name: "topics", label: "Topics", type: "list" },
    { name: "text", label: "Text", type: "text" },
  ],
} as MetadataSchema;

describe("search filter schema", () => {
  beforeEach(() => localStorage.clear());

  it("uses schema fields and skips corpus text", () => {
    expect(filterFieldsFromSchema(schema).map((field) => field.key)).toEqual([
      "speaker",
      "year",
      "topics",
    ]);
  });

  it("prefers a schema over collection and fallback lists", () => {
    const fields = resolveSearchFilterFields({
      schema,
      collectionFields: ["work"],
      availableFields: ["work", "needs_review"],
    });
    expect(fields.map((field) => field.key)).toEqual(["speaker", "year", "topics"]);
  });

  it("falls back to collection filter fields when no schema is associated", () => {
    const fields = resolveSearchFilterFields({
      collectionFields: ["stance", "work"],
      availableFields: ["needs_review"],
    });
    expect(fields.map((field) => field.key)).toEqual(["stance", "work"]);
  });

  it("limits database operators to equality unless filters-only search is active", () => {
    expect(
      filterOpsForKind("list", { database: true, method: "similarity" }).map(([op]) => op),
    ).toEqual(["eq"]);
    expect(
      filterOpsForKind("list", { database: true, method: "filter" }).map(([op]) => op),
    ).toEqual(["has", "eq"]);
  });

  it("stores a user-chosen schema for a corpus and otherwise uses the associated or default schema", () => {
    expect(chosenFilterSchemaId({ store: "derrida-primary", associatedId: "notes" })).toBe("notes");
    saveFilterSchemaOverride("derrida-primary", "custom");
    expect(chosenFilterSchemaId({ store: "derrida-primary", associatedId: "notes" })).toBe(
      "custom",
    );
    expect(defaultFilterSchemaId()).toBe("default");
  });
});
