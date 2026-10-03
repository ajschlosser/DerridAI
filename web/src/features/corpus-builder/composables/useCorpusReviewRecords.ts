/* Copyright 2026 Aaron John Schlosser, PhD. */
// Owns the review queue's lightweight rows, pagination, and a small selected-Record cache, and
// drives every other review composable through the shared `queueRows`/`selectRecord` contract
// (docs/GRAPHQL.md). The queue list holds `CorpusQueueRow`s; a full `CorpusRecord` is read one at
// a time, only when a row is opened, and kept in an LRU cache so moving between recently seen
// records does not re-read them.
import { onScopeDispose, ref, toRaw, watch, type Ref } from "vue";
import type { CorpusBuild, CorpusRecord } from "../../../api/corpus";
import type { ReviewQueue } from "../../../types/corpus";
import {
  GraphQLRequestError,
  invalidateGraphQLReads,
  isAbortError,
} from "../../../api/graphql/client";
import { createLatestRequest } from "../../../api/graphql/latestRequest";
import {
  corpusReviewReads,
  type CorpusQueueNavigation,
  type CorpusQueueRow,
} from "../api/reviewReads";
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
  reviewerKey?: Ref<string>;
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
  const nextCursor = ref<string | null>(null);
  const previousCursor = ref<string | null>(null);
  const hasNextPage = ref(false);
  const hasPreviousPage = ref(false);
  const dataGeneration = ref<number | null>(null);
  const topologyGeneration = ref<number | null>(null);

  const cache = createRecordCache();
  const latestPage = createLatestRequest();
  const latestSelection = createLatestRequest();
  const latestFacets = createLatestRequest();
  let generation = 0;
  let selectionVersion = 0;
  const recordGenerations = new Map<string, number>();
  const cachedStateVersions = new Map<string, number | null>();
  let facetsLoadedForBuild = false;
  let facetsLoadingForBuild = false;
  let context = "";
  let reconcilePending = false;
  let reconcilePromise: Promise<void> | undefined;

  function invalidateBuild(buildId = options.selectedBuildId.value) {
    if (buildId) invalidateGraphQLReads({ buildId });
  }

  function resetCursor() {
    nextCursor.value = previousCursor.value = null;
    hasNextPage.value = hasPreviousPage.value = false;
  }

  function dropRecords(ids: readonly string[]) {
    for (const id of ids) {
      cache.delete(id);
      cachedStateVersions.delete(id);
      recordGenerations.set(id, (recordGenerations.get(id) || 0) + 1);
    }
    invalidateGraphQLReads({ buildId: options.selectedBuildId.value, recordIds: ids });
  }

  function invalidateQueue(cancelPage = true) {
    invalidateGraphQLReads({
      buildId: options.selectedBuildId.value,
      operations: ["CorpusReviewQueue", "CorpusMetadataFacets"],
    });
    latestFacets.cancel();
    if (cancelPage) {
      latestPage.cancel();
      recordsLoading.value = false;
    }
    facetsLoadingForBuild = facetsLoadedForBuild = false;
  }

  /** Coalesce hints/mutations; membership, counts and backfill come only from the queue read. */
  function reconcileQueue(): Promise<void> {
    reconcilePending = true;
    if (!reconcilePromise) {
      const epoch = generation;
      reconcilePromise = Promise.resolve()
        .then(async () => {
          while (reconcilePending && epoch === generation) {
            reconcilePending = false;
            await refreshRecords();
          }
        })
        .finally(() => {
          reconcilePromise = undefined;
          if (reconcilePending) void reconcileQueue();
        });
    }
    return reconcilePromise;
  }

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
          !cached ||
          (row.record_revision != null && cached.record_revision !== row.record_revision) ||
          (row.state_version != null &&
            cachedStateVersions.get(row.record_id) !== row.state_version)
        );
      },
    );
    if (!neighbours.length) return;
    const buildId = options.selectedBuildId.value;
    invalidateGraphQLReads({
      buildId,
      recordIds: neighbours.map((row) => row.record_id),
    });
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
        for (const record of records) {
          if (versions.get(record.record_id) !== recordGenerations.get(record.record_id)) continue;
          cache.set(record.record_id, record);
          cachedStateVersions.set(
            record.record_id,
            neighbours.find((row) => row.record_id === record.record_id)?.state_version ?? null,
          );
        }
      })
      .catch(() => undefined);
  }

  /** Resolve one Record by id (cache first, dropping a stale entry) and hand it to `activateRecord`. */
  async function resolveAndActivate(
    id: string,
    revisionHint: number | null,
    stateHint: number | null = null,
  ): Promise<void> {
    if (!options.selectedBuildId.value || !id) return;
    const ticket = latestSelection.start();
    selectionVersion += 1;
    const buildId = options.selectedBuildId.value;
    const epoch = generation;
    const recordVersion = recordGenerations.get(id);
    const refreshingSelection =
      options.selectedRecordId.value === id && options.selectedRecord.value?.record_id === id;
    requestedRecordId.value = id;
    options.selectedRecordId.value = id;
    recordError.value = "";
    loadingRecordId.value = "";
    const cached = cache.get(id);
    if (
      cached &&
      (revisionHint == null || cached.record_revision === revisionHint) &&
      (stateHint == null || cachedStateVersions.get(id) === stateHint)
    ) {
      if (toRaw(options.selectedRecord.value) !== toRaw(cached)) options.activateRecord(cached);
      prefetchNeighbours(id);
      return;
    }
    if (cached) invalidateGraphQLReads({ buildId, recordIds: [id] });
    // Never leave a stale Record showing while a different one loads: a slow response for the
    // previous selection could otherwise land after the reviewer has already moved on and a
    // command (accept/reject/edit) would fire against the wrong Record.
    if (!refreshingSelection) options.selectedRecord.value = null;
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
      cachedStateVersions.set(record.record_id, stateHint);
      if (refreshingSelection && options.hasActiveDraft()) return;
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
    await resolveAndActivate(
      target.record_id,
      target.record_revision ?? null,
      target.state_version ?? null,
    );
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

  async function refreshRecords(
    reset = false,
    preferredId = "",
    navigation: CorpusQueueNavigation = {},
    recovered = false,
  ): Promise<void> {
    if (!options.selectedBuildId.value) return;
    const nextContext = JSON.stringify([
      options.selectedBuildId.value,
      options.reviewerKey?.value,
      options.reviewQueue.value,
      options.recordQuery.value,
    ]);
    if (reset || (context && context !== nextContext)) {
      // Queue pages and full Record projections contain server-authoritative review state,
      // including enrichment proposals that may change without advancing RecordRevision.
      // A reset is therefore an explicit invalidation boundary for both cache layers.
      invalidateBuild();
      generation += 1;
      cache.clear();
      cachedStateVersions.clear();
      invalidateQueue();
      resetCursor();
      topologyGeneration.value = dataGeneration.value = null;
      options.recordOffset.value = 0;
      navigation = {};
    }
    context = nextContext;
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
        navigation,
      );
      if (!ticket.current()) return;
      if (!recovered && !page.rows.length && page.total > 0 && options.recordOffset.value > 0) {
        // Concurrent completions can empty the final filtered page. Move to the
        // nearest valid page instead of stranding the reviewer on an empty view.
        options.recordOffset.value = Math.max(
          0,
          Math.floor((page.total - 1) / options.pageSize) * options.pageSize,
        );
        await refreshRecords(false, preferredId, {}, true);
        return;
      }
      if (
        topologyGeneration.value != null &&
        topologyGeneration.value !== page.topologyGeneration
      ) {
        generation += 1;
        cache.clear();
        cachedStateVersions.clear();
        invalidateBuild();
        invalidateQueue(false);
        resetCursor();
      }
      const previousRows = new Map(queueRows.value.map((row) => [row.record_id, row]));
      const changedIds = page.rows
        .filter((row) => {
          const previous = previousRows.get(row.record_id);
          return (
            previous &&
            (row.record_revision !== previous.record_revision ||
              row.state_version !== previous.state_version)
          );
        })
        .map((row) => row.record_id);
      if (changedIds.length) dropRecords(changedIds);
      if (dataGeneration.value != null && dataGeneration.value !== page.dataGeneration) {
        invalidateGraphQLReads({
          buildId: options.selectedBuildId.value,
          operations: ["CorpusMetadataFacets"],
        });
        latestFacets.cancel();
        facetsLoadingForBuild = facetsLoadedForBuild = false;
      }
      queueRows.value = page.rows;
      options.recordOffset.value = page.offset;
      nextCursor.value = page.nextCursor ?? null;
      previousCursor.value = page.previousCursor ?? null;
      hasNextPage.value = page.hasNextPage;
      hasPreviousPage.value = page.hasPreviousPage ?? page.offset > 0;
      dataGeneration.value = page.dataGeneration ?? null;
      topologyGeneration.value = page.topologyGeneration ?? null;
      recordTotal.value = page.total;
      if (options.currentBuild.value) options.currentBuild.value.review_queue_counts = page.counts;
      hydratedTopologyCount.value = page.topologyCount;
      reviewHydrated.value = true;
      options.onPageLoaded(page.rows);
      const shouldLoadFacets = !facetsLoadedForBuild || reset;
      if (selectionAtStart !== selectionVersion || loadingRecordId.value) {
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
      await resolveAndActivate(targetId, row?.record_revision ?? null, row?.state_version ?? null);
      // Build-wide facets are expensive because they inspect every Record. They are
      // autocomplete enrichment, not a prerequisite for reading the selected Record,
      // so never let that O(corpus-size) work race the critical-path Record fetch.
      if (shouldLoadFacets) void loadFacets();
    } catch (exc) {
      if (
        ticket.current() &&
        navigation.cursor &&
        !recovered &&
        exc instanceof GraphQLRequestError &&
        exc.hasCode("STALE_QUEUE_CURSOR")
      ) {
        resetCursor();
        generation += 1;
        cache.clear();
        cachedStateVersions.clear();
        invalidateBuild();
        invalidateQueue();
        await refreshRecords(false, preferredId, {}, true);
        return;
      }
      if (ticket.current() && !isAbortError(exc)) options.onError(messageOf(exc));
    } finally {
      if (ticket.current()) recordsLoading.value = false;
    }
  }

  /** Reconcile a durable completion hint; refresh the selected Record unless it has a draft. */
  async function refreshRecord(recordId: string): Promise<void> {
    if (!options.selectedBuildId.value || !recordId) return;
    await refreshRows([recordId]);
  }

  /** Invalidate affected Records, then reconcile current membership, backfill, counts and facets. */
  async function refreshRows(
    recordIds: readonly string[] = queueRows.value.map((row) => row.record_id),
  ): Promise<void> {
    if (!options.selectedBuildId.value || !recordIds.length) return;
    // Metadata enrichment rewrites a Record without bumping its revision, so a cached copy would
    // still look current. Drop it; the next open (or the selected Record's refresh) re-reads it.
    dropRecords(recordIds);
    invalidateQueue();
    await reconcileQueue();
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
  function applyRecord(record: CorpusRecord, authoritative = true) {
    // Optimistic edits stay local until REST settles; never reconcile them against older state.
    invalidateGraphQLReads({
      buildId: options.selectedBuildId.value,
      recordIds: [record.record_id],
    });
    recordGenerations.set(record.record_id, (recordGenerations.get(record.record_id) || 0) + 1);
    remember(record);
    const index = queueRows.value.findIndex((row) => row.record_id === record.record_id);
    if (index >= 0) queueRows.value.splice(index, 1, queueRowFromRecord(record));
    if (authoritative) {
      invalidateQueue();
      if (reviewHydrated.value) void reconcileQueue();
    }
  }

  function clear(buildId = options.selectedBuildId.value) {
    generation += 1;
    latestPage.cancel();
    latestSelection.cancel();
    latestFacets.cancel();
    invalidateBuild(buildId);
    cache.clear();
    cachedStateVersions.clear();
    resetCursor();
    topologyGeneration.value = dataGeneration.value = null;
    context = "";
    reconcilePending = false;
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

  watch(options.selectedBuildId, (_build, oldBuild) => clear(oldBuild), { flush: "sync" });
  if (options.reviewerKey)
    watch(
      options.reviewerKey,
      (reviewer) => {
        clear();
        if (reviewer) void refreshRecords();
      },
      { flush: "sync" },
    );
  onScopeDispose(() => clear(), true);

  return {
    queueRows,
    recordTotal,
    recordsLoading,
    reviewHydrated,
    hydratedTopologyCount,
    loadingRecordId,
    recordError,
    requestedRecordId,
    nextCursor,
    previousCursor,
    hasNextPage,
    hasPreviousPage,
    dataGeneration,
    topologyGeneration,
    movePage: (direction: "forward" | "backward") =>
      refreshRecords(false, "", {
        cursor: direction === "forward" ? nextCursor.value : previousCursor.value,
        direction,
      }),
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
