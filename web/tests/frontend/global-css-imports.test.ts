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

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

// style.css is an ordered @import index (import order is cascade order). A stylesheet that is
// split out but never imported silently stops applying, so the index must stay complete.
const SRC = resolve(process.cwd(), "src");
const imports = [
  ...readFileSync(join(SRC, "style.css"), "utf8").matchAll(/^@import "([^"]+)";$/gm),
].map((m) => m[1].replace(/^\.\//, ""));

function cssUnder(dir: string): string[] {
  return readdirSync(join(SRC, dir), { withFileTypes: true }).flatMap((entry) => {
    const rel = `${dir}/${entry.name}`;
    return entry.isDirectory() ? cssUnder(rel) : rel.endsWith(".css") ? [rel] : [];
  });
}

describe("global stylesheet import index", () => {
  it("imports every legacy and feature stylesheet exactly once", () => {
    const expected = [...cssUnder("styles/legacy"), ...cssUnder("styles/features")].sort();
    const indexed = imports.filter((p) => /^styles\/(legacy|features)\//.test(p)).sort();
    expect(indexed).toEqual(expected);
  });

  it("only imports files that exist", () => {
    expect(imports.filter((p) => !existsSync(join(SRC, p)))).toEqual([]);
  });
});
