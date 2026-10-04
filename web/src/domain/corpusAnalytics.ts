/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { flattenValueList } from "./recordQuery";

// Derived, memoized statistics over the loaded corpus for the dashboard and Works view.
// Corpus rows and the memo cache are injected so these calculations remain framework-light.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

interface Deps {
  allRows: () => Loose[];
  memoCorpus: <T>(key: string, builder: () => T) => T;
}

interface ReviewStateEvent {
  time: number;
  previousValue: boolean;
}

interface ReviewStateHistory {
  currentValue: boolean;
  eventsNewestFirst: ReviewStateEvent[];
}

/**
 * Reconstruct review state at a past cutoff by rolling today's state backward
 * through every later audit event.
 */
function reviewStateAt(history: ReviewStateHistory, cutoffTime: number): boolean {
  let value = history.currentValue;
  for (const event of history.eventsNewestFirst) {
    if (event.time <= cutoffTime) break;
    value = event.previousValue;
  }
  return value;
}

export function createCorpusAnalytics(deps: Deps) {
  const { allRows, memoCorpus } = deps;
  function workIndex() {
    return memoCorpus("work-index", () => {
      // The same logical Record can appear in several loaded files (for example,
      // a collection and one of its Works). Count it once per Work and prefer
      // the copy carrying unsaved edits so local changes remain visible.
      const rowsByWork = new Map<string, Loose[]>();
      const recordIndexByWork = new Map<string, Map<string, number>>();

      for (const row of allRows()) {
        const workTitle = String(row.record.work || "(Untitled work)");
        const workRows = rowsByWork.get(workTitle) || [];
        const recordIndex = recordIndexByWork.get(workTitle) || new Map<string, number>();
        rowsByWork.set(workTitle, workRows);
        recordIndexByWork.set(workTitle, recordIndex);

        const recordId = row.record.record_id;
        const hasUnsavedEdits = Boolean(row.file.dirty?.has?.(row.index));
        if (recordId != null && String(recordId) !== "") {
          const existingIndex = recordIndex.get(String(recordId));
          if (existingIndex !== undefined) {
            const existingRow = workRows[existingIndex];
            const existingRowIsEdited = Boolean(
              existingRow.file.dirty?.has?.(existingRow.index),
            );
            if (hasUnsavedEdits && !existingRowIsEdited) {
              workRows[existingIndex] = row;
            }
            continue;
          }
          recordIndex.set(String(recordId), workRows.length);
        }
        workRows.push(row);
      }

      const workSummaries = new Map();
      for (const [workTitle, workRows] of rowsByWork) {
        const summary = {
          work: workTitle,
          count: 0,
          review: 0,
          files: new Set(),
          authors: new Set(),
          years: new Set(),
          rows: [] as Loose[],
        };
        for (const { file, record, index } of workRows) {
          summary.count += 1;
          if (record.needs_review) summary.review += 1;
          summary.files.add(file.name);
          if (record.document_author) summary.authors.add(record.document_author);
          if (record.year != null) summary.years.add(record.year);
          summary.rows.push({ file, record, index });
        }
        workSummaries.set(workTitle, summary);
      }
      return workSummaries;
    });
  }
  function dateKeys(days = 30) {
    const today = new Date();
    const keys = [];
    for (let offset = days - 1; offset >= 0; offset -= 1) {
      const date = new Date(today);
      date.setHours(0, 0, 0, 0);
      date.setDate(date.getDate() - offset);
      keys.push(date.toISOString().slice(0, 10));
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

      const recordsByWork: Map<string, ReviewStateHistory[]> = new Map(
        top.map(
          (work: string) => [work, []] as [string, ReviewStateHistory[]],
        ),
      );
      for (const { record } of allRows()) {
        const work = String(record.work || "(Untitled work)");
        if (!recordsByWork.has(work)) continue;
        const eventsNewestFirst = (
          (Array.isArray(record.updates) ? record.updates : []) as Loose[]
        )
          .filter((update) => update.field_name === "needs_review" && update.timestamp)
          .map((update) => ({
            time: new Date(update.timestamp).getTime(),
            previousValue: Boolean(update.old_value),
          }))
          .filter((event) => Number.isFinite(event.time))
          .sort((left, right) => right.time - left.time);
        recordsByWork.get(work)!.push({
          currentValue: Boolean(record.needs_review),
          eventsNewestFirst,
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
            if (reviewStateAt(history, end)) count += 1;
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

      const recordHistories: ReviewStateHistory[] = allRows().map(({ record }) => {
        const eventsNewestFirst = (
          (Array.isArray(record.updates) ? record.updates : []) as Loose[]
        )
          .filter((update) => update.field_name === "needs_review" && update.timestamp)
          .map((update) => ({
            time: new Date(update.timestamp).getTime(),
            previousValue: Boolean(update.old_value),
          }))
          .filter((event) => Number.isFinite(event.time))
          .sort((left, right) => right.time - left.time);
        return {
          currentValue: Boolean(record.needs_review),
          eventsNewestFirst,
        };
      });

      return dates.map((date) => {
        const end = date.getTime();
        let count = 0;
        for (const history of recordHistories) {
          if (reviewStateAt(history, end)) count += 1;
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
