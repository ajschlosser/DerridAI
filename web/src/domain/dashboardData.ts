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

// The home dashboard's data helpers (counts and the record preview), over injected helpers. The page itself is
// `views/DashboardView.vue`; the HTML renderer this module once held is gone.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

type Helper =
  | "allRows"
  | "api"
  | "isResearcher"
  | "memoCorpus"
  | "openAnnotationsWorkspaceRecord"
  | "recordStores"
  | "researcherDbRecords"
  | "responseCacheStore";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createDashboardData(deps: Deps) {
  const {
    state,
    allRows,
    api,
    isResearcher,
    memoCorpus,
    openAnnotationsWorkspaceRecord,
    recordStores,
    researcherDbRecords,
    responseCacheStore,
  } = deps;
  function dashboardTotals() {
    if (isResearcher()) {
      const stores = recordStores();
      const active = stores.find((store: Any) => store.name === state.activeStore) || stores[0];
      return {
        records: Number(active?.count || 0),
        works: state.storeWorkStats.length,
        flagged: 0,
        files: 0,
        changes: 0,
        dbs: stores.length,
        dbRecords: stores.reduce((sum: Any, store: Any) => sum + (Number(store.count) || 0), 0),
        cacheResponses: 0,
      };
    }
    const corpus = memoCorpus("dashboard-totals", () => {
      let flagged = 0,
        changes = 0;
      const works = new Set();
      for (const { record } of allRows()) {
        const work = String(record.work || "").trim();
        if (work) works.add(work);
        if (record.needs_review) flagged++;
        changes += Array.isArray(record.updates) ? record.updates.length : 0;
      }
      return {
        records: allRows().length,
        works: works.size,
        flagged,
        files: state.files.length,
        changes,
      };
    });
    const stores = recordStores();
    return {
      ...corpus,
      dbs: stores.length,
      dbRecords: stores.reduce((sum: Any, store: Any) => sum + (Number(store.count) || 0), 0),
      cacheResponses: Number(responseCacheStore()?.count || 0),
    };
  }
  function dashboardWorkspaceRecordTarget(pointer: Any) {
    if (!pointer || pointer.kind !== "workspace") return null;
    const file = state.files.find((item: Any) => item.id === pointer.fileId);
    const index = Number(pointer.index);
    if (!file || !Number.isInteger(index) || index < 0 || index >= file.records.length) return null;
    return { record: file.records[index], target: { kind: "workspace", fileId: file.id, index } };
  }
  async function dashboardRecordPreview() {
    const pointer = state.lastViewedRecord;
    if (pointer?.kind === "workspace") {
      const found = dashboardWorkspaceRecordTarget(pointer);
      if (found) return { ...found, lastViewed: true };
    }
    if (pointer?.kind === "database" && pointer.store && pointer.id) {
      let record = (state.activeStore === pointer.store ? researcherDbRecords() : []).find(
        (item: Any) => String(item._chroma_id || item.record_id || "") === String(pointer.id),
      );
      if (!record) {
        try {
          record = await api(
            `/api/stores/${encodeURIComponent(pointer.store)}/records/${encodeURIComponent(pointer.id)}`,
          );
        } catch {
          record = null;
        }
      }
      if (record)
        return {
          record,
          target: { kind: "database", store: pointer.store, id: String(pointer.id) },
          lastViewed: true,
        };
    }
    if (isResearcher()) {
      const current =
        recordStores().find((store: Any) => store.name === state.activeStore) || recordStores()[0];
      if (!current?.name || !Number(current.count || 0))
        return { record: null, target: null, lastViewed: false };
      try {
        const offset = Math.floor(Math.random() * Math.max(1, Number(current.count || 0)));
        const data = await api(
          `/api/stores/${encodeURIComponent(current.name)}/records?limit=1&offset=${offset}`,
        );
        const record = (data.records || [])[0] || null;
        if (record) {
          const id = String(record._chroma_id || record.record_id || "");
          return {
            record,
            target: { kind: "database", store: current.name, id },
            lastViewed: false,
          };
        }
      } catch (error: Any) {
        console.warn("Could not choose a random dashboard record", error);
      }
      return { record: null, target: null, lastViewed: false };
    }
    const choices = allRows();
    if (!choices.length) return { record: null, target: null, lastViewed: false };
    const item = choices[Math.floor(Math.random() * choices.length)];
    return {
      record: item.record,
      target: { kind: "workspace", fileId: item.file.id, index: item.index },
      lastViewed: false,
    };
  }
  /** Opens the record a shared (server) annotation is attached to, in the store it belongs to. */
  function openSharedAnnotationRecord(store: Any, recordId: Any) {
    openAnnotationsWorkspaceRecord({ server: true, source: store, record_id: recordId });
  }
  return {
    openSharedAnnotationRecord,
    dashboardTotals,
    dashboardWorkspaceRecordTarget,
    dashboardRecordPreview,
  };
}
