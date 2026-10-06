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

import { describe, expect, it, beforeEach } from "vitest";
import {
  chosenFilterSchemaId,
  defaultFilterSchemaId,
  filterFieldsFromSchema,
  filterOpsForKind,
  filterValueSuggestions,
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

  it("prefers a schema over collection and fallback lists for loaded records", () => {
    const fields = resolveSearchFilterFields({
      schema,
      collectionFields: ["work"],
      availableFields: ["work", "needs_review"],
      database: false,
    });
    expect(fields.map((field) => field.key)).toEqual(["speaker", "year", "topics"]);
  });

  it("intersects schema fields with database index capabilities without relying on built-in names", () => {
    const renamedSchema = {
      id: "renamed",
      name: "Renamed",
      fields: [
        {
          field_id: "field-position-holder",
          name: "holder_alias",
          semantic_compatibility_id: "derridai.position_holder",
          label: "Position holder",
          type: "choice",
          strict: true,
          values: [
            { value: "Derrida", definition: "" },
            { value: "Levinas", definition: "" },
          ],
        },
        {
          field_id: "field-conceptual-tension",
          name: "conceptual_tension",
          label: "Conceptual tension",
          type: "list",
          values: [],
        },
        { field_id: "field-unindexed", name: "unindexed_note", label: "Note", type: "text" },
      ],
    } as MetadataSchema;

    const fields = resolveSearchFilterFields({
      schema: renamedSchema,
      collectionFields: ["holder_alias", "conceptual_tension"],
      database: true,
    });

    expect(fields.map((field) => field.key)).toEqual(["holder_alias", "conceptual_tension"]);
    expect(fields[0]).toMatchObject({
      fieldId: "field-position-holder",
      semanticCompatibilityId: "derridai.position_holder",
      kind: "choice",
      cardinality: "scalar",
      controlledValues: ["Derrida", "Levinas"],
      strict: true,
      input: "select",
    });
    expect(fields[1]).toMatchObject({
      fieldId: "field-conceptual-tension",
      kind: "list",
      cardinality: "collection",
      input: "text",
    });
  });

  it("uses collection filter fields as the database capability when no schema is associated", () => {
    const fields = resolveSearchFilterFields({
      collectionFields: ["stance", "work"],
      availableFields: ["needs_review"],
      database: true,
    });
    expect(fields.map((field) => field.key)).toEqual(["stance", "work"]);
  });

  it("keeps the legacy built-in ordering only for schema-less loaded records", () => {
    const fields = resolveSearchFilterFields({
      collectionFields: ["concepts", "work"],
      availableFields: ["page_start", "conceptual_tension"],
      database: false,
    });
    expect(fields.slice(0, 4).map((field) => field.key)).toEqual([
      "work",
      "document_author",
      "year",
      "document_language",
    ]);
    expect(fields.some((field) => field.key === "conceptual_tension")).toBe(true);
  });

  it("uses schema-controlled boolean values to choose a closed select control", () => {
    const booleanSchema = {
      id: "boolean",
      name: "Boolean",
      fields: [
        {
          field_id: "field-direct-speech",
          name: "direct_speech",
          label: "Direct speech",
          type: "boolean",
          values: [],
        },
      ],
    } as unknown as MetadataSchema;
    const [field] = filterFieldsFromSchema(booleanSchema);
    expect(field).toMatchObject({
      kind: "boolean",
      controlledValues: ["true", "false"],
      input: "select",
    });
    expect(filterValueSuggestions(field, ["unexpected"])).toEqual(["true", "false"]);
  });

  it("keeps strict controlled values closed even when observed records contain stale values", () => {
    const [field] = filterFieldsFromSchema({
      id: "strict",
      name: "Strict",
      fields: [
        {
          field_id: "field-role",
          name: "role_alias",
          label: "Role",
          type: "choice",
          strict: true,
          values: [
            { value: "author", definition: "" },
            { value: "critic", definition: "" },
          ],
        },
      ],
    } as unknown as MetadataSchema);
    expect(filterValueSuggestions(field, ["legacy-value"])).toEqual(["author", "critic"]);
  });

  it("does not offer unindexed schema fields when a database declares no filter capability", () => {
    expect(
      resolveSearchFilterFields({
        schema,
        collectionFields: [],
        database: true,
      }),
    ).toEqual([]);
  });

  it("limits database operators to equality unless filters-only search is active", () => {
    expect(
      filterOpsForKind("list", { database: true, method: "similarity" }).map(([op]) => op),
    ).toEqual(["eq"]);
    expect(
      filterOpsForKind("list", { database: true, method: "filter" }).map(([op]) => op),
    ).toEqual(["has", "eq"]);
  });

  it("uses schema type semantics instead of text containment for choices and booleans", () => {
    expect(filterOpsForKind("choice").map(([op]) => op)).toEqual([
      "eq",
      "neq",
      "empty",
      "notempty",
    ]);
    expect(filterOpsForKind("boolean").map(([op]) => op)).toEqual([
      "eq",
      "neq",
      "empty",
      "notempty",
    ]);
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
