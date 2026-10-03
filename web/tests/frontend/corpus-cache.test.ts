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

import { beforeEach, describe, expect, it } from "vitest";
import {
  allRows,
  corpusCache,
  invalidateCorpusCache,
  memoCorpus,
  recordFingerprint,
} from "../../src/domain/corpusCache";
import { state } from "../../src/domain/sharedUrlState";

describe("shared corpus cache", () => {
  beforeEach(() => {
    state.files = [
      { id: "f1", name: "a.jsonl", records: [{ record_id: "1" }, { record_id: "2" }] },
    ];
    invalidateCorpusCache();
  });

  it("flattens records into rows once and reuses them until invalidated", () => {
    const rows = allRows();
    expect(rows.map((row) => row.index)).toEqual([0, 1]);
    expect(allRows()).toBe(rows);
    state.files[0].records.push({ record_id: "3" });
    invalidateCorpusCache();
    expect(allRows()).toHaveLength(3);
  });

  it("memoizes by key and clears the memo and bumps the version on invalidation", () => {
    let calls = 0;
    const build = () => ++calls;
    expect(memoCorpus("k", build)).toBe(1);
    expect(memoCorpus("k", build)).toBe(1);
    const before = corpusCache.version;
    invalidateCorpusCache();
    expect(corpusCache.version).toBe(before + 1);
    expect(memoCorpus("k", build)).toBe(2);
  });

  it("does not reuse a fingerprint after an in-place edit and invalidation", () => {
    const record: Record<string, unknown> = { record_id: "1", title: "Before" };
    const first = recordFingerprint(record);
    expect(recordFingerprint(record)).toBe(first);
    record.title = "After";
    invalidateCorpusCache();
    expect(recordFingerprint(record)).not.toBe(first);
  });
});
