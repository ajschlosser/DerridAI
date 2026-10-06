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
import { researchFilterCatalog } from "../../src/domain/researchFilters";
import {
  appendFilterExpression,
  interpretResearchInstructionFilters,
} from "../../src/domain/researchInstructionFilters";

const catalog = researchFilterCatalog(["work", "speaker", "page_start", "year"]);
const inventory = {
  works: [
    { work: "Of Grammatology", authors: ["Jacques Derrida"] },
    { work: "Writing and Difference", authors: ["Jacques Derrida"] },
    { work: "Being and Time", authors: ["Martin Heidegger"] },
    { work: "Phenomenology of Spirit", authors: ["G. W. F. Hegel"] },
  ],
};
const run = (text: string, cat = catalog) =>
  interpretResearchInstructionFilters(text, inventory, cat);
const expressions = (text: string) => run(text).proposals.map((p) => p.expression);

describe("deterministic instruction filters", () => {
  it("turns 'only' into an inclusive scope", () => {
    expect(expressions("Only use Of Grammatology.")).toEqual(['work = "Of Grammatology"']);
    expect(expressions("Use only Of Grammatology and Being and Time")).toEqual([
      'work in ("Being and Time", "Of Grammatology")',
    ]);
  });

  it("turns exclusion into a negative scope, including via author", () => {
    expect(expressions("Exclude Being and Time")).toEqual(['work != "Being and Time"']);
    expect(expressions("exclude Derrida")).toEqual([
      'work not in ("Of Grammatology", "Writing and Difference")',
    ]);
  });

  it("handles 'use A but not B' as only an exclusion of B", () => {
    const result = run("Use Of Grammatology but not Being and Time");
    expect(result.proposals.map((p) => p.expression)).toEqual(['work != "Being and Time"']);
  });

  it("does not turn 'do not exclude' or 'not only' into filters", () => {
    const negated = run("Do not exclude Being and Time.");
    expect(negated.proposals).toEqual([]);
    expect(negated.unresolved[0].reason).toBe("negated_instruction");
    const notOnly = run("Not only Of Grammatology, but others too.");
    expect(notOnly.proposals).toEqual([]);
    expect(notOnly.unresolved[0].reason).toBe("not_only");
  });

  it("interprets speaker constraints, including exclusion as speaker", () => {
    expect(expressions("Speaker is Derrida")).toEqual(['speaker = "Derrida"']);
    expect(expressions("speaker is not Heidegger")).toEqual(['speaker != "Heidegger"']);
    expect(expressions("Exclude Heidegger as speaker.")).toEqual(['speaker != "Heidegger"']);
    expect(run("speaker is not Heidegger").proposals[0].verified).toBe(false);
  });

  it("interprets page and year bounds, refusing ambiguous numbers", () => {
    expect(expressions("pages after 100")).toEqual(["page_start > 100"]);
    expect(expressions("pages 140 to 100")).toEqual(["page_start >= 100 and page_start <= 140"]);
    expect(expressions("before 1970")).toEqual(["year < 1970"]);
    const ambiguous = run("after 50");
    expect(ambiguous.proposals).toEqual([]);
    expect(ambiguous.unresolved[0].reason).toBe("ambiguous_number");
  });

  it("keeps emphasis and unknown or partial scopes as unresolved instructions", () => {
    const soft = run("Focus especially on Derrida's early works.");
    expect(soft.proposals).toEqual([]);
    expect(soft.unresolved[0].reason).toBe("soft_preference");
    const unknown = run("Only use recent essays");
    expect(unknown.proposals).toEqual([]);
    expect(unknown.unresolved[0].reason).toBe("unknown_scope");
    const partial = run("Only Of Grammatology and recent essays");
    expect(partial.proposals).toEqual([]);
    expect(partial.unresolved[0].reason).toBe("partially_resolved");
  });

  it("never proposes a field the collection does not declare", () => {
    const result = run("Only Of Grammatology", researchFilterCatalog(["speaker"]));
    expect(result.proposals).toEqual([]);
    expect(result.unresolved[0]).toMatchObject({ reason: "field_unavailable" });
    expect(run("language is French").unresolved[0].reason).toBe("unsupported_field");
  });

  it("matches accented and possessive names", () => {
    const accented = interpretResearchInstructionFilters(
      "Only De la grammatologie",
      { works: [{ work: "De la grammatologie", authors: [] }] },
      catalog,
    );
    expect(accented.proposals[0].expression).toBe('work = "De la grammatologie"');
  });

  it("appends to an existing expression without changing its meaning", () => {
    expect(appendFilterExpression("", 'work = "A"')).toBe('work = "A"');
    expect(appendFilterExpression("a = 1 or b = 2", 'work = "A"')).toBe(
      '(a = 1 or b = 2) and work = "A"',
    );
    expect(appendFilterExpression('work = "A"', 'work = "A"')).toBe('work = "A"');
  });
});
