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

/**
 * Deterministic interpretation of Research instructions into proposed hard filters.
 *
 * Only phrases whose meaning maps with high confidence onto a typed constraint are
 * proposed ("only", "exclude", "speaker is (not)", "pages after/N to M",
 * "before/after <year>"). Everything else (emphasis, "early works", partially
 * resolvable scopes, negated negations) is reported as unresolved and stays an
 * ordinary instruction. A proposal is never applied silently: the caller shows it
 * and the researcher confirms; the server validates the resulting plan again.
 *
 * Work/author resolution uses the collection's actual inventory, and field keys
 * resolve through the collection's field catalog, so no field is assumed to exist.
 */

import { parseResearchFilterExpression } from "./researchFilters";
import type { ResearchFilterField } from "./researchFilters";

export type ScopeInventory = {
  works: Array<{ work: string; authors: string[] }>;
};

export type InstructionFilterProposal = {
  id: string;
  /** The instruction text the proposal came from. */
  phrase: string;
  /** Expression in the explicit filter grammar. */
  expression: string;
  /** Whether every value was resolved against the corpus inventory. */
  verified: boolean;
};

export type InstructionUnresolvedReason =
  | "soft_preference"
  | "negated_instruction"
  | "not_only"
  | "unknown_scope"
  | "partially_resolved"
  | "field_unavailable"
  | "unsupported_field"
  | "too_many_works"
  | "ambiguous_number";

export type InstructionUnresolved = {
  phrase: string;
  reason: InstructionUnresolvedReason;
  params: Record<string, string>;
};

export type InstructionInterpretation = {
  proposals: InstructionFilterProposal[];
  unresolved: InstructionUnresolved[];
};

/** Concepts resolve to the first indexed key the collection actually declares. */
const CONCEPT_KEYS = {
  work: ["work"],
  speaker: ["speaker"],
  page: ["page_start"],
  year: ["year", "publication_year"],
} as const;
type Concept = keyof typeof CONCEPT_KEYS;

const MAX_SCOPE_WORKS = 50;
const SOFT_MARKERS =
  /\b(?:especially|mainly|mostly|primarily|particularly|focus(?:ing)?|prefer(?:ably)?|early|late|representative|where useful|emphasi[sz]e|surtout|principalement)\b/u;
