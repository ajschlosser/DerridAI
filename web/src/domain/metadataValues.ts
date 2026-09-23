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
    if (typeof value === "string" && !isPlaceholderValue(value)) out.add(value.trim());
  return [...out];
}

/** Expand list-field values without splitting prose fields that may contain commas. */
export function usableListOptions(values: Iterable<unknown>): string[] {
  const expanded: string[] = [];
  for (const value of values) {
    if (Array.isArray(value)) expanded.push(...value);
    else if (typeof value === "string") expanded.push(...value.split(/[,\n]/));
    else expanded.push(value as never);
  }
  return usableOptions(expanded);
}
