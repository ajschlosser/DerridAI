/* Copyright 2026 Aaron John Schlosser, PhD. */

import type {
  RecordEditorField,
  RecordEditorFieldKind,
} from "../composables/recordFieldEditorDialog";

/** Fields whose values are long prose, so they span the whole editor grid. */
const FULL_WIDTH_FIELDS = new Set([
  "text",
  "edition",
  "review_reason",
  "full_citation",
  "quotation_chain",
]);

/** How a value is edited: arrays and objects as JSON, the `text` field as a large text area. */
export function recordEditorKind(key: string, value: unknown): RecordEditorFieldKind {
  if (typeof value === "boolean") return "boolean";
  if (key === "text") return "text";
  if (Array.isArray(value) || (value !== null && typeof value === "object")) return "json";
  if (typeof value === "number") return "number";
  if (value === null) return "null";
  return "string";
}

export function recordEditorField(
  key: string,
  value: unknown,
  label: (key: string) => string,
): RecordEditorField {
  return {
    key,
    label: label(key),
    kind: recordEditorKind(key, value),
    value,
    full: FULL_WIDTH_FIELDS.has(key),
  };
}

/** The text a field's control starts with. */
export function recordEditorText(field: Pick<RecordEditorField, "kind" | "value">): string {
  if (field.kind === "json") return JSON.stringify(field.value, null, 2) ?? "";
  if (field.kind === "boolean") return "";
  return String(field.value ?? "");
}

/** Turn a control's text (or checked state) back into a value. JSON that does not parse throws. */
export function parseRecordEditorValue(
  kind: RecordEditorFieldKind,
  text: string,
  checked: boolean,
): unknown {
  if (kind === "boolean") return checked;
  if (kind === "number") return text === "" ? null : Number(text);
  if (kind === "null") return text === "" ? null : text;
  if (kind === "json") return JSON.parse(text);
  return text;
}