const FILLER = new Set(
  (
    "use using the from in on of work works text texts book books by and or et ou le la les des du de " +
    "a an to as is are only just solely please answer based drawing include including only uniquement seulement " +
    "utiliser utilise that which"
  ).split(" "),
);
// "only" and "exclude" markers (EN + FR). "not only" is handled before these apply.
const MARKER =
  /\b(?:(only|solely|uniquement|seulement)|(exclude|excluding|omit|ignore|skip|avoid|do not use|don't use|dont use|but not|and not|except|sauf|exclure))\b/giu;

function fold(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[’']s\b/gu, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function quote(value: string): string {
  return `"${value.replace(/\\/gu, "\\\\").replace(/"/gu, '\\"')}"`;
}

function resolveKey(concept: Concept, catalog: ResearchFilterField[]): string | null {
  const keys = new Set(catalog.map((field) => field.key));
  return CONCEPT_KEYS[concept].find((key) => keys.has(key)) ?? null;
}

type NameMatch = { works: string[]; leftover: string[]; names: string[] };

/** Match known works/authors in `tail`; remaining non-filler words are `leftover`. */
function matchNames(tail: string, inventory: ScopeInventory): NameMatch {
  let rest = ` ${fold(tail)} `;
  const works = new Set<string>();
  const names: string[] = [];
  const candidates: Array<{ label: string; norm: string; works: string[] }> = [];
  const authorWorks = new Map<string, { label: string; works: Set<string> }>();
  for (const entry of inventory.works) {
    const norm = fold(entry.work);
    if (norm) candidates.push({ label: entry.work, norm, works: [entry.work] });
    for (const author of entry.authors) {
      const key = fold(author);
      if (!key) continue;
      const slot = authorWorks.get(key) ?? { label: author, works: new Set<string>() };
      slot.works.add(entry.work);
      authorWorks.set(key, slot);
    }
  }
  for (const [norm, slot] of authorWorks) {
    candidates.push({ label: slot.label, norm, works: [...slot.works] });
    const surname = norm.split(" ").at(-1) ?? "";
    if (surname.length >= 4 && surname !== norm) {
      candidates.push({ label: slot.label, norm: surname, works: [...slot.works] });
    }
  }
  // Longest names first so a work title is consumed before a shorter author surname.
  candidates.sort((a, b) => b.norm.length - a.norm.length);
  for (const candidate of candidates) {
    const needle = ` ${candidate.norm} `;
    if (!rest.includes(needle)) continue;
    rest = rest.split(needle).join(" ");
    candidate.works.forEach((work) => works.add(work));
    names.push(candidate.label);
  }
  const leftover = rest
    .split(" ")
    .filter((word) => word && !FILLER.has(word) && !/^\d+$/u.test(word));
  return { works: [...works].sort((a, b) => a.localeCompare(b)), leftover, names };
}

function listExpression(key: string, values: string[], negated: boolean): string {
  if (values.length === 1) return `${key} ${negated ? "!=" : "="} ${quote(values[0])}`;
  return `${key} ${negated ? "not in" : "in"} (${values.map(quote).join(", ")})`;
}

class Collector {
  readonly proposals: InstructionFilterProposal[] = [];
  readonly unresolved: InstructionUnresolved[] = [];
  private seen = new Set<string>();
  constructor(private readonly catalog: ResearchFilterField[]) {}

  propose(phrase: string, expression: string, verified: boolean) {
    // Re-validate through the one grammar so a proposal is always an executable filter.
    const parsed = parseResearchFilterExpression(expression, this.catalog);
    if (!parsed.ok || this.seen.has(expression)) return;
    this.seen.add(expression);
    this.proposals.push({ id: `p${this.proposals.length + 1}`, phrase, expression, verified });
  }
  skip(phrase: string, reason: InstructionUnresolvedReason, params: Record<string, string> = {}) {
    this.unresolved.push({ phrase, reason, params });
  }
  key(concept: Concept, phrase: string): string | null {
    const key = resolveKey(concept, this.catalog);
    if (!key) this.skip(phrase, "field_unavailable", { concept });
    return key;
  }
}

function scopeSegment(
  out: Collector,
  inventory: ScopeInventory,
  phrase: string,
  tail: string,
  negated: boolean,
) {
  const matched = matchNames(tail, inventory);
  if (matched.leftover.length) {
    out.skip(phrase, matched.works.length ? "partially_resolved" : "unknown_scope", {
      text: matched.leftover.join(" "),
    });
    return;
  }
  if (!matched.works.length) {
    out.skip(phrase, "unknown_scope", { text: tail.trim() });
    return;
  }
  if (matched.works.length > MAX_SCOPE_WORKS) {
    out.skip(phrase, "too_many_works", { count: String(matched.works.length) });
    return;
  }
  const key = out.key("work", phrase);
  if (key) out.propose(phrase, listExpression(key, matched.works, negated), true);
}

function numericClauses(out: Collector, sentence: string): boolean {
  const pageWord = /\bpages?\b|\bpp?\.\s*\d|\bpage\b/iu.test(sentence);
  const range =
    /\b(?:pages?|pp?\.?)\s*(\d{1,5})\s*(?:to|through|-|–|—|and)\s*(\d{1,5})\b/iu.exec(sentence) ||
    /\bbetween\s+pages?\s+(\d{1,5})\s+and\s+(\d{1,5})\b/iu.exec(sentence);
  if (range) {
    const [low, high] = [Number(range[1]), Number(range[2])].sort((a, b) => a - b);
    const key = out.key("page", range[0]);
    if (key) out.propose(range[0], `${key} >= ${low} and ${key} <= ${high}`, true);
    return true;
  }
  const bound = /\b(before|after|since|until|avant|apres|après)\s+(?:page\s+)?(\d{1,5})\b/iu.exec(
    sentence,
  );
  if (!bound) return false;
  const value = Number(bound[2]);
  const operator = /^(before|until|avant)$/iu.test(bound[1]) ? "<" : ">";
  const isYear = !pageWord && value >= 1000 && value <= 2999;
  if (!isYear && !pageWord) {
    out.skip(bound[0], "ambiguous_number", { value: String(value) });
    return true;
  }
  const key = out.key(isYear ? "year" : "page", bound[0]);
  if (key) out.propose(bound[0], `${key} ${operator} ${value}`, true);
  return true;
}

function speakerValues(text: string): string[] {
  return text
    .split(/\s*(?:,|\bor\b|\band\b)\s*/iu)
    .map((part) => part.trim().replace(/^["“”']|["“”']$/gu, ""))
    .filter(Boolean);
}

function speakerClause(out: Collector, sentence: string): boolean {
  const text = sentence.trim().replace(/[.!?]+$/u, "");
  let negated = false;
  let list = "";
  let match = /\bspeaker\s+(?:isn't|is not|≠)\s+([^,;]+)$/iu.exec(text);
  if (match) {
    negated = true;
    list = match[1];
  } else if ((match = /\bspeaker\s+(?:is|=|equals)\s+([^,;]+)$/iu.exec(text))) {
    list = match[1];
  } else if (
    (match = /\b(?:exclude|omit|ignore|skip)\s+(.+?)\s+as\s+(?:the\s+)?speakers?\b/iu.exec(text))
  ) {
    negated = true;
    list = match[1];
  } else if ((match = /\bonly\s+(.+?)\s+as\s+(?:the\s+)?speakers?\b/iu.exec(text))) {
    list = match[1];
  }
  if (!match) return false;
  const values = speakerValues(list);
  if (!values.length) return false;
  const key = out.key("speaker", match[0]);
  if (key) out.propose(match[0], listExpression(key, values, negated), false);
  return true;
}

function interpretSentence(out: Collector, inventory: ScopeInventory, raw: string) {
  const sentence = raw.replace(/[’]/gu, "'").replace(/\s+/gu, " ").trim();
  if (!sentence) return;

  if (/\blanguage\s+(?:is|=)\b/iu.test(sentence)) {
    out.skip(sentence, "unsupported_field", { concept: "language" });
    return;
  }
  if (/\bnot\s+only\b|\bpas\s+seulement\b/iu.test(sentence)) {
    out.skip(sentence, "not_only");
    return;
  }
  if (
    /\b(?:do not|don't|dont|never|no need to)\s+(?:exclude|omit|ignore|skip|avoid)\b/iu.test(
      sentence,
    )
  ) {
    out.skip(sentence, "negated_instruction");
    return;
  }

  const speaker = speakerClause(out, sentence);
  let handled = numericClauses(out, sentence) || speaker;

  const markers = [...sentence.matchAll(MARKER)];
  if (markers.length && !speaker) {
    markers.forEach((marker, index) => {
      const start = (marker.index ?? 0) + marker[0].length;
      const end = markers[index + 1]?.index ?? sentence.length;
      const tail = sentence.slice(start, end);
      scopeSegment(
        out,
        inventory,
        sentence.slice(marker.index, end).trim(),
        tail,
        Boolean(marker[2]),
      );
    });
    handled = true;
  }
  if (!handled && SOFT_MARKERS.test(sentence)) out.skip(sentence, "soft_preference");
}

export function interpretResearchInstructionFilters(
  text: string,
  inventory: ScopeInventory,
  catalog: ResearchFilterField[],
): InstructionInterpretation {
  const out = new Collector(catalog);
  for (const sentence of text.split(/(?<=[.!?;])\s+|\n+/u)) {
    interpretSentence(out, inventory, sentence);
  }
  return { proposals: out.proposals, unresolved: out.unresolved };
}

/** Append a confirmed proposal to an existing expression, preserving its meaning. */
export function appendFilterExpression(existing: string, addition: string): string {
  const base = existing.trim();
  if (!base) return addition;
  if (base.includes(addition)) return base;
  const left = /\bor\b/iu.test(base) ? `(${base})` : base;
  const right = /\bor\b/iu.test(addition) ? `(${addition})` : addition;
  return `${left} and ${right}`;
}
