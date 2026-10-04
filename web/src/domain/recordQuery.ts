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

// Pure record parsing, matching, and text helpers shared by record-oriented views.

type JsonObject = Record<string, unknown>;

const errorMessage = (error: unknown): string =>
  error instanceof Error ? error.message : String(error);

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseJsonl(text: string): { records: JsonObject[]; errors: string[] } {
  const records: JsonObject[] = [];
  const errors: string[] = [];
  const trimmedText = text.trim();
  if (!trimmedText) return { records, errors };

  if (trimmedText.startsWith("[")) {
    try {
      const parsedRoot = JSON.parse(trimmedText);
      if (!Array.isArray(parsedRoot)) throw Error("Root is not an array");

      parsedRoot.forEach((item, itemIndex) => {
        if (isJsonObject(item)) {
          records.push(item);
        } else {
          errors.push(`Item ${itemIndex + 1}: not an object`);
        }
      });
      return { records, errors };
    } catch (error) {
      return { records, errors: [errorMessage(error)] };
    }
  }

  text.split(/\r?\n/).forEach((line, lineIndex) => {
    if (!line.trim()) return;
    try {
      const parsedLine = JSON.parse(line);
      if (isJsonObject(parsedLine)) {
        records.push(parsedLine);
      } else {
        errors.push(`Line ${lineIndex + 1}: not an object`);
      }
    } catch (error) {
      errors.push(`Line ${lineIndex + 1}: ${errorMessage(error)}`);
    }
  });
  return { records, errors };
}

export function flattenValueList(value: unknown): string[] {
  if (value == null) return [];
  if (Array.isArray(value)) return value.flatMap(flattenValueList);
  if (typeof value === "object") return Object.values(value as object).flatMap(flattenValueList);
  const text = String(value).trim();
  if (!text) return [];
  if (
    (text.startsWith("[") && text.endsWith("]")) ||
    (text.startsWith("{") && text.endsWith("}"))
  ) {
    try {
      return flattenValueList(JSON.parse(text));
    } catch {
      // Not valid JSON; fall through to the delimiter handling below.
    }
  }
  // Legacy corpus files have used newline, semicolon, pipe, and CSV-like
  // encodings for list metadata. Normalize them once so every badge surface
  // receives a stable list rather than rendering serialized arrays as a chip.
  if (/[\n;|]/.test(text))
    return text
      .split(/[\n;|]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  // Commas are intentionally not treated as a universal list separator: person
  // names and bibliographic values commonly contain commas. Legacy list fields
  // should use JSON arrays, semicolons, pipes, or line breaks.
  return [text];
}

export function countOccurrences(text: unknown, query: unknown): number {
  if (!query) return 0;

  const haystack = String(text).toLocaleLowerCase();
  const needle = String(query).toLocaleLowerCase();
  let searchFrom = 0;
  let occurrenceCount = 0;
  let matchIndex = haystack.indexOf(needle, searchFrom);

  while (matchIndex >= 0) {
    occurrenceCount += 1;
    searchFrom = matchIndex + Math.max(needle.length, 1);
    matchIndex = haystack.indexOf(needle, searchFrom);
  }
  return occurrenceCount;
}

/** Filter-row matching for the operators `empty`, `notempty`, `eq`, `neq`, `has`, `nhas`, `gte` and `lte`. */
export function valueMatches(value: unknown, operator: string, operand: unknown): boolean {
  const isEmpty =
    value == null || value === "" || (Array.isArray(value) && !value.length);
  if (operator === "empty") return isEmpty;
  if (operator === "notempty") return !isEmpty;

  const candidateValues: unknown[] = Array.isArray(value) ? value : [value];
  const normalizedOperand = String(operand ?? "").toLocaleLowerCase();
  const normalize = (candidate: unknown) => String(candidate ?? "").toLocaleLowerCase();

  if (operator === "eq")
    return candidateValues.some((candidate) => normalize(candidate) === normalizedOperand);
  if (operator === "neq")
    return !candidateValues.some((candidate) => normalize(candidate) === normalizedOperand);
  if (operator === "has")
    return candidateValues.some((candidate) => normalize(candidate).includes(normalizedOperand));
  if (operator === "nhas")
    return !candidateValues.some((candidate) => normalize(candidate).includes(normalizedOperand));
  if (operator === "gte")
    return candidateValues.some((candidate) => Number(candidate) >= Number(operand));
  if (operator === "lte")
    return candidateValues.some((candidate) => Number(candidate) <= Number(operand));
  return true;
}

export function subsetValueText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(subsetValueText).join(" ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export interface SubsetRule {
  field: string;
  operator: string;
  value?: unknown;
}

export function subsetRuleMatches(
  record: JsonObject | null | undefined,
  rule: SubsetRule,
  caseSensitive = false,
): boolean {
  const fieldValue = record?.[rule.field];
  const rawRuleValue = String(rule.value ?? "");
  const normalize = (text: unknown) =>
    caseSensitive ? String(text) : String(text).toLocaleLowerCase();
  const normalizedFieldText = normalize(subsetValueText(fieldValue));
  const normalizedRuleValue = normalize(rawRuleValue);

  switch (rule.operator) {
    case "equals":
      return Array.isArray(fieldValue)
        ? fieldValue.some(
            (item) => normalize(subsetValueText(item)) === normalizedRuleValue,
          )
        : normalizedFieldText === normalizedRuleValue;
    case "not_equals":
      return Array.isArray(fieldValue)
        ? !fieldValue.some(
            (item) => normalize(subsetValueText(item)) === normalizedRuleValue,
          )
        : normalizedFieldText !== normalizedRuleValue;
    case "contains":
      return normalizedFieldText.includes(normalizedRuleValue);
    case "not_contains":
      return !normalizedFieldText.includes(normalizedRuleValue);
    case "array_contains":
      return (
        Array.isArray(fieldValue) &&
        fieldValue.some(
          (item) => normalize(subsetValueText(item)) === normalizedRuleValue,
        )
      );
    case "exists":
      return (
        fieldValue !== undefined &&
        fieldValue !== null &&
        subsetValueText(fieldValue) !== ""
      );
    case "missing":
      return (
        fieldValue === undefined ||
        fieldValue === null ||
        subsetValueText(fieldValue) === ""
      );
    case "truthy":
      return Boolean(fieldValue);
    case "falsy":
      return !fieldValue;
    case "regex":
      try {
        return new RegExp(rawRuleValue, caseSensitive ? "" : "i").test(
          subsetValueText(fieldValue),
        );
      } catch {
        return false;
      }
    default:
      return false;
  }
}
