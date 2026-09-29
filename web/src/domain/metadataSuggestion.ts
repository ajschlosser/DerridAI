// Copyright 2026 Aaron John Schlosser, PhD.
import { unwrapMetadataValue } from "./metadataValues";

/**
 * The value(s) the model proposed for a field, as trimmed strings, so option lists can lead with them.
 *
 * Order of trust: an explicit `llm_value`, then a model-made `proposed_value`, then the record's own value when the
 * model produced it. A value a human or the manifest supplied is never called a model suggestion.
 */
export function suggestedValues(
  status: Record<string, unknown> | undefined,
  recordValue: unknown,
  isModelValue: boolean,
  hasValue: (value: unknown) => boolean,
): string[] {
  const s = status || {};
  const raw = hasValue(s.llm_value)
    ? s.llm_value
    : isModelValue && hasValue(s.proposed_value)
      ? s.proposed_value
      : isModelValue && hasValue(recordValue)
        ? recordValue
        : null;
  if (raw == null) return [];
  const values = Array.isArray(raw) ? raw : [raw];
  return values.map((item) => String(unwrapMetadataValue(item) ?? "").trim()).filter(Boolean);
}

/**
 * Split a closed vocabulary into the suggested options and the rest. Every option appears exactly once, in its
 * original order within each group, so a suggestion can lead the list without removing or reordering anything else.
 */
export function groupOptionsBySuggestion(
  options: string[],
  suggested: string[],
): { suggested: string[]; others: string[] } {
  const wanted = new Set(suggested.map(optionKey));
  return {
    suggested: options.filter((option) => wanted.has(optionKey(option))),
    others: options.filter((option) => !wanted.has(optionKey(option))),
  };
}

/** Case/separator-insensitive identity, so a model's "Close Reading" still names the option `close_reading`. */
const optionKey = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .replace(/[\s_-]+/g, "_");

/** The closed-vocabulary option a value names, or `undefined` when it names none. */
export function matchOption(options: string[], value: string): string | undefined {
  if (!value.trim()) return undefined;
  const key = optionKey(value);
  return options.find((option) => option === value) ?? options.find((o) => optionKey(o) === key);
}
