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
import { legacyCorpusUrl } from "../../src/api/corpus/compatibility";

describe("Corpus Builder legacy route compatibility", () => {
  it("keeps PDF-named server routes behind one adapter", () => {
    expect(legacyCorpusUrl("assets")).toBe("/api/pdf/assets");
    expect(legacyCorpusUrl("/corpus-builds")).toBe("/api/pdf/corpus-builds");
  });
});
