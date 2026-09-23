/* Copyright 2026 Aaron John Schlosser, PhD. */

export function compactNumber(value: unknown): string {
  const n = Number(value) || 0;
  if (n >= 1000000) return `${(n / 1000000).toFixed(n >= 10000000 ? 0 : 1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 100000 ? 0 : 1)}K`;
  return n.toLocaleString();
}
