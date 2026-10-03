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
import { format } from "prettier";
import { expect, it } from "vitest";

const paths = [
  "src/api/metadataMemory.ts",
  "src/components/metadata-memory/MetadataMemoryFilters.vue",
  "src/components/metadata-memory/MetadataMemoryFilters.stories.ts",
  "src/components/metadata-memory/MetadataMemoryTable.vue",
  "src/composables/useMetadataMemoryData.ts",
  "src/i18n/enUsDefaults.json",
  "src/realtime/dataQuery.ts",
  "src/views/MetadataMemoryView.vue",
  "tests/e2e/metadata-memory-progressive-loading.spec.ts",
  "tests/frontend/metadata-memory-view.test.ts",
  "../docs/USER_GUIDE.md",
];

it("temporary prettier dump", async () => {
  const differences: string[] = [];
  for (const path of paths) {
    const source = readFileSync(path, "utf8");
    const formatted = await format(source, { filepath: path, printWidth: 100 });
    if (formatted !== source) {
      differences.push(path);
      console.log(`PRETTIER_BEGIN ${path}\n${formatted}PRETTIER_END ${path}`);
    }
  }
  expect(differences).toEqual([]);
});
