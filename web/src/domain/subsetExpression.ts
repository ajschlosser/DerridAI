/* Copyright 2026 Aaron John Schlosser, PhD. */
import { subsetRuleMatches, subsetValueText, type SubsetRule } from "./recordQuery";

/**
 * A subset filter expression: deterministic filtering of Records by their field values.
 *
 * The expression is a list of items joined left to right. AND binds tighter than OR, so
 * `a AND b OR c` means `(a AND b) OR c`. A group is one parenthesised item whose conditions are
 * combined by its own mode. The shape is persisted with each subset file (`logic` below) and in
 * saved filter profiles, so it must not change meaning without a new logic identifier.
 */
export const SUBSET_EXPRESSION_LOGIC = "grouped_boolean_v2";

export const SUBSET_OPERATORS = [
  "equals",
  "not_equals",
  "contains",
  "not_contains",
  "array_contains",
  "exists",
  "missing",
  "truthy",
  "falsy",
  "regex",
] as const;

/** Operators that test presence or truth only, so the condition has no value. */
export const VALUELESS_OPERATORS: ReadonlySet<string> = new Set([
  "exists",
  "missing",
  "truthy",
  "falsy",
]);

/** Long free-text fields: offering every distinct value as a suggestion would be useless and slow. */
const UNSUGGESTED_FIELDS: ReadonlySet<string> = new Set([
  "text",
  "extracted_text",
  "extractedText",
  "raw_text",
  "ocr_text",
]);

export type SubsetJoin = "AND" | "OR";
export type SubsetExpressionItem =
  | { type: "rule"; join: SubsetJoin; rule: SubsetRule }
  | { type: "group"; join: SubsetJoin; mode: SubsetJoin; rules: SubsetRule[] };

function itemMatches(
  record: Record<string, unknown>,
  item: SubsetExpressionItem,
  caseSensitive: boolean,
) {
  if (item.type === "rule") return subsetRuleMatches(record, item.rule, caseSensitive);
  const results = item.rules.map((rule) => subsetRuleMatches(record, rule, caseSensitive));
  return item.mode === "AND" ? results.every(Boolean) : results.some(Boolean);
}

/** Whether a Record satisfies the expression. An empty expression matches nothing. */
export function recordMatchesExpression(
  record: Record<string, unknown>,
  items: SubsetExpressionItem[],
  caseSensitive: boolean,
): boolean {
  if (!items.length) return false;
  // Split at each OR into runs of ANDed items; the Record matches when any run matches in full.
  const runs: SubsetExpressionItem[][] = [];
  for (const [index, item] of items.entries()) {
    if (index === 0 || item.join === "OR") runs.push([]);
    runs[runs.length - 1].push(item);
  }
  return runs.some((run) => run.every((item) => itemMatches(record, item, caseSensitive)));
}

/** Distinct scalar values of a field, for suggesting condition values; none for long text fields. */
export function fieldValueSuggestions(
  records: Iterable<Record<string, unknown>>,
  field: string,
  locale?: string,
): string[] {
  if (UNSUGGESTED_FIELDS.has(field)) return [];
  const values = new Set<string>();
  for (const record of records) {
    const raw = record?.[field];
    for (const item of Array.isArray(raw) ? raw : [raw]) {
      if (item === null || item === undefined || typeof item === "object") continue;
      const text = String(item).trim();
      if (text) values.add(text);
    }
  }
  return [...values].sort((a, b) =>
    a.localeCompare(b, locale, { numeric: true, sensitivity: "base" }),
  );
}

export function fieldHasSuggestions(field: string): boolean {
  return !UNSUGGESTED_FIELDS.has(field);
}

/** A readable one-line form of the expression, e.g. `Work equals “Glas” AND (Topics contains …)`. */
export function describeExpression(
  items: SubsetExpressionItem[],
  labels: { field: (key: string) => string; operator: (key: string) => string },
): string {
  const condition = (rule: SubsetRule) => {
    const head = `${labels.field(rule.field)} ${labels.operator(rule.operator)}`;
    return VALUELESS_OPERATORS.has(rule.operator)
      ? head
      : `${head} “${subsetValueText(rule.value)}”`;
  };
  return items
    .map((item, index) => {
      const prefix = index ? ` ${item.join} ` : "";
      if (item.type === "rule") return `${prefix}${condition(item.rule)}`;
      return `${prefix}(${item.rules.map(condition).join(` ${item.mode} `)})`;
    })
    .join("");
}
