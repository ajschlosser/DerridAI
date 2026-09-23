/* Copyright 2026 Aaron John Schlosser, PhD. */
import { englishDefault } from "./englishDefault";

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;
type Values = Record<string, unknown>;

/**
 * Bind tr/trf so call sites pass a key (and interpolations). English comes from
 * enUsDefaults.json, exported from api/app/locales/en_us.py.
 */
export function bindCopy(tr: Tr, trf: Trf) {
  const t = (key: string, fallback?: string) => tr(key, fallback || englishDefault(key) || key);
  const tf = (key: string, fallbackOrValues?: string | Values, values?: Values) => {
    if (fallbackOrValues && typeof fallbackOrValues === "object") {
      return trf(key, englishDefault(key) || key, fallbackOrValues);
    }
    return trf(
      key,
      (typeof fallbackOrValues === "string" && fallbackOrValues) || englishDefault(key) || key,
      values || {},
    );
  };
  return { t, tf, tr: t, trf: tf };
}
