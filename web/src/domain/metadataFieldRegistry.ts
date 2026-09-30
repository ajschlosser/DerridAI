import { isPlaceholderValue } from "./metadataValues";
import type { SchemaField } from "../api/metadataSchemas";
export type MetadataControl =
  | "enum"
  | "combobox"
  | "multi-combobox"
  | "boolean"
  | "number"
  | "text";
export interface MetadataFieldSpec {
  control: MetadataControl;
  allowedValues?: string[];
  suggestionFields?: string[];
  allowCustom?: boolean;
}

const SPEAKER_FIELDS = [
  "speaker",
  "position_holder",
  "region_author",
  "document_author",
  "translator",
  "quoted_speaker",
  "quoted_author",
  "quoted_position_holder",
];
const TARGET_FIELDS = ["target", "quoted_addressee", "quoted_referent"];

/**
 * Compatibility contract for fields owned by DerridAI or records created before
 * a pinned metadata schema was available. Cardinality lives here in one place;
 * callers must not infer it from the runtime value shape or a field-name list.
 */
const LEGACY_FIELD_SPECS: Record<string, MetadataFieldSpec> = {
  semantic_function: {
    control: "multi-combobox",
    suggestionFields: ["semantic_function"],
    allowCustom: true,
  },
  quoted_speaker: { control: "combobox", suggestionFields: SPEAKER_FIELDS, allowCustom: true },
  quoted_author: { control: "combobox", suggestionFields: SPEAKER_FIELDS, allowCustom: true },
  quoted_work: {
    control: "combobox",
    suggestionFields: ["quoted_work", "works_referenced", "work", "document_title", "original_title"],
    allowCustom: true,
  },
  quoted_position_holder: {
    control: "combobox",
    suggestionFields: SPEAKER_FIELDS,
    allowCustom: true,
  },
  quoted_addressee: {
    control: "combobox",
    suggestionFields: [...TARGET_FIELDS, ...SPEAKER_FIELDS],
    allowCustom: true,
  },
  quoted_referent: {
    control: "combobox",
    suggestionFields: [...TARGET_FIELDS, ...SPEAKER_FIELDS],
    allowCustom: true,
  },
  quotation_chain: {
    control: "multi-combobox",
    suggestionFields: [
      "quotation_chain",
      "quoted_speaker",
      "quoted_author",
      "quoted_work",
      "quoted_position_holder",
    ],
    allowCustom: true,
  },
  topics: { control: "multi-combobox", suggestionFields: ["topics"], allowCustom: true },
  concepts: { control: "multi-combobox", suggestionFields: ["concepts"], allowCustom: true },
  persons: { control: "multi-combobox", suggestionFields: ["persons", ...SPEAKER_FIELDS], allowCustom: true },
  works_referenced: {
    control: "multi-combobox",
    suggestionFields: ["works_referenced", "quoted_work", "work", "document_title"],
    allowCustom: true,
  },
  institutions_referenced: {
    control: "multi-combobox",
    suggestionFields: ["institutions_referenced"],
    allowCustom: true,
  },
  locations_referenced: {
    control: "multi-combobox",
    suggestionFields: ["locations_referenced"],
    allowCustom: true,
  },
  events_referenced: {
    control: "multi-combobox",
    suggestionFields: ["events_referenced"],
    allowCustom: true,
  },
  groups_referenced: {
    control: "multi-combobox",
    suggestionFields: ["groups_referenced"],
    allowCustom: true,
  },
  languages_referenced: {
    control: "multi-combobox",
    suggestionFields: ["languages_referenced"],
    allowCustom: true,
  },
  document_language: {
    control: "combobox",
    suggestionFields: ["document_language", "original_language", "language"],
    allowCustom: true,
  },
  original_language: {
    control: "combobox",
    suggestionFields: ["original_language", "document_language", "language"],
    allowCustom: true,
  },
};

