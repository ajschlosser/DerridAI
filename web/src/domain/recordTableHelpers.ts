/* Copyright 2026 Aaron John Schlosser, PhD. */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function formatTimestamp(value: Any): string {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

export function toggleSort(sort: Any, key: Any): void {
  if (sort.key === key) sort.dir *= -1;
  else {
    sort.key = key;
    sort.dir = 1;
  }
}

export function localRecordKey(file: Any, index: Any): string {
  return `${file.id}::${index}`;
}
