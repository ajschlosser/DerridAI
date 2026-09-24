/* Copyright 2026 Aaron John Schlosser, PhD. */
import { englishDefault } from "./englishDefault";

export type Tr = (key: string, fallback?: string) => string;
export type Values = Record<string, unknown>;
export type Trf = (key: string, fallbackOrValues?: string | Values, values?: Values) => string;
type RawTrf = (key: string, fallback: string, values?: Values) => string;

/**
 * Bind tr/trf so call sites pass a key (and interpolations). English comes from
 * enUsDefaults.json, exported from api/app/locales/en_us.py.
 */
export function bindCopy(tr: Tr, trf: RawTrf) {
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
