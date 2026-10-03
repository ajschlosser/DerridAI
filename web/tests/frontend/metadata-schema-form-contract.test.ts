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

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const FEATURE_FILES = [
  "src/components/MetadataSchemaEditor.vue",
  "src/components/metadata-schemas/SchemaFieldForm.vue",
  "src/components/metadata-schemas/SchemaFieldsTable.vue",
  "src/components/metadata-schemas/SchemaGroupsPanel.vue",
  "src/components/metadata-schemas/SchemaDocumentFieldsPanel.vue",
  "src/components/metadata-schemas/SchemaPreviewPanel.vue",
  "src/components/metadata-schemas/SchemaListTable.vue",
];

describe("metadata schema form contract", () => {
  it("uses shared primitives for ordinary native form controls", () => {
    const offenders: string[] = [];

    for (const path of FEATURE_FILES) {
      const source = readFileSync(path, "utf8");
      for (const match of source.matchAll(/<(input|select|textarea)\b[^>]*>/g)) {
        const tag = match[0];
        // File selection cannot be represented by the ordinary text-input primitive. It is
        // intentionally visually hidden behind the localized Import action.
        if (path.endsWith("MetadataSchemaEditor.vue") && /<input\b[^>]*type="file"/.test(tag))
          continue;
        offenders.push(`${path}: ${tag.replace(/\s+/g, " ")}`);
      }
    }

    expect(offenders).toEqual([]);
  });

  it("does not reintroduce feature-local legacy control skins", () => {
    const offenders = FEATURE_FILES.filter((path) =>
      /\.control\s*\{/.test(readFileSync(path, "utf8")),
    );
    expect(offenders).toEqual([]);
  });
});
