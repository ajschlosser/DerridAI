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
// The caller supplies corpus rows and cache ownership so these calculations stay framework-light.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

interface CorpusAnalyticsDeps {
  allRows: () => Loose[];
  memoCorpus: <T>(key: string, builder: () => T) => T;
}

export function createCorpusAnalytics(deps: CorpusAnalyticsDeps) {
  const { allRows, memoCorpus } = deps;
  function workIndex() {
    return memoCorpus("work-index", () => {
      // The same logical record can sit in several loaded files (a collection and one of its works, or a
      // reload). Count it once per work; prefer the copy carrying unsaved edits so they stay visible.
      const rowsByWork = new Map<string, Loose[]>();
      const recordIndexByWork = new Map<string, Map<string, number>>();

      for (const row of allRows()) {
        const workName = String(row.record.work || "(Untitled work)");
        const workRows = rowsByWork.get(workName) || [];
        const recordIndex = recordIndexByWork.get(workName) || new Map<string, number>();
        rowsByWork.set(workName, workRows);
        recordIndexByWork.set(workName, recordIndex);

        const recordId = row.record.record_id;
        const hasUnsavedEdits = Boolean(row.file.dirty?.has?.(row.index));
        if (recordId != null && String(recordId) !== "") {
          const existingIndex = recordIndex.get(String(recordId));
          if (existingIndex !== undefined) {
            const existingRow = workRows[existingIndex];
            if (hasUnsavedEdits && !existingRow.file.dirty?.has?.(existingRow.index)) {
              workRows[existingIndex] = row;
            }
            continue;
          }
          recordIndex.set(String(recordId), workRows.length);
        }
        workRows.push(row);
      }

      const workSummaries = new Map();
      for (const [workName, workRows] of rowsByWork) {
        const summary = {
          work: workName,
          count: 0,
          review: 0,
          files: new Set(),
          authors: new Set(),
          years: new Set(),
          rows: [] as Loose[],
        };
        for (const { file, record, index } of workRows) {
          summary.count++;
          if (record.needs_review) summary.review++;
          summary.files.add(file.name);
          if (record.document_author) summary.authors.add(record.document_author);
          if (record.year != null) summary.years.add(record.year);
          summary.rows.push({ file, record, index });
        }
        workSummaries.set(workName, summary);
      }
      return workSummaries;
    });
  }
  function dateKeys(days = 30) {
    const today = new Date();
    const keys = [];
    for (let offset = days - 1; offset >= 0; offset--) {
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
      const topWorks = [...counts.entries()]
        .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
        .slice(0, limit)
        .map(([work]) => work);
      if (!topWorks.length) return { rows: [], series: [] };

      const recordsByWork: Map<string, Loose[]> = new Map(
        topWorks.map((work: string) => [work, []] as [string, Loose[]]),
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
      const series = topWorks.map((work, index) => ({
        key: `work_${index}`,
        label: work,
        short_label: `${index + 1}. ${work.length > 18 ? `${work.slice(0, 16)}…` : work}`,
      }));
      const rows = keys.map((key) => {
        const end = new Date(`${key}T23:59:59.999Z`).getTime();
        const row: Loose = { key };
        topWorks.forEach((work, index) => {
          let needsReviewCount = 0;
          for (const history of recordsByWork.get(work) || []) {
            // Events are newest-first. Walk backward from current state until
            // reaching the requested historical cutoff.
            let neededReviewAtCutoff = history.current;
            for (const event of history.events) {
              if (event.time <= end) break;
              neededReviewAtCutoff = event.old;
            }
            if (neededReviewAtCutoff) needsReviewCount++;
          }
          row[`work_${index}`] = needsReviewCount;
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
        const date = new Date(today);
        date.setDate(date.getDate() - offset);
        dates.push(date);
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
        let needsReviewCount = 0;
        for (const history of recordHistories) {
          // Reconstruct state at this date by undoing newer updates from the
          // current value. This avoids materializing a full snapshot per day.
          let neededReviewAtCutoff = history.current;
          for (const event of history.events) {
            if (event.time <= end) break;
            neededReviewAtCutoff = event.old;
          }
          if (neededReviewAtCutoff) needsReviewCount++;
        }
        return { key: date.toISOString().slice(0, 10), value: needsReviewCount };
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
      const sortedWorks = [...counts.entries()].sort(
        (left, right) => right[1] - left[1] || left[0].localeCompare(right[0]),
      );
      const largestWorks = sortedWorks.slice(0, limit);
      const otherRecordCount = sortedWorks
        .slice(limit)
        .reduce((sum, [, count]) => sum + count, 0);
      if (otherRecordCount) largestWorks.push(["Other works", otherRecordCount]);
      return largestWorks;
    });
  }
  function averageRecordLengthForTopWorks(limit = 5) {
    return memoCorpus(`avg-record-length-by-work:${limit}`, () => {
      const statsByWork = new Map();
      for (const { record } of allRows()) {
        const work = String(record.work || "(Untitled work)").trim() || "(Untitled work)";
        const stats = statsByWork.get(work) || { count: 0, total: 0 };
        stats.count++;
        stats.total += String(record.text || "").length;
        statsByWork.set(work, stats);
      }
      return [...statsByWork.entries()]
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
