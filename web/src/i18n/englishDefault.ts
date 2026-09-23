/* Copyright 2026 Aaron John Schlosser, PhD. */
import enUsDefaults from "./enUsDefaults.json";

const EN_US_DEFAULTS = enUsDefaults as Record<string, string>;

/** Canonical English for a UI key. Source of truth is api/app/locales/en_us.py. */
export function englishDefault(key: string): string {
  return EN_US_DEFAULTS[key] || "";
}

export { EN_US_DEFAULTS };
