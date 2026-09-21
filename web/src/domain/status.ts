/* Copyright 2026 Aaron John Schlosser, PhD. */

export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";

export function statusTone(kind: string): StatusTone {
  if (kind === "synced") return "success";
  if (kind === "changed") return "warning";
  if (kind === "exists") return "info";
  if (kind === "absent") return "danger";
  return "neutral";
}
