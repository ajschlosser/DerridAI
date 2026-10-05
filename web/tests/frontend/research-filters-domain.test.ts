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
  explainResearchFilterPlan,
  parseResearchFilterExpression,
  researchFilterCatalog,
  suggestResearchFilterCompletions,
} from "../../src/domain/researchFilters";

const catalog = researchFilterCatalog(["work", "page_start", "speaker", "translated"]);

function plan(text: string) {
  const result = parseResearchFilterExpression(text, catalog);
  if (!result.ok) throw new Error(JSON.stringify(result.errors));
  return result.plan;
}
function errors(text: string) {
  const result = parseResearchFilterExpression(text, catalog);
  if (result.ok) throw new Error("expected failure");
  return result.errors[0];
}

describe("research filter expressions", () => {
  it("compiles the documented example", () => {
    expect(
      plan('work = "Of Grammatology" and page_start >= 100 and speaker != "Heidegger"'),
    ).toEqual({
      metadata_filter: {
        $and: [
          { work: { $eq: "Of Grammatology" } },
          { page_start: { $gte: 100 } },
          { speaker: { $ne: "Heidegger" } },
        ],
      },
      document_filter: null,
    });
  });

  it("gives and higher precedence than or, and parentheses override it", () => {
    expect(plan('work = "A" or work = "B" and page_start > 1').metadata_filter).toEqual({
      $or: [{ work: { $eq: "A" } }, { $and: [{ work: { $eq: "B" } }, { page_start: { $gt: 1 } }] }],
    });
    expect(plan('(work = "A" or work = "B") and page_start > 1').metadata_filter).toEqual({
      $and: [{ $or: [{ work: { $eq: "A" } }, { work: { $eq: "B" } }] }, { page_start: { $gt: 1 } }],
    });
  });

  it("supports in / not in, booleans, negative numbers and quoted Unicode", () => {
    expect(plan('work in ("Éthique", "La voix et le phénomène")').metadata_filter).toEqual({
      work: { $in: ["Éthique", "La voix et le phénomène"] },
    });
    expect(plan('speaker not in ("Heidegger")').metadata_filter).toEqual({
      speaker: { $nin: ["Heidegger"] },
    });
    expect(plan("translated = true").metadata_filter).toEqual({ translated: { $eq: true } });
    expect(plan("page_start > -1").metadata_filter).toEqual({ page_start: { $gt: -1 } });
  });

  it("routes document predicates to the document filter and keeps or groups pure", () => {
    expect(plan('work = "A" and document contains "pharmakon"')).toEqual({
      metadata_filter: { work: { $eq: "A" } },
      document_filter: { $contains: "pharmakon" },
    });
    expect(plan('document not contains "editorial note"').document_filter).toEqual({
      $not_contains: "editorial note",
    });
    expect(errors('work = "A" or document contains "x"').code).toBe("mixed_document_and_metadata");
  });

  it("treats an empty expression as no filter", () => {
    expect(plan("   ")).toEqual({ metadata_filter: null, document_filter: null });
  });

  it("reports positioned errors instead of guessing", () => {
    expect(errors('author = "x"')).toMatchObject({ code: "unknown_field", position: 0 });
    expect(errors('work ~ "x"')).toMatchObject({ code: "unexpected_character", position: 5 });
    expect(errors('work = "x')).toMatchObject({ code: "unterminated_string" });
    expect(errors("work =").code).toBe("unexpected_end");
    expect(errors('work = "A" work = "B"').code).toBe("unexpected_token");
    expect(errors('page_start >= "late"').code).toBe("type_mismatch");
    expect(errors("work in ()").code).toBe("unexpected_token");
    expect(errors('work in ("A", 2)').code).toBe("mixed_list_types");
    expect(errors('work = "A" and (page_start > 1').code).toBe("unexpected_end");
  });

  it("does not accept function calls or arbitrary code", () => {
    expect(errors('work = "A" and alert(1)').code).toBe("unknown_field");
    expect(errors("work = x").code).toBe("unexpected_token");
  });

  it("enforces typed catalog fields", () => {
    const typed = [{ key: "page_start", type: "number" as const }];
    const result = parseResearchFilterExpression('page_start = "a"', typed);
    expect(result.ok).toBe(false);
  });

  it("explains a compiled plan as flat localizable clauses", () => {
    expect(explainResearchFilterPlan(plan('work = "A" and document contains "x"'))).toEqual([
      { field: "work", operator: "$eq", value: "A" },
      { field: "document", operator: "$contains", value: "x" },
    ]);
  });

  it("suggests fields, operators and connectives from the catalog", () => {
    const texts = (value: string) =>
      suggestResearchFilterCompletions(value, catalog).map((item) => item.text);
    expect(texts("")).toContain("work");
    expect(texts("wo")).toEqual(["work"]);
    expect(texts("work ")).toContain(">=");
    expect(texts("work = 'A' ")).toEqual(["and", "or"]);
    expect(texts("work = 'A' and sp")).toEqual(["speaker"]);
    expect(texts("document ")).toEqual(["contains", "not contains"]);
    expect(texts("work = ")).toEqual([]);
  });
});
