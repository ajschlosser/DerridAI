/* Copyright 2026 Aaron John Schlosser, PhD. */

/**
 * Column widths for configurable tables, as percentages of the space the data columns share.
 * The shown columns always total 100%: widening one narrows the others in proportion to their
 * current widths, and no column goes below MIN_COLUMN_PERCENT.
 */
export type ColumnWidths = Record<string, number>;

export const MIN_COLUMN_PERCENT = 5;

/** Relative starting widths: reading text gets the room, identifiers and flags stay narrow. */
export function defaultColumnWeight(key: string): number {
  if (key === "text") return 4;
  if (["work", "speaker", "quoted_speaker", "position_holder", "__file"].includes(key)) return 1.5;
  return 1;
}

const round = (value: number) => Math.round(value * 10) / 10;

/** Scale to 100 after rounding, putting the rounding remainder on the widest column. */
function toHundred(keys: string[], raw: ColumnWidths): ColumnWidths {
  const total = keys.reduce((sum, key) => sum + raw[key], 0) || 1;
  const out: ColumnWidths = {};
  for (const key of keys) out[key] = round((raw[key] / total) * 100);
  const drift = round(100 - keys.reduce((sum, key) => sum + out[key], 0));
  if (drift && keys.length) {
    const widest = keys.reduce((a, b) => (out[b] > out[a] ? b : a));
    out[widest] = round(out[widest] + drift);
  }
  return out;
}

/**
 * Fit each column to at least `min` while keeping the same total: columns below the floor are
 * pinned to it and the rest are rescaled in proportion, repeating until none falls short.
 */
function enforceMinimum(keys: string[], widths: ColumnWidths, min: number): ColumnWidths {
  const total = keys.reduce((sum, key) => sum + widths[key], 0);
  const floor = Math.min(min, total / Math.max(1, keys.length));
  const pinned = new Set<string>();
  const out = { ...widths };
  for (;;) {
    const free = keys.filter((key) => !pinned.has(key));
    const freeTotal = free.reduce((sum, key) => sum + widths[key], 0) || 1;
    const room = total - floor * pinned.size;
    for (const key of pinned) out[key] = floor;
    for (const key of free) out[key] = (room * widths[key]) / freeTotal;
    const short = free.filter((key) => out[key] < floor - 1e-9);
    if (!short.length) return out;
    for (const key of short) pinned.add(key);
  }
}

/**
 * Widths for the shown columns. Saved widths are kept in proportion; a column without one (newly
 * shown) starts at its default share, so adding a column narrows the others evenly.
 */
export function normalizeColumnWidths(
  keys: string[],
  saved: ColumnWidths = {},
  min = MIN_COLUMN_PERCENT,
): ColumnWidths {
  if (!keys.length) return {};
  const weightTotal = keys.reduce((sum, key) => sum + defaultColumnWeight(key), 0);
  const raw: ColumnWidths = {};
  for (const key of keys) {
    const value = Number(saved[key]);
    raw[key] =
      Number.isFinite(value) && value > 0 ? value : (defaultColumnWeight(key) / weightTotal) * 100;
  }
  return toHundred(keys, enforceMinimum(keys, toHundred(keys, raw), min));
}

/**
 * Set one column's width; the other columns share what is left in proportion to their current
 * widths. The value is clamped so every other column can keep the minimum.
 */
export function setColumnWidth(
  keys: string[],
  widths: ColumnWidths,
  key: string,
  percent: number,
  min = MIN_COLUMN_PERCENT,
): ColumnWidths {
  const current = normalizeColumnWidths(keys, widths, min);
  if (!keys.includes(key) || keys.length === 1) return current;
  const others = keys.filter((item) => item !== key);
  const floor = Math.min(min, 100 / keys.length);
  const target = Math.min(100 - floor * others.length, Math.max(floor, Number(percent) || floor));
  const otherTotal = others.reduce((sum, item) => sum + current[item], 0) || 1;
  const raw: ColumnWidths = {};
  for (const item of others) raw[item] = ((100 - target) * current[item]) / otherTotal;
  const fitted = enforceMinimum(others, raw, min);
  // Keep the edited column exactly where the user put it; rounding drift goes to the others.
  const rest = toHundred(others, Object.fromEntries(others.map((item) => [item, fitted[item]])));
  const out: ColumnWidths = { [key]: round(target) };
  for (const item of others) out[item] = round((rest[item] * (100 - out[key])) / 100);
  const drift = round(100 - keys.reduce((sum, item) => sum + out[item], 0));
  if (drift) {
    const widest = others.reduce((a, b) => (out[b] > out[a] ? b : a));
    out[widest] = round(out[widest] + drift);
  }
  return out;
}

/** Scale one column by `factor` (for example a denser layout narrowing the text column). */
export function scaleColumnWidth(
  keys: string[],
  widths: ColumnWidths,
  key: string,
  factor: number,
  min = MIN_COLUMN_PERCENT,
): ColumnWidths {
  const current = normalizeColumnWidths(keys, widths, min);
  return keys.includes(key)
    ? setColumnWidth(keys, current, key, current[key] * factor, min)
    : current;
}
