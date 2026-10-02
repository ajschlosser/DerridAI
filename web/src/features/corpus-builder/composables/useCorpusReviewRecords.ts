/* Copyright 2026 Aaron John Schlosser, PhD. */
// Owns the review queue's lightweight rows, pagination, and a small selected-Record cache, and
// drives every other review composable through the shared `queueRows`/`selectRecord` contract
// (docs/GRAPHQL.md). The queue list holds `CorpusQueueRow`s; a full `CorpusRecord` is read one at
// a time, only when a row is opened, and kept in an LRU cache so moving between recently seen
// records does not re-read them.
import { onScopeDispose, ref, watch, type Ref } from "vue";
import type { CorpusBuild, CorpusRecord } from "../../../api/corpus";
import type { ReviewQueue } from "../../../types/corpus";
import { clearGraphQLReadCache, isAbortError } from "../../../api/graphql/client";
import { createLatestRequest } from "../../../api/graphql/latestRequest";
import { corpusReviewReads, type CorpusQueueRow } from "../api/reviewReads";
import { isFullRecord, queueRowFromRecord, type ReviewTargetLike } from "../domain/queueRows";

/** What `selectRecord` accepts: a lightweight queue row, or a full Record the caller already has. */
export type ReviewTarget = ReviewTargetLike;

/** Selected-Record cache capacity: enough to hold a review session's recent neighbourhood. */
const CACHE_CAPACITY = 48;

function createRecordCache() {
  const store = new Map<string, CorpusRecord>();
  return {
    get(id: string): CorpusRecord | undefined {
      const value = store.get(id);
      if (value === undefined) return undefined;
      // Re-insert to mark most-recently-used (Map iteration order is insertion order).
      store.delete(id);
      store.set(id, value);
      return value;
    },
    set(id: string, record: CorpusRecord) {
      store.delete(id);
      store.set(id, record);
      while (store.size > CACHE_CAPACITY) {
        const oldest = store.keys().next().value;
        if (oldest === undefined) break;
        store.delete(oldest);
      }
    },
    delete(id: string) {
      store.delete(id);
    },
    clear() {
      store.clear();
    },
  };
}

