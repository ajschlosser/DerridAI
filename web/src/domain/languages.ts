/* Copyright 2026 Aaron John Schlosser, PhD. */
/**
 * Language display for sources and captures. Names come from the browser's CLDR data through
 * `Intl.DisplayNames`, in the interface locale; an unknown or malformed code is shown as the code
 * itself, never guessed. Languages are never represented by flags.
 */

const cache = new Map<string, Intl.DisplayNames | null>();

function displayNames(locale: string): Intl.DisplayNames | null {
  const key = locale || "en";
  if (!cache.has(key)) {
    try {
      cache.set(key, new Intl.DisplayNames([key], { type: "language" }));
    } catch {
      cache.set(key, null);
    }
  }
  return cache.get(key) ?? null;
}

/** "fr" → "French" (in English) or "français" (in French); the code when no name is known. */
export function languageName(code: string | null | undefined, locale = "en"): string {
  const value = String(code || "").trim();
  if (!value) return "";
  if (value === "und") return value;
  try {
    const name = displayNames(locale)?.of(value);
    return name && name.toLowerCase() !== value.toLowerCase() ? name : value;
  } catch {
    return value;
  }
}

/** Several languages as one label, in their given order: "Latin · English". */
export function languageList(codes: readonly string[] | null | undefined, locale = "en"): string {
  return (codes || [])
    .map((code) => languageName(code, locale))
    .filter(Boolean)
    .join(" · ");
}

/** Codes sorted by their display name in the interface locale. */
export function sortLanguageCodes(codes: Iterable<string>, locale = "en"): string[] {
  const collator = new Intl.Collator(locale || undefined);
  return [...new Set(codes)].sort((a, b) =>
    collator.compare(languageName(a, locale), languageName(b, locale)),
  );
}
