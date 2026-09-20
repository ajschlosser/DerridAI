/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flattenValueList } from "./recordQuery";

// Derived, memoized statistics over the loaded corpus for the dashboard and Works view. Moved verbatim from the
// legacy runtime; the corpus rows and the memo cache are passed in.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

interface Deps {
  allRows: () => Loose[];
  memoCorpus: <T>(key: string, builder: () => T) => T;
}

export function createCorpusAnalytics(deps: Deps) {
  const { allRows, memoCorpus } = deps;
  function workIndex() {
    return memoCorpus("work-index", () => {
      const map = new Map();
      for (const { file, record: r, index } of allRows()) {
        const key = String(r.work || "(Untitled work)");
        const item = map.get(key) || {
          work: key,
          count: 0,
          review: 0,
          files: new Set(),
          authors: new Set(),
          years: new Set(),
          rows: [],
        };
        item.count++;
        if (r.needs_review) item.review++;
        item.files.add(file.name);
        if (r.document_author) item.authors.add(r.document_author);
        if (r.year != null) item.years.add(r.year);
        item.rows.push({ file, record: r, index });
        map.set(key, item);
      }
      return map;
    });
  }
  function dateKeys(days = 30) {
    const today = new Date();
    const keys = [];
    for (let offset = days - 1; offset >= 0; offset--) {
      const d = new Date(today);
      d.setHours(0, 0, 0, 0);
      d.setDate(d.getDate() - offset);
      keys.push(d.toISOString().slice(0, 10));
    }
    return keys;
  }
  function topNeedsReviewWorkSeries(days = 30, limit = 5) {
    const dayKey = new Date().toISOString().slice(0, 10);
    return memoCorpus(`review-work-series:${days}:${limit}:${dayKey}`, () => {
      const counts = new Map();
      for (const { record } of allRows()) {
        if (!record.needs_review) continue;
        const work = String(record.work || "(Untitled work)");
        counts.set(work, (counts.get(work) || 0) + 1);
      }
      const top = [...counts.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .slice(0, limit)
        .map(([work]) => work);
      if (!top.length) return { rows: [], series: [] };

      const recordsByWork: Map<string, Loose[]> = new Map(
        top.map((work: string) => [work, []] as [string, Loose[]]),
      );
      for (const { record } of allRows()) {
        const work = String(record.work || "(Untitled work)");
        if (!recordsByWork.has(work)) continue;
        const events = ((Array.isArray(record.updates) ? record.updates : []) as Loose[])
          .filter((update) => update.field_name === "needs_review" && update.timestamp)
          .map((update) => ({
            time: new Date(update.timestamp).getTime(),
            old: Boolean(update.old_value),
          }))
          .filter((event) => Number.isFinite(event.time))
          .sort((a, b) => b.time - a.time);
        recordsByWork.get(work)!.push({
          current: Boolean(record.needs_review),
          events,
        });
      }

      const keys = dateKeys(days);
      const series = top.map((work, index) => ({
        key: `work_${index}`,
        label: work,
        short_label: `${index + 1}. ${work.length > 18 ? `${work.slice(0, 16)}…` : work}`,
      }));
      const rows = keys.map((key) => {
        const end = new Date(`${key}T23:59:59.999Z`).getTime();
        const row: Loose = { key };
        top.forEach((work, index) => {
          let count = 0;
          for (const history of recordsByWork.get(work) || []) {
            let value = history.current;
            for (const event of history.events) {
              if (event.time <= end) break;
              value = event.old;
            }
            if (value) count++;
          }
          row[`work_${index}`] = count;
        });
        return row;
      });
      return { rows, series };
    });
  }
  function needsReviewTimeline(days = 30) {
    const dayKey = new Date().toISOString().slice(0, 10);
    return memoCorpus(`needs-review-timeline:${days}:${dayKey}`, () => {
      const today = new Date();
      today.setHours(23, 59, 59, 999);
      const dates = [];
      for (let offset = days - 1; offset >= 0; offset--) {
        const d = new Date(today);
        d.setDate(d.getDate() - offset);
        dates.push(d);
      }

      const recordHistories = allRows().map(({ record }) => {
        const events = ((Array.isArray(record.updates) ? record.updates : []) as Loose[])
          .filter((update) => update.field_name === "needs_review" && update.timestamp)
          .map((update) => ({
            time: new Date(update.timestamp).getTime(),
            old: Boolean(update.old_value),
            next: Boolean(update.new_value),
          }))
          .filter((event) => Number.isFinite(event.time))
          .sort((a, b) => b.time - a.time);
        return { current: Boolean(record.needs_review), events };
      });

      return dates.map((date) => {
        const end = date.getTime();
        let count = 0;
        for (const history of recordHistories) {
          let value = history.current;
          for (const event of history.events) {
            if (event.time <= end) break;
            value = event.old;
          }
          if (value) count++;
        }
        return { key: date.toISOString().slice(0, 10), value: count };
      });
    });
  }
  function topFieldValues(field: string, limit = 5) {
    return memoCorpus(`top:${field}:${limit}`, () => {
      const counts = new Map();
      for (const { record } of allRows()) {
        for (const value of flattenValueList(record[field])) {
          const key = value.trim();
          if (!key) continue;
          counts.set(key, (counts.get(key) || 0) + 1);
        }
      }
      return [...counts.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .slice(0, limit);
    });
  }
  function publicationYearSeries() {
    return memoCorpus("publication-year-series", () => {
      const counts = new Map();
      for (const { record } of allRows()) {
        const year = Number(record.year);
        if (!Number.isFinite(year) || year < 1000 || year > 3000) continue;
        counts.set(year, (counts.get(year) || 0) + 1);
      }
      return [...counts.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([key, value]) => ({ key: String(key), value }));
    });
  }
  function workRecordShares(limit = 9) {
    return memoCorpus(`work-shares:${limit}`, () => {
      const counts = new Map();
      for (const { record } of allRows()) {
        const work = String(record.work || "(Untitled work)");
        counts.set(work, (counts.get(work) || 0) + 1);
      }
      const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
      const top = sorted.slice(0, limit);
      const other = sorted.slice(limit).reduce((sum, [, count]) => sum + count, 0);
      if (other) top.push(["Other works", other]);
      return top;
    });
  }
  function averageRecordLengthForTopWorks(limit = 5) {
    return memoCorpus(`avg-record-length-by-work:${limit}`, () => {
      const groups = new Map();
      for (const { record } of allRows()) {
        const work = String(record.work || "(Untitled work)").trim() || "(Untitled work)";
        const stats = groups.get(work) || { count: 0, total: 0 };
        stats.count++;
        stats.total += String(record.text || "").length;
        groups.set(work, stats);
      }
      return [...groups.entries()]
        .sort((a, b) => b[1].count - a[1].count || a[0].localeCompare(b[0]))
        .slice(0, limit)
        .map(([work, stats]) => ({
          key: work,
          value: Math.round(stats.total / Math.max(1, stats.count)),
          count: stats.count,
        }));
    });
  }
  function recentAuditChanges(limit = 10) {
    return memoCorpus(`recent-audit:${limit}`, () => {
      const changes = [];
      for (const { file, record, index } of allRows()) {
        for (const update of Array.isArray(record.updates) ? record.updates : []) {
          changes.push({ file, record, index, update });
        }
      }
      return changes
        .sort(
          (a, b) =>
            new Date(b.update.timestamp || 0).getTime() -
            new Date(a.update.timestamp || 0).getTime(),
        )
        .slice(0, limit);
    });
  }
  return {
    workIndex,
    dateKeys,
    topNeedsReviewWorkSeries,
    needsReviewTimeline,
    topFieldValues,
    publicationYearSeries,
    workRecordShares,
    averageRecordLengthForTopWorks,
    recentAuditChanges,
  };
}
