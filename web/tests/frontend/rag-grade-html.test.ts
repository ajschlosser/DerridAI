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
import { ragGradeHtml } from "../../src/domain/ragGradeHtml";

describe("ragGradeHtml", () => {
  it("escapes model-supplied text and lists strengths", () => {
    const html = ragGradeHtml({ strengths: ["<b>clear</b>"], overall: 4 });
    expect(html).toContain("&lt;b&gt;clear&lt;/b&gt;");
    expect(html).not.toContain("<b>clear</b>");
  });

  it("says nothing was reported for an empty grade", () => {
    expect(ragGradeHtml({})).toContain("None reported.");
  });
});