function messageOf(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

interface CorpusReviewRecordsOptions {
  selectedBuildId: Ref<string>;
  currentBuild: Ref<CorpusBuild | null>;
  recordOffset: Ref<number>;
  pageSize: number;
  reviewQueue: Ref<ReviewQueue>;
  recordQuery: Ref<string>;
  selectedRecordId: Ref<string>;
  selectedRecord: Ref<CorpusRecord | null>;
  /** True while the reviewer has an unsaved local edit open; a background refresh must not clobber it. */
  hasActiveDraft: () => boolean;
  /** Show a resolved full Record in the review workspace (owns `selectedRecordId`/`selectedRecord` and their side effects). */
  activateRecord: (record: CorpusRecord) => void;
  /** The selection could not be kept (empty page, or the targeted record no longer exists). */
  onSelectionCleared: () => void;
  /** A review-queue page was loaded, with its rows in document order. */
  onPageLoaded: (rows: CorpusQueueRow[]) => void;
  /** Build-wide observed metadata values, read separately from the queue page. */
  onFacets: (values: Record<string, string[]>) => void;
  onError: (message: string) => void;
}

export function useCorpusReviewRecords(options: CorpusReviewRecordsOptions) {
  const queueRows = ref<CorpusQueueRow[]>([]) as Ref<CorpusQueueRow[]>;
  const recordTotal = ref(0);
  const recordsLoading = ref(false);
  const reviewHydrated = ref(false);
  const hydratedTopologyCount = ref(0);
  const loadingRecordId = ref("");
  const recordError = ref("");
  const requestedRecordId = ref("");

  const cache = createRecordCache();
  const latestPage = createLatestRequest();
  const latestSelection = createLatestRequest();
  const latestFacets = createLatestRequest();
  let generation = 0;
  let selectionVersion = 0;
  const recordGenerations = new Map<string, number>();
  let facetsLoadedForBuild = false;
  let facetsLoadingForBuild = false;

  function clearSelection() {
    if (!options.selectedRecordId.value && !options.selectedRecord.value) return;
    options.selectedRecordId.value = "";
    options.selectedRecord.value = null;
    options.onSelectionCleared();
  }

  /** Prefetch the rows either side of `id` so stepping to a neighbour is instant. Best-effort. */
  function prefetchNeighbours(id: string) {
    const index = queueRows.value.findIndex((row) => row.record_id === id);
    if (index < 0 || !options.selectedBuildId.value) return;
    const neighbours = [queueRows.value[index - 1], queueRows.value[index + 1]].filter(
      (row): row is CorpusQueueRow => {
        if (!row) return false;
        const cached = cache.get(row.record_id);
        return (
          !cached || (row.record_revision != null && cached.record_revision !== row.record_revision)
        );
      },
    );
    if (!neighbours.length) return;
    const buildId = options.selectedBuildId.value;
    const epoch = generation;
    const versions = new Map(
      neighbours.map((row) => [row.record_id, recordGenerations.get(row.record_id)]),
    );
    void corpusReviewReads
      .records(
        buildId,
        neighbours.map((row) => row.record_id),
      )
      .then((records) => {
        if (epoch !== generation || buildId !== options.selectedBuildId.value) return;
        for (const record of records)
          if (versions.get(record.record_id) === recordGenerations.get(record.record_id))
            cache.set(record.record_id, record);
      })
      .catch(() => undefined);
  }

  /** Resolve one Record by id (cache first, dropping a stale entry) and hand it to `activateRecord`. */
  async function resolveAndActivate(id: string, revisionHint: number | null): Promise<void> {
    if (!options.selectedBuildId.value || !id) return;
    const ticket = latestSelection.start();
    selectionVersion += 1;
    const buildId = options.selectedBuildId.value;
    const epoch = generation;
    const recordVersion = recordGenerations.get(id);
    requestedRecordId.value = id;
    options.selectedRecordId.value = id;
    recordError.value = "";
    loadingRecordId.value = "";
    const cached = cache.get(id);
    if (cached && (revisionHint == null || cached.record_revision === revisionHint)) {
      options.activateRecord(cached);
      prefetchNeighbours(id);
      return;
    }
    // Never leave a stale Record showing while a different one loads: a slow response for the
    // previous selection could otherwise land after the reviewer has already moved on and a
    // command (accept/reject/edit) would fire against the wrong Record.
    options.selectedRecord.value = null;
    loadingRecordId.value = id;
    try {
      const [record] = await corpusReviewReads.records(buildId, [id], {
        signal: ticket.signal,
      });
      if (!ticket.current() || epoch !== generation || buildId !== options.selectedBuildId.value)
        return;
      if (recordVersion !== recordGenerations.get(id)) {
        await resolveAndActivate(id, null);
        return;
      }
      if (!record) {
        clearSelection();
        recordError.value = "not_found";
        return;
      }
      cache.set(record.record_id, record);
      options.activateRecord(record);
      prefetchNeighbours(record.record_id);
    } catch (exc) {
      if (ticket.current() && buildId === options.selectedBuildId.value && !isAbortError(exc)) {
        recordError.value = messageOf(exc);
        options.onError(messageOf(exc));
      }
    } finally {
      if (ticket.current()) loadingRecordId.value = "";
    }
  }

  async function selectRecord(target: ReviewTarget): Promise<void> {
    if (isFullRecord(target)) {
      // The caller already has the full Record (for example a review decision's `next_record`):
      // open it without another read, but still supersede any selection already in flight.
      const ticket = latestSelection.start();
      selectionVersion += 1;
      loadingRecordId.value = "";
      recordError.value = "";
      requestedRecordId.value = target.record_id;
      cache.set(target.record_id, target);
      if (!ticket.current()) return;
      options.activateRecord(target);
      prefetchNeighbours(target.record_id);
      return;
    }
    await resolveAndActivate(target.record_id, target.record_revision ?? null);
  }

  /** Jump to a record even if the current filtered queue does not contain it. */
  async function selectRecordById(recordId: string, onNotFound?: () => void): Promise<void> {
    if (!recordId) return;
    const existing = queueRows.value.find((row) => row.record_id === recordId);
    if (existing) {
      await selectRecord(existing);
      return;
    }
    // Not on the current (possibly filtered) page: let the caller widen the queue/query, then
    // reload targeting this id directly. `record`/`records` resolve by id regardless of filter.
    onNotFound?.();
    options.selectedRecordId.value = recordId;
    await refreshRecords(true, recordId);
  }

  async function loadFacets() {
    if (!options.selectedBuildId.value || facetsLoadingForBuild) return;
    const buildId = options.selectedBuildId.value;
    const ticket = latestFacets.start();
    facetsLoadingForBuild = true;
    try {
      const values = await corpusReviewReads.metadataFacets(buildId, [], { signal: ticket.signal });
      if (!ticket.current() || options.selectedBuildId.value !== buildId) return;
      options.onFacets(values);
      facetsLoadedForBuild = true;
    } catch (exc) {
      if (ticket.current() && !isAbortError(exc)) options.onError(messageOf(exc));
    } finally {
      if (ticket.current()) facetsLoadingForBuild = false;
    }
  }

  async function refreshRecords(reset = false, preferredId = ""): Promise<void> {
    if (!options.selectedBuildId.value) return;
    if (reset) {
      // Queue pages and full Record projections contain server-authoritative review state,
      // including enrichment proposals that may change without advancing RecordRevision.
      // A reset is therefore an explicit invalidation boundary for both cache layers.
      clearGraphQLReadCache();
      generation += 1;
      cache.clear();
      options.recordOffset.value = 0;
    }
    const ticket = latestPage.start();
    const selectionAtStart = selectionVersion;
    recordsLoading.value = true;
    try {
      const page = await corpusReviewReads.queuePage(
        options.selectedBuildId.value,
        options.recordOffset.value,
        options.pageSize,
        { reviewQueue: options.reviewQueue.value, query: options.recordQuery.value },
        { signal: ticket.signal },
      );
      if (!ticket.current()) return;
      if (!page.rows.length && page.total > 0 && options.recordOffset.value > 0) {
        // Concurrent completions can empty the final filtered page. Move to the
        // nearest valid page instead of stranding the reviewer on an empty view.
        options.recordOffset.value = Math.max(
          0,
          Math.floor((page.total - 1) / options.pageSize) * options.pageSize,
        );
        await refreshRecords(false);
        return;
      }
      queueRows.value = page.rows;
      recordTotal.value = page.total;
      hydratedTopologyCount.value = Math.max(hydratedTopologyCount.value, page.topologyCount);
      reviewHydrated.value = true;
      options.onPageLoaded(page.rows);
      const shouldLoadFacets = !facetsLoadedForBuild || reset;
      if (selectionAtStart !== selectionVersion) {
        if (shouldLoadFacets) void loadFacets();
        return;
      }

      const selectedVisible = page.rows.some(
        (item) => item.record_id === options.selectedRecordId.value,
      );
      const keepDraftSelection =
        options.hasActiveDraft() && Boolean(options.selectedRecordId.value);
      const targetId =
        preferredId ||
        (selectedVisible || keepDraftSelection ? options.selectedRecordId.value : "") ||
        page.rows[0]?.record_id ||
        "";
      if (!targetId) {
        latestSelection.cancel();
        loadingRecordId.value = "";
        requestedRecordId.value = "";
        recordError.value = "";
        clearSelection();
        if (shouldLoadFacets) void loadFacets();
        return;
      }
      if (options.hasActiveDraft() && targetId === options.selectedRecordId.value) {
        // An in-progress local edit is already shown optimistically; a server round trip here
        // would briefly revert it for nothing.
        if (shouldLoadFacets) void loadFacets();
        return;
      }
      const row = page.rows.find((item) => item.record_id === targetId);
      await resolveAndActivate(targetId, row?.record_revision ?? null);
      // Build-wide facets are expensive because they inspect every Record. They are
      // autocomplete enrichment, not a prerequisite for reading the selected Record,
      // so never let that O(corpus-size) work race the critical-path Record fetch.
      if (shouldLoadFacets) void loadFacets();
    } catch (exc) {
      if (ticket.current() && !isAbortError(exc)) options.onError(messageOf(exc));
    } finally {
      if (ticket.current()) recordsLoading.value = false;
    }
  }

  /** Re-read one full Record after a durable realtime completion hint. */
  async function refreshRecord(recordId: string): Promise<void> {
    if (!options.selectedBuildId.value || !recordId) return;
    const buildId = options.selectedBuildId.value;
    const epoch = generation;
    const version = (recordGenerations.get(recordId) || 0) + 1;
    recordGenerations.set(recordId, version);
    try {
      clearGraphQLReadCache();
      const [record] = await corpusReviewReads.records(buildId, [recordId]);
      if (
        epoch !== generation ||
        buildId !== options.selectedBuildId.value ||
        recordGenerations.get(recordId) !== version
      )
        return;
      if (!record) return;
      const index = queueRows.value.findIndex((row) => row.record_id === record.record_id);
      if (index >= 0) queueRows.value.splice(index, 1, queueRowFromRecord(record));
      // Selection changes clear selectedRecord before the new Record arrives, while selectedRecordId
      // can still point at the old Record. Do not let a late realtime refresh resurrect that old view.
      const selectedStillOpen =
        record.record_id === options.selectedRecordId.value &&
        options.selectedRecord.value?.record_id === record.record_id;
      if (selectedStillOpen && options.hasActiveDraft()) return;
      cache.set(record.record_id, record);
      if (selectedStillOpen) options.activateRecord(record);
    } catch (exc) {
      if (epoch === generation && !isAbortError(exc)) options.onError(messageOf(exc));
    }
  }

  /** Re-read specific rows in place (a realtime event, a neighbour patch) without re-paging. */
  async function refreshRows(
    recordIds: readonly string[] = queueRows.value.map((row) => row.record_id),
  ): Promise<void> {
    if (!options.selectedBuildId.value || !recordIds.length) return;
    const buildId = options.selectedBuildId.value;
    const epoch = generation;
    // Metadata enrichment rewrites a Record without bumping its revision, so a cached copy would
    // still look current. Drop it; the next open (or the selected Record's refresh) re-reads it.
    for (const id of recordIds) {
      cache.delete(id);
      recordGenerations.set(id, (recordGenerations.get(id) || 0) + 1);
    }
    const versions = new Map(recordIds.map((id) => [id, recordGenerations.get(id)]));
    try {
      // A row refresh is normally caused by a realtime event or a completed mutation. It must
      // observe the server's current revision and disposition rather than a cached projection.
      clearGraphQLReadCache();
      const rows = await corpusReviewReads.rows(buildId, recordIds);
      if (epoch !== generation || buildId !== options.selectedBuildId.value) return;
      if (!rows.length) return;
      const byId = new Map(
        rows
          .filter((row) => versions.get(row.record_id) === recordGenerations.get(row.record_id))
          .map((row) => [row.record_id, row]),
      );
      queueRows.value = queueRows.value.map((row) => byId.get(row.record_id) ?? row);
    } catch (exc) {
      if (epoch === generation && !isAbortError(exc)) options.onError(messageOf(exc));
    }
  }

  /** The visible page's full text, for the clean-up dialog's repeated-running-head detection. */
  async function visiblePageTexts(): Promise<string[]> {
    if (!options.selectedBuildId.value || !queueRows.value.length) return [];
    return corpusReviewReads.texts(
      options.selectedBuildId.value,
      queueRows.value.map((row) => row.record_id),
    );
  }

  /** Remember a Record the caller already has (for example after an optimistic local edit). */
  function remember(record: CorpusRecord | null | undefined) {
    if (!record?.record_id) return;
    cache.set(record.record_id, record);
  }

  /** Patch the review queue's row (and cached Record) from an updated Record. */
  function applyRecord(record: CorpusRecord) {
    // This record came from an authoritative REST response. Drop read projections before keeping
    // the bounded local copy so a later queue refresh cannot resurrect an older disposition.
    clearGraphQLReadCache();
    recordGenerations.set(record.record_id, (recordGenerations.get(record.record_id) || 0) + 1);
    remember(record);
    const index = queueRows.value.findIndex((row) => row.record_id === record.record_id);
    if (index >= 0) queueRows.value.splice(index, 1, queueRowFromRecord(record));
  }

  function clear() {
    generation += 1;
    latestPage.cancel();
    latestSelection.cancel();
    latestFacets.cancel();
    clearGraphQLReadCache();
    cache.clear();
    facetsLoadedForBuild = false;
    facetsLoadingForBuild = false;
    queueRows.value = [];
    recordTotal.value = 0;
    recordsLoading.value = false;
    reviewHydrated.value = false;
    hydratedTopologyCount.value = 0;
    loadingRecordId.value = "";
    recordError.value = "";
    requestedRecordId.value = "";
    recordGenerations.clear();
    clearSelection();
  }

  watch(options.selectedBuildId, clear, { flush: "sync" });
  onScopeDispose(clear, true);

  return {
    queueRows,
    recordTotal,
    recordsLoading,
    reviewHydrated,
    hydratedTopologyCount,
    loadingRecordId,
    recordError,
    requestedRecordId,
    getSelectionVersion: () => selectionVersion,
    retryRecord: () => resolveAndActivate(requestedRecordId.value, null),
    refreshRecords,
    selectRecord,
    selectRecordById,
    remember,
    refreshRows,
    refreshRecord,
    visiblePageTexts,
    applyRecord,
    clear,
  };
}