// Closed semantic vocabularies belong here. Open scholarly identifiers remain
// editable comboboxes even when the application can suggest known values.
export const PROPOSITION_STATUS_VALUES = [
  "asserted",
  "affirmed",
  "rejected",
  "criticized",
  "questioned",
  "qualified",
  "hypothetical",
  "attributed",
  "reported",
  "conceded",
  "suspended",
];
export const STANCE_VALUES = [
  "affirm",
  "reject",
  "criticize",
  "question",
  "qualify",
  "suspend",
  "neutral",
  "describe",
];

export const STANCE_ALIASES: Record<string, string> = {
  affirmed: "affirm",
  rejected: "reject",
  criticized: "criticize",
  questioned: "question",
  qualified: "qualify",
  suspended: "suspend",
  descriptive: "describe",
};

export function normalizeMetadataFieldValue(field: string, value: unknown): unknown {
  if (field !== "stance" || typeof value !== "string") return value;
  const normalized = value.trim().toLowerCase();
  if (STANCE_VALUES.includes(normalized)) return normalized;
  return STANCE_ALIASES[normalized] ?? value;
}

/** How a field defined by a metadata schema is edited. The locked core fields are handled by metadataFieldSpec itself. */
export function schemaFieldSpec(field: SchemaField): MetadataFieldSpec {
  if (field.type === "boolean") return { control: "boolean" };
  if (field.type === "number") return { control: "number" };
  if (field.type === "list")
    return { control: "multi-combobox", suggestionFields: [field.name], allowCustom: true };
  if (field.type === "choice") {
    const values = field.values.map((v) => v.value);
    return field.strict
      ? { control: "enum", allowedValues: values }
      : { control: "combobox", allowedValues: values, allowCustom: true };
  }
  return { control: "combobox", suggestionFields: [field.name], allowCustom: true };
}

export function metadataFieldSpec(
  field: string,
  regionTypes: string[],
  discourseRoles: string[],
  schemaField?: SchemaField,
): MetadataFieldSpec {
  if (schemaField && !["region_type", "primary_text", "discourse_role"].includes(field))
    return schemaFieldSpec(schemaField);
  if (field === "region_type") return { control: "enum", allowedValues: regionTypes };
  if (field === "discourse_role") return { control: "enum", allowedValues: discourseRoles };
  if (field === "proposition_status")
    return { control: "enum", allowedValues: PROPOSITION_STATUS_VALUES };
  if (field === "stance") return { control: "enum", allowedValues: STANCE_VALUES };
  if (field === "claim_scope")
    return { control: "combobox", suggestionFields: [field], allowCustom: true };
  if (
    field === "primary_text" ||
    field === "document_is_translation" ||
    field === "is_direct_quote"
  )
    return { control: "boolean" };
  if (field === "year" || field === "publication_year") return { control: "number" };
  const legacySpec = LEGACY_FIELD_SPECS[field];
  if (legacySpec)
    return {
      ...legacySpec,
      suggestionFields: legacySpec.suggestionFields ? [...legacySpec.suggestionFields] : undefined,
      allowedValues: legacySpec.allowedValues ? [...legacySpec.allowedValues] : undefined,
    };
  if (SPEAKER_FIELDS.includes(field))
    return { control: "combobox", suggestionFields: SPEAKER_FIELDS, allowCustom: true };
  if (TARGET_FIELDS.includes(field))
    return { control: "combobox", suggestionFields: TARGET_FIELDS, allowCustom: true };
  if (
    [
      "work",
      "document_title",
      "short_title",
      "original_title",
      "edition",
      "publisher",
      "publication_place",
      "isbn",
    ].includes(field)
  )
    return { control: "combobox", suggestionFields: [field], allowCustom: true };
  return { control: "text", allowCustom: true };
}

export function metadataSuggestions(
  record: Record<string, unknown>,
  fields: string[] = [],
): string[] {
  const out = new Set<string>();
  for (const field of fields) {
    const value = record[field];
    if (typeof value === "string" && !isPlaceholderValue(value)) out.add(value.trim());
    if (Array.isArray(value))
      for (const item of value)
        if (typeof item === "string" && !isPlaceholderValue(item)) out.add(item.trim());
  }
  return [...out].sort((a, b) => a.localeCompare(b));
}
