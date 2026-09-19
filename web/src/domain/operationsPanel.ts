// Copyright 2026 Aaron John Schlosser, PhD.
// Pure view logic for the Home page Operations panel: which section an operation belongs in,
// filtering, elapsed time / ETA, and locale-aware duration and relative-time text.
import { isActiveJobStatus, jobProgressPercent } from "./operationsDock";

/** What the panel needs to know about one background operation (built by the runtime bridge). */
export interface OperationView {
  id: string;
  type: string;
  status: string;
  label: string;
  /** Name of an AppIcon that suggests the kind of operation. */
  icon: string;
  subtitle: string;
  facts: Array<{ name: string; value: string }>;
  owner: string;
  createdAt: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  total: number;
  completed: number;
  progressLabel: string;
  cancelRequested: boolean;
  error: string;
  /** The primary "go to the outcome" action, when the operation has one. */
  result: null | { kind: "review-partial" | "review" | "result" | "build" };
}

/** Everything the panel needs from the (legacy) runtime: data, change notification, and actions. */
export interface OperationsBridge {
  snapshot(): OperationView[];
  subscribe(listener: () => void): () => void;
  refresh(): Promise<void>;
  openDetails(id: string): void;
  openResult(id: string): void;
  cancel(id: string): Promise<void>;
  remove(id: string): Promise<void>;
  clearFinished(): Promise<void>;
}

export type OperationFilter = "all" | "active" | "attention" | "done";

export function isActive(view: Pick<OperationView, "status">): boolean {
  return isActiveJobStatus(view.status);
}

/** Failed and blocked operations, and finished ones whose results still await a decision. */
export function needsAttention(view: OperationView): boolean {
  if (isActive(view)) return false;
  return view.status === "failed" || view.status === "blocked" || view.result?.kind === "review";
}

function time(value: string | null): number {
  const parsed = value ? new Date(value).getTime() : NaN;
  return Number.isFinite(parsed) ? parsed : 0;
}
const newestFirst = (key: (view: OperationView) => number) => (a: OperationView, b: OperationView) => key(b) - key(a);
const startedOrCreated = (view: OperationView) => time(view.startedAt) || time(view.createdAt);
const endedOrStarted = (view: OperationView) => time(view.finishedAt) || startedOrCreated(view);

export interface ClassifiedOperations {
  active: OperationView[];
  attention: OperationView[];
  history: OperationView[];
}

export function classifyOperations(views: readonly OperationView[]): ClassifiedOperations {
  const active = views.filter(isActive).sort(newestFirst(startedOrCreated));
  const attention = views.filter(needsAttention).sort(newestFirst(endedOrStarted));
  const rest = views.filter((view) => !isActive(view) && !needsAttention(view)).sort(newestFirst(endedOrStarted));
  return { active, attention, history: rest };
}

export function filterOperations(views: readonly OperationView[], filter: OperationFilter): OperationView[] {
  if (filter === "active") return views.filter(isActive);
  if (filter === "attention") return views.filter(needsAttention);
  if (filter === "done") return views.filter((view) => !isActive(view));
  return [...views];
}

export function filterCounts(views: readonly OperationView[]): Record<OperationFilter, number> {
  return {
    all: views.length,
    active: filterOperations(views, "active").length,
    attention: filterOperations(views, "attention").length,
    done: filterOperations(views, "done").length,
  };
}

export function percentOf(view: Pick<OperationView, "total" | "completed">): number {
  return jobProgressPercent(view);
}

export function elapsedSeconds(view: OperationView, nowMs: number): number {
  const start = time(view.startedAt);
  if (!start) return 0;
  const end = view.finishedAt ? time(view.finishedAt) : nowMs;
  return Math.max(0, (end - start) / 1000);
}

/**
 * Remaining time for a running operation, or null when a reliable estimate is not possible.
 * PDF corpus builds report a weighted multi-stage figure, not a steady rate, so they get none.
 */
export function etaSeconds(view: OperationView, nowMs: number): number | null {
  if (view.status !== "running" || view.type === "pdf_corpus" || view.cancelRequested) return null;
  const percent = percentOf(view);
  const elapsed = elapsedSeconds(view, nowMs);
  if (percent < 3 || percent > 97 || elapsed < 10) return null;
  const remaining = (elapsed * (100 - percent)) / percent;
  return Number.isFinite(remaining) && remaining > 0 && remaining < 86_400 ? remaining : null;
}

/** "1 min 11 sec" in the user's language, from Intl unit formatting (no hand-written abbreviations). */
export function formatDuration(seconds: number, locale: string): string {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const parts: Array<[number, "hour" | "minute" | "second"]> = [
    [Math.floor(total / 3600), "hour"],
    [Math.floor((total % 3600) / 60), "minute"],
    [total % 60, "second"],
  ];
  const shown = parts.filter(([value]) => value > 0);
  const useful = shown.length ? shown : [[0, "second"] as [number, "second"]];
  // Two most significant units are plenty for a glance ("1 h 4 min", not "1 h 4 min 17 s").
  return useful
    .slice(0, 2)
    .map(([value, unit]) => new Intl.NumberFormat(locale, { style: "unit", unit, unitDisplay: "short" }).format(value))
    .join(" ");
}

export function relativeTime(iso: string | null, nowMs: number, locale: string): string {
  const then = time(iso);
  if (!then) return "";
  const seconds = Math.round((then - nowMs) / 1000);
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  const abs = Math.abs(seconds);
  if (abs < 45) return formatter.format(0, "second");
  if (abs < 3600) return formatter.format(Math.round(seconds / 60), "minute");
  if (abs < 86_400) return formatter.format(Math.round(seconds / 3600), "hour");
  return formatter.format(Math.round(seconds / 86_400), "day");
}

export function absoluteTime(iso: string | null, locale: string): string {
  const then = time(iso);
  return then ? new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(then)) : "";
}

const localDayKey = (ms: number) => {
  const date = new Date(ms);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
};

export interface DayGroup {
  key: string;
  label: string;
  items: OperationView[];
}

/** History grouped by local calendar day, newest first, labelled "today"/"yesterday" or a date. */
export function groupByDay(views: readonly OperationView[], nowMs: number, locale: string): DayGroup[] {
  const groups = new Map<string, DayGroup>();
  const today = new Date(nowMs);
  today.setHours(0, 0, 0, 0);
  const relative = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  for (const view of views) {
    const ms = endedOrStarted(view) || nowMs;
    const key = localDayKey(ms);
    let group = groups.get(key);
    if (!group) {
      const day = new Date(ms);
      day.setHours(0, 0, 0, 0);
      const diff = Math.round((day.getTime() - today.getTime()) / 86_400_000);
      const label = diff >= -1 && diff <= 0
        ? relative.format(diff, "day")
        : new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(day);
      group = { key, label: label.charAt(0).toLocaleUpperCase(locale) + label.slice(1), items: [] };
      groups.set(key, group);
    }
    group.items.push(view);
  }
  return [...groups.values()];
}
