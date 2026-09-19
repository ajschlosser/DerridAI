import { describe, expect, it } from "vitest";
import {
  classifyOperations, elapsedSeconds, etaSeconds, filterCounts, filterOperations, formatDuration,
  groupByDay, needsAttention, relativeTime, type OperationView,
} from "../../src/domain/operationsPanel";

const NOW = new Date("2026-09-20T15:00:00").getTime();
const iso = (offsetSeconds: number) => new Date(NOW + offsetSeconds * 1000).toISOString();

function view(over: Partial<OperationView> = {}): OperationView {
  return {
    id: "j", type: "llm_tool", status: "completed", label: "Job", subtitle: "", facts: [], owner: "admin",
    createdAt: iso(-600), startedAt: iso(-600), finishedAt: iso(-300), total: 10, completed: 10,
    progressLabel: "10/10 (100%)", cancelRequested: false, error: "", result: null, ...over,
  };
}

describe("classification", () => {
  it("puts running, failed/blocked/unreviewed, and everything else in separate sections", () => {
    const list = [
      view({ id: "run", status: "running", finishedAt: null }),
      view({ id: "queued", status: "queued", startedAt: null, finishedAt: null }),
      view({ id: "fail", status: "failed" }),
      view({ id: "blocked", status: "blocked" }),
      view({ id: "review", status: "completed", type: "llm", result: { kind: "review" } }),
      view({ id: "ok", status: "completed" }),
      view({ id: "cancelled", status: "cancelled" }),
    ];
    const { active, attention, history } = classifyOperations(list);
    expect(active.map((v) => v.id).sort()).toEqual(["queued", "run"]);
    expect(attention.map((v) => v.id).sort()).toEqual(["blocked", "fail", "review"]);
    expect(history.map((v) => v.id).sort()).toEqual(["cancelled", "ok"]);
  });

  it("does not call a running job with partial results 'needs attention'", () => {
    expect(needsAttention(view({ status: "running", result: { kind: "review-partial" } }))).toBe(false);
  });

  it("orders each section newest first", () => {
    const { history } = classifyOperations([
      view({ id: "old", finishedAt: iso(-7200) }),
      view({ id: "new", finishedAt: iso(-60) }),
    ]);
    expect(history.map((v) => v.id)).toEqual(["new", "old"]);
  });

  it("counts and filters consistently", () => {
    const list = [view({ id: "a", status: "running", finishedAt: null }), view({ id: "b", status: "failed" }), view({ id: "c" })];
    expect(filterCounts(list)).toEqual({ all: 3, active: 1, attention: 1, done: 2 });
    expect(filterOperations(list, "done").map((v) => v.id)).toEqual(["b", "c"]);
    expect(filterOperations(list, "all")).toHaveLength(3);
  });
});

describe("time", () => {
  it("measures elapsed time against 'now' for running jobs and against the end for finished ones", () => {
    expect(elapsedSeconds(view({ status: "running", startedAt: iso(-90), finishedAt: null }), NOW)).toBe(90);
    expect(elapsedSeconds(view({ startedAt: iso(-600), finishedAt: iso(-300) }), NOW)).toBe(300);
    expect(elapsedSeconds(view({ startedAt: null }), NOW)).toBe(0);
  });

  it("estimates the remaining time only when the rate is trustworthy", () => {
    const running = (over: Partial<OperationView>) => view({ status: "running", finishedAt: null, startedAt: iso(-100), total: 100, completed: 50, ...over });
    expect(etaSeconds(running({}), NOW)).toBeCloseTo(100, 0);
    expect(etaSeconds(running({ completed: 1 }), NOW)).toBeNull(); // too early to extrapolate
    expect(etaSeconds(running({ completed: 99 }), NOW)).toBeNull(); // about to finish
    expect(etaSeconds(running({ startedAt: iso(-5) }), NOW)).toBeNull(); // too little elapsed time
    expect(etaSeconds(running({ type: "pdf_corpus" }), NOW)).toBeNull(); // weighted stages, not a rate
    expect(etaSeconds(running({ status: "queued" }), NOW)).toBeNull();
    expect(etaSeconds(running({ cancelRequested: true }), NOW)).toBeNull();
  });

  it("formats durations with Intl units in the requested language", () => {
    expect(formatDuration(71, "en-US")).toBe("1 min 11 sec");
    expect(formatDuration(3861, "en-US")).toBe("1 hr 4 min");
    expect(formatDuration(0, "en-US")).toBe("0 sec");
    expect(formatDuration(71, "fr-CA")).toMatch(/^1\s*min\s*11\s*s$/);
  });

  it("describes when something happened in words", () => {
    expect(relativeTime(iso(-10), NOW, "en-US")).toBe("now");
    expect(relativeTime(iso(-300), NOW, "en-US")).toBe("5 minutes ago");
    expect(relativeTime(iso(-7200), NOW, "en-US")).toBe("2 hours ago");
    expect(relativeTime(iso(-86400 * 3), NOW, "en-US")).toBe("3 days ago");
    expect(relativeTime(iso(-300), NOW, "fr-CA")).toMatch(/5\s*minutes/);
    expect(relativeTime(null, NOW, "en-US")).toBe("");
  });
});

describe("history grouping", () => {
  it("groups by local day with today/yesterday labels and dates after that", () => {
    const groups = groupByDay([
      view({ id: "t", finishedAt: iso(-60) }),
      view({ id: "y", finishedAt: iso(-86400) }),
      view({ id: "old", finishedAt: iso(-86400 * 10) }),
    ], NOW, "en-US");
    expect(groups.map((g) => g.label)).toEqual(["Today", "Yesterday", "Sep 10, 2026"]);
    expect(groups.map((g) => g.items[0].id)).toEqual(["t", "y", "old"]);
  });

  it("keeps several operations from one day together", () => {
    const groups = groupByDay([view({ id: "a", finishedAt: iso(-60) }), view({ id: "b", finishedAt: iso(-120) })], NOW, "en-US");
    expect(groups).toHaveLength(1);
    expect(groups[0].items.map((v) => v.id)).toEqual(["a", "b"]);
  });
});
