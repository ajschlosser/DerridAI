/* Copyright 2026 Aaron John Schlosser, PhD. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createCorpusAnalytics } from "../../src/domain/corpusAnalytics";

// The snapshots were verified to be identical to the original legacy runtime.js functions, over this
// corpus and a range of arguments, before they were recorded.
// The date keys are built from local midnight, so fix the time zone for stable snapshots.
const originalTz = process.env.TZ;
beforeEach(() => {
  process.env.TZ = "UTC";
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-03-10T15:00:00Z"));
});
afterEach(() => {
  if (originalTz === undefined) delete process.env.TZ;
  else process.env.TZ = originalTz;
  vi.useRealTimers();
});

function corpus() {
  const files = [
    { id: "f1", name: "a.jsonl" },
    { id: "f2", name: "b.jsonl" },
  ];
  const rows: Array<{
    file: (typeof files)[number];
    record: Record<string, unknown>;
    index: number;
  }> = [];
  const works = [
    "Of Grammatology",
    "Speech and Phenomena",
    undefined,
    "Dissemination",
    "Margins",
    "Glas",
    "Positions",
    "Writing and Difference",
    "Specters",
    "Archive Fever",
    "Politics of Friendship",
    "Given Time",
  ];
  let n = 0;
  for (const file of files)
    for (let i = 0; i < 40; i++, n++) {
      const day = (d: number) =>
        new Date(Date.parse("2026-03-10T12:00:00Z") - d * 86400000).toISOString();
      const updates =
        i % 3 === 0
          ? [
              {
                field_name: "needs_review",
                old_value: true,
                new_value: false,
                timestamp: day(i % 25),
              },
              {
                field_name: "needs_review",
                old_value: false,
                new_value: true,
                timestamp: day((i % 25) + 3),
              },
              { field_name: "topics", old_value: [], new_value: ["x"], timestamp: day(2) },
              { field_name: "needs_review", old_value: true, new_value: false },
            ]
          : i % 7 === 0
            ? [{ field_name: "text", old_value: "o", new_value: "n", timestamp: "bad" }]
            : undefined;
      rows.push({
        file,
        index: i,
        record: {
          record_id: `r${n}`,
          work: works[n % works.length],
          year: n % 5 === 0 ? undefined : 1960 + (n % 50),
          document_author: n % 2 ? "J. Derrida" : "Other, A.",
          needs_review: n % 4 === 0,
          text: "x".repeat((n * 37) % 500),
          topics: n % 3 ? ["a", "b;c", " a "] : "d|e",
          updates,
        },
      });
    }
  return rows;
}
function make() {
  const rows = corpus();
  const memo = new Map<string, unknown>();
  return {
    allRows: () => rows,
    memoCorpus: (key: string, builder: () => unknown) => {
      if (memo.has(key)) return memo.get(key);
      const v = builder();
      memo.set(key, v);
      return v;
    },
  };
}

const plain = (value: unknown) =>
  JSON.parse(
    JSON.stringify(value, (_k, x) =>
      x instanceof Set ? { __set: [...x] } : x instanceof Map ? { __map: [...x] } : x,
    ),
  );

describe("corpus analytics", () => {
  const analytics = () =>
    createCorpusAnalytics(make() as never) as Record<string, (...args: unknown[]) => unknown>;

  it("indexes works", () => {
    const index = analytics().workIndex() as Map<string, { count: number; review: number }>;
    expect(index.size).toBe(12);
    expect(index.get("(Untitled work)")?.count).toBeGreaterThan(0);
    expect(plain(index)).toMatchSnapshot();
  });
  it("counts and ranks", () => {
    const a = analytics();
    expect(plain(a.topFieldValues("topics", 3))).toMatchSnapshot();
    expect(plain(a.publicationYearSeries())).toMatchSnapshot();
    expect(plain(a.workRecordShares(3))).toMatchSnapshot();
    expect(plain(a.averageRecordLengthForTopWorks(3))).toMatchSnapshot();
    expect(plain(a.recentAuditChanges(5))).toMatchSnapshot();
  });
  it("builds the needs-review series", () => {
    const a = analytics();
    expect(plain(a.topNeedsReviewWorkSeries(7, 3))).toMatchSnapshot();
    expect(plain(a.needsReviewTimeline(7))).toMatchSnapshot();
    expect(a.dateKeys(3)).toEqual(["2026-03-08", "2026-03-09", "2026-03-10"]);
  });
  it("memoizes per key", () => {
    let builds = 0;
    const a = createCorpusAnalytics({
      allRows: () => [],
      memoCorpus: (key, builder) => {
        builds++;
        return builder();
      },
    } as never);
    a.publicationYearSeries();
    expect(builds).toBe(1);
  });
});
