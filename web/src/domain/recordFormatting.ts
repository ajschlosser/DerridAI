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

import { esc } from "./html";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

// Framework-light text highlighting, snippets, and model/similarity display helpers.

export function highlight(text: unknown, query: unknown): string {
  const source = String(text ?? "");
  const searchText = String(query ?? "");
  if (!searchText) return esc(source);

  const normalizedSource = source.toLocaleLowerCase();
  const normalizedSearchText = searchText.toLocaleLowerCase();
  let rendered = "";
  let searchFrom = 0;
  let matchIndex = normalizedSource.indexOf(normalizedSearchText, searchFrom);

  while (matchIndex >= 0) {
    rendered +=
      esc(source.slice(searchFrom, matchIndex)) +
      "<mark>" +
      esc(source.slice(matchIndex, matchIndex + searchText.length)) +
      "</mark>";
    searchFrom = matchIndex + Math.max(1, searchText.length);
    matchIndex = normalizedSource.indexOf(normalizedSearchText, searchFrom);
  }

  return rendered + esc(source.slice(searchFrom));
}

export function highlightTerms(text: unknown, query: unknown): string {
  const source = String(text ?? "");
  const terms = [
    ...new Set(
      String(query ?? "")
        .trim()
        .split(/\s+/)
        // eslint-disable-next-line no-useless-escape -- SA-14: preserve legacy matching until dedicated text fixtures cover it.
        .map((term) => term.replace(/^[\"'()\[\]{}]+|[\"'()\[\]{},.;:!?]+$/g, ""))
        .filter((term) => term.length > 1),
    ),
  ].sort((left, right) => right.length - left.length);
  if (!terms.length) return esc(source);

  const escapedTerms = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escapedTerms.join("|")})`, "gi");
  let rendered = "";
  let previousMatchEnd = 0;
  let match = pattern.exec(source);

  while (match) {
    rendered +=
      esc(source.slice(previousMatchEnd, match.index)) + `<mark>${esc(match[0])}</mark>`;
    previousMatchEnd = match.index + match[0].length;

    // Defensive guard for a future pattern that could match an empty string.
    if (!match[0].length) pattern.lastIndex += 1;
    match = pattern.exec(source);
  }

  return rendered + esc(source.slice(previousMatchEnd));
}

export function snippet(text: unknown, query?: string | null, max: number = 430): string {
  const source = String(text ?? "")
    .replace(/\s+/g, " ")
    .trim();
  if (!source) return "";
  if (!query) return source.length > max ? source.slice(0, max) + "…" : source;

  const matchIndex = source.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
  if (matchIndex < 0) return source.length > max ? source.slice(0, max) + "…" : source;

  const startIndex = Math.max(0, matchIndex - Math.floor(max / 2));
  const endIndex = Math.min(source.length, startIndex + max);
  return (
    (startIndex ? "…" : "") +
    source.slice(startIndex, endIndex) +
    (endIndex < source.length ? "…" : "")
  );
}

/**
 * Convert a Chroma distance to a monotonic display score.
 *
 * The result is deliberately not presented as a calibrated probability; it
 * only makes smaller distances read naturally on a 0..1 display scale.
 */
export function semanticSimilarity(distance: unknown): number | null {
  const parsedDistance = Number(distance);
  if (!Number.isFinite(parsedDistance)) return null;
  return 1 / (1 + Math.max(0, parsedDistance));
}

export function modelOptionLabel(model: Loose): string {
  const modelDetails = [];
  if (model.parameter_size) modelDetails.push(model.parameter_size);
  if (model.quantization_level) modelDetails.push(model.quantization_level);
  return modelDetails.length ? `${model.name} · ${modelDetails.join(" · ")}` : model.name;
}

export function openAiModelMatchesKind(name: unknown, kind: string | null | undefined): boolean {
  if (!kind || kind === "any") return true;

  const normalizedName = String(name || "").toLocaleLowerCase();
  const kindPatterns: Record<string, string[]> = {
    reasoning: ["reason", "deepseek", "r1", "qwq", "o1", "o3", "thinking"],
    coding: ["code", "coder", "codex", "devstral", "starcoder"],
    fast: ["mini", "small", "flash", "haiku", "fast", "3b", "4b", "7b", "8b"],
    general: ["gpt", "gemma", "llama", "qwen", "mistral", "claude", "general", "chat"],
  };
  return (kindPatterns[kind] || []).some((token) => normalizedName.includes(token));
}
