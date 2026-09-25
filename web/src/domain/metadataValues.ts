// Values that are not answers: "null", "N/A", "the author of the current record". Mirrors
// api/app/metadata_values.py, which drops them where a model's proposal is read; this drops any that were
// stored before that (or typed by hand) from the options a dropdown offers.
const NOTHING = new Set([
  "null",
  "none",
  "nil",
  "undefined",
  "nan",
  "n/a",
  "na",
  "n.a.",
  "n.a",
  "unknown",
  "unspecified",
  "unnamed",
  "untitled",
  "not specified",
  "not stated",
  "not applicable",
  "not available",
  "not provided",
  "not given",
  "not mentioned",
  "not identified",
  "not identifiable",
  "no value",
  "no author",
  "no speaker",
  "tbd",
  "todo",
  "empty",
  "blank",
  "-",
  "--",
  "—",
  "–",
  "?",
  "??",
]);
const ROLES =
  "author|speaker|writer|narrator|person|record|text|passage|document|book|work|source|party|individual|figure|reader|interlocutor|voice|subject|object|entity|thing|topic|concept|idea|position|claim|argument|excerpt|section|chapter|quotation|quote";
const WHERE = `(?:of|in|from|for|within|at)\\s+(?:the|this|that)\\s+(?:current\\s+|present\\s+|given\\s+)?(?:${ROLES})`;
const GENERIC = new RegExp(
  `^(?:(?:the|this|that|an?|current|present|same|given)\\s+)+(?:(?:current|present|same|main|primary|original|unnamed|unknown|anonymous|implied|implicit|general|generic|specific|relevant|previous|prior|other|another|first|second)\\s+)*(?:${ROLES})(?:s)?(?:\\s+${WHERE})?$` +
    `|^(?:unknown|unnamed|anonymous|unidentified|unspecified|generic|implied|implicit)\\s+(?:${ROLES})$` +
    `|^(?:${ROLES})\\s+(?:unknown|unnamed|not\\s+(?:specified|stated|named|identified))$` +
    `|^(?:the\\s+)?(?:${ROLES})\\s+${WHERE}$`,
  "i",
);
export function isPlaceholderValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value !== "string") return false;
  const plain = value
    .trim()
    .replace(/^["'“”‘’`.,;:()[\]{}<>]+|["'“”‘’`.,;:()[\]{}<>]+$/g, "")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();
  return !plain || NOTHING.has(plain) || GENERIC.test(plain);
}
/** Options for a dropdown: trimmed, without placeholders, without duplicates. */
export function usableOptions(values: Iterable<unknown>): string[] {
  const out = new Set<string>();
  for (const value of values)
    if (isUsableMetadataSuggestion(value)) out.add(value.trim());
  return [...out];
}

/** Expand list-field values without splitting prose fields that may contain commas. */
export function usableListOptions(values: Iterable<unknown>): string[] {
  const expanded: string[] = [];
  for (const raw of values) {
    const value = unwrapMetadataValue(raw);
    if (Array.isArray(value)) expanded.push(...value);
    else if (typeof value === "string") {
      if (!looksLikeRuntimeFragment(value)) expanded.push(...value.split(/[,\n]/));
    } else expanded.push(value as never);
  }
  return usableOptions(expanded);
}


/**
 * Unwrap the common accidental envelope shape produced by older compatibility
 * projections. Scholarly field values themselves are scalar/list values; audit
 * objects belong in assertion/status metadata rather than the editable value.
 */
export function unwrapMetadataValue(value: unknown): unknown {
  if (
    value &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.prototype.hasOwnProperty.call(value, "value")
  ) {
    const inner = (value as Record<string, unknown>).value;
    if (
      inner === null ||
      ["string", "number", "boolean"].includes(typeof inner) ||
      Array.isArray(inner)
    ) {
      return inner;
    }
  }
  return value;
}

function looksLikeRuntimeFragment(value: string): boolean {
  const text = value.trim();
  if (!text) return true;
  if (/^p\d{3,}-b\d{3,}$/i.test(text) || /^b\d{3,}$/i.test(text)) return true;
  if (
    /"(?:block_ids|confidence|needs_review|reason|outcome|field_evidence|field_assessments)"\s*:/i.test(
      text,
    )
  )
    return true;
  if (/^(?:\[|\]|\{|\})",?$/.test(text) || /^(?:\[|\]|\{|\})/.test(text) || /(?:\[|\]|\{|\})$/.test(text))
    return true;
  if (/^["'][^"']+["']\s*:\s*/.test(text)) return true;
  return false;
}

/** A candidate suitable for human-facing metadata autocomplete. */
export function isUsableMetadataSuggestion(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const text = value.trim();
  return (
    text.length > 0 &&
    text.length <= 240 &&
    !isPlaceholderValue(text) &&
    !looksLikeRuntimeFragment(text)
  );
}

/** Human-readable fallback that never leaks JavaScript's "[object Object]". */
export function metadataValueText(value: unknown): string {
  const unwrapped = unwrapMetadataValue(value);
  if (Array.isArray(unwrapped))
    return unwrapped
      .map((item) =>
        item && typeof item === "object" ? JSON.stringify(item) : String(item ?? ""),
      )
      .filter(Boolean)
      .join(", ");
  if (unwrapped === null || unwrapped === undefined || unwrapped === "") return "";
  if (typeof unwrapped === "object") {
    try {
      return JSON.stringify(unwrapped);
    } catch {
      return "";
    }
  }
  return String(unwrapped);
}
