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
import {
  buildCompareRows,
  filterLibraryOptions,
  parseCompareRecord,
  prettyRecord,
} from "../../src/domain/compare";

describe("compare domain", () => {
  it("parses a single JSONL line and pretty JSON without inventing fields", () => {
    const line = parseCompareRecord('{"record_id":"r1","work":"Glas","text":"hello"}');
    expect(line.record?.record_id).toBe("r1");
    expect(parseCompareRecord(prettyRecord(line.record!)).record?.text).toBe("hello");
  });

  it("rejects multiple JSONL rows so copies cannot be silently mixed", () => {
    const parsed = parseCompareRecord('{"record_id":"a"}\n{"record_id":"b"}');
    expect(parsed.record).toBeNull();
    expect(parsed.errorKey).toBe("compare.error.one_record");
  });

  it("marks only changed fields and hides audit history", () => {
    const rows = buildCompareRows(
      { record_id: "a", text: "one", updates: [{ n: 1 }] },
      { record_id: "a", text: "two", updates: [{ n: 2 }] },
      "changed",
    );
    expect(rows.map((row) => row.key)).toEqual(["text"]);
    expect(rows[0]?.parts.some((part) => part.kind === "ins")).toBe(true);
  });

  it("filters library options by work or record id without requiring a giant select", () => {
    const hits = filterLibraryOptions(
      [
        { value: "1", label: "file.jsonl · r1 · Glas", search: "derrida" },
        { value: "2", label: "file.jsonl · r2 · Voice", search: "other" },
      ],
      "glas",
    );
    expect(hits.map((item) => item.value)).toEqual(["1"]);
  });
});
