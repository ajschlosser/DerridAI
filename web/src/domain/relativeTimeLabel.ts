/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Tr, Trf } from "../i18n/bindCopy";

const FALLBACKS = {
  minutes: ["{count} minute ago", "{count} minutes ago"],
  hours: ["{count} hour ago", "{count} hours ago"],
  days: ["{count} day ago", "{count} days ago"],
} as const;

/**
 * "just now", "1 minute ago", "2 days ago". Each unit has a `_one` and `_other` key so every locale
 * can inflect the noun; only an exact count of one takes the singular (zero never reaches the units).
 */
export function relativeTimeLabel(
  value: unknown,
  nowMs: number,
  { tr, trf, locale }: { tr: Tr; trf: Trf; locale?: string },
): string {
  const date = new Date((value as string | number | Date) || 0);
  if (!Number.isFinite(date.getTime())) return tr("time.recently");
  const seconds = Math.max(0, Math.round((nowMs - date.getTime()) / 1000));
  if (seconds < 60) return tr("time.just_now");
  const count = (unit: keyof typeof FALLBACKS, n: number) => {
    const one = n === 1;
    return trf(`time.${unit}_ago_${one ? "one" : "other"}`, FALLBACKS[unit][one ? 0 : 1], {
      count: n.toLocaleString(locale || undefined),
    });
  };
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return count("minutes", minutes);
  const hours = Math.round(minutes / 60);
  if (hours < 24) return count("hours", hours);
  return count("days", Math.round(hours / 24));
}
