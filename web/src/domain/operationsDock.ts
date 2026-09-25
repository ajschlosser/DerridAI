// Copyright 2026 Aaron John Schlosser, PhD.

export const ACTIVE_JOB_STATUSES = ["queued", "running", "cancelling"] as const;
export const TERMINAL_JOB_STATUSES = ["completed", "cancelled", "failed", "blocked"] as const;

export type JobStatusTone = "neutral" | "info" | "success" | "warning" | "danger";

export type DockCollapsedSummary = {
  key: string;
  fallback: string;
  values: Record<string, string | number>;
  tone: JobStatusTone;
  percent: number | null;
};

export function isActiveJobStatus(status: string | null | undefined): boolean {
  return (ACTIVE_JOB_STATUSES as readonly string[]).includes(String(status || ""));
}

export function isTerminalJobStatus(status: string | null | undefined): boolean {
  return (TERMINAL_JOB_STATUSES as readonly string[]).includes(String(status || ""));
}

export function shouldMountOperationDock(visibleCount: number): boolean {
  return Number(visibleCount) > 0;
}

export function jobIdsToPruneFromDock(
  visibleJobIds: Iterable<string>,
  liveJobIds: Iterable<string>,
): string[] {
  const live = new Set([...liveJobIds].map(String).filter(Boolean));
  return [...visibleJobIds].map(String).filter((id) => Boolean(id) && !live.has(id));
}

export function jobProgressPercent(
  job: { total?: number | null; completed?: number | null } | null | undefined,
): number {
  const total = Number(job?.total || 0);
  const done = Number(job?.completed || 0);
  if (!total) return 0;
  return Math.max(0, Math.min(100, Math.round((done / total) * 100)));
}

export function statusBadgeTone(status: string | null | undefined): JobStatusTone {
  switch (String(status || "")) {
    case "queued":
      return "neutral";
    case "running":
      return "info";
    case "cancelling":
      return "warning";
    case "completed":
      return "success";
    case "blocked":
      return "warning";
    case "cancelled":
      return "neutral";
    case "failed":
      return "danger";
    default:
      return "neutral";
  }
}

export function dockCollapsedSummary(input: {
  activeCount: number;
  failedCount: number;
  finishedCount: number;
  primaryLabel?: string;
  primaryPercent?: number | null;
}): DockCollapsedSummary {
  const active = Math.max(0, Number(input.activeCount) || 0);
  const failed = Math.max(0, Number(input.failedCount) || 0);
  const finished = Math.max(0, Number(input.finishedCount) || 0);
  const percent =
    input.primaryPercent == null || Number.isNaN(Number(input.primaryPercent))
      ? null
      : Math.max(0, Math.min(100, Math.round(Number(input.primaryPercent))));
  const primaryLabel = String(input.primaryLabel || "").trim();

  if (failed > 0 && active === 0) {
    return {
      key: failed === 1 ? "operations.pill_failed_one" : "operations.pill_failed_other",
      fallback: "{count} failed",
      values: { count: failed },
      tone: "danger",
      percent: null,
    };
  }
  if (active === 1 && primaryLabel) {
    if (percent != null) {
      return {
        key: "operations.pill_primary_progress",
        fallback: "{label} · {percent}%",
        values: { label: primaryLabel, percent },
        tone: "info",
        percent,
      };
    }
    return {
      key: "operations.pill_primary",
      fallback: "{label}",
      values: { label: primaryLabel },
      tone: "info",
      percent: null,
    };
  }
  if (active > 0 && failed > 0) {
    return {
      key: "operations.pill_running_failed",
      fallback: "{running} running · {failed} failed",
      values: { running: active, failed },
      tone: "danger",
      percent,
    };
  }
  if (active > 0) {
    return {
      key: active === 1 ? "operations.pill_running_one" : "operations.pill_running_other",
      fallback: "{count} running",
      values: { count: active },
      tone: "info",
      percent,
    };
  }
  if (finished > 0) {
    return {
      key: finished === 1 ? "operations.pill_finished_one" : "operations.pill_finished_other",
      fallback: finished === 1 ? "{count} needs attention" : "{count} need attention",
      values: { count: finished },
      tone: "warning",
      percent: null,
    };
  }
  return {
    key: "operations.title",
    fallback: "Operations",
    values: {},
    tone: "neutral",
    percent: null,
  };
}

export type DockPlacement = { left: number; top: number; maxHeight: number };

/**
 * Where a user-positioned dock goes so every edge stays on screen. The saved anchor is where the
 * user left the (often minimized) dock; when it expands past the right or bottom edge it slides
 * back in rather than hanging off the viewport. The anchor itself is not rewritten, so collapsing
 * again returns the dock to where the user put it.
 */
export function fitDockInViewport(
  anchor: { left: number; top: number },
  size: { width: number; height: number },
  viewport: { width: number; height: number },
  margin = 8,
): DockPlacement {
  const width = Math.min(size.width, viewport.width - margin * 2);
  const height = Math.min(size.height, viewport.height - margin * 2);
  const clamp = (value: number, min: number, max: number) =>
    Math.round(Math.min(Math.max(min, max), Math.max(min, value)));
  const left = clamp(Number(anchor.left) || margin, margin, viewport.width - width - margin);
  const top = clamp(Number(anchor.top) || margin, margin, viewport.height - height - margin);
  return { left, top, maxHeight: Math.max(120, viewport.height - top - margin) };
}
