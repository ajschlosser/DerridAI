/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref, watch, type Ref } from "vue";
import {
  corpusBuilderApi,
  type CorpusBuild,
  type CorpusRecord,
  type HumanEvidenceSource,
  type SourceBlock,
} from "../../../api/corpus";
import type { ProviderProfile } from "../../../api/system";
import type { ReviewQueue } from "../../../types/corpus";
import type { ReviewViewport } from "./useCorpusReviewWorkspace";
import { describeDecisionResult } from "../domain/metadataDecisions";
import { isUsableMetadataSuggestion } from "../../../domain/metadataValues";
import { allEvidenceBlockIds } from "../../../domain/metadataEvidence";

type MessageTone = "error" | "notice";
type I18nValues = Record<string, string | number>;

interface EditorialMemory {
  conventions: Record<string, { value: unknown; confirmed_records: number }>;
  examples: Record<
    string,
    Array<{ record_id: string; value: unknown; similarity: number; excerpt: string }>
  >;
  reset_at?: string | null;
  convention_count: number;
  example_count: number;
}

interface CorpusMetadataReviewOptions {
  currentBuild: Ref<CorpusBuild | null>;
  selectedRecord: Ref<CorpusRecord | null>;
  selectedRecordId: Ref<string>;
  /** Patch the review queue's row (and cached Record) from an updated Record. */
  applyRecordToQueue: (record: CorpusRecord) => void;
  busy: Ref<string>;
  selectedEvidenceField: Ref<string>;
  reviewInspectorTab: Ref<"metadata" | "evidence" | "source" | "semantic">;
  selectedPdfPage: Ref<number>;
  sourceBlocks: Ref<SourceBlock[]>;
  selectedReviewIds: Ref<Set<string>>;
  reviewQueue: Ref<ReviewQueue>;
  recordQuery: Ref<string>;
  llmActionProviderId: Ref<string>;
  llmActionModel: Ref<string>;
  selectedProviderId: Ref<string>;
  providerProfiles: Ref<ProviderProfile[]>;
  directProfilePayloadWithModel: (
    profileId: string,
    modelOverride?: string,
  ) => Record<string, unknown> | null;
  captureReviewViewport: () => ReviewViewport;
  restoreReviewViewport: (
    snapshot: ReviewViewport,
    options?: { record?: boolean; inspector?: boolean },
  ) => Promise<void>;
  queueRecordRequest: (
    recordId: string | readonly string[],
    fields: string[],
    request: (rebase: boolean) => Promise<unknown>,
    onFailure?: () => void | Promise<void>,
    retryOnFailure?: boolean,
  ) => void;
  applyAuthoritativeRecord: (record: CorpusRecord, build?: CorpusBuild | null) => void;
  syncBuildInRail: (build: CorpusBuild) => void;
  registerBuildOperation: (build: CorpusBuild) => void;
  startPolling: () => void;
  refreshBuild: () => Promise<void>;
  refreshRecords: (reset?: boolean, preferredId?: string) => Promise<void>;
  recordMetadata: (record: CorpusRecord) => Record<string, unknown>;
  metadataDraftKey: (buildId: string, recordId: string) => string;
  setMessage: (message: string, tone?: MessageTone) => void;
  t: (key: string, fallback?: string) => string;
  tf: (key: string, fallbackOrValues?: string | I18nValues, values?: I18nValues) => string;
}

export function useCorpusMetadataReview(options: CorpusMetadataReviewOptions) {
  const metadataSavingField = ref("");
  const metadataSavedField = ref("");
  const metadataDraft = ref("{}");
  const bulkMetadataOpen = ref(false);
  const metadataEnrichmentOpen = ref(false);
  const metadataEditorDirty = ref(false);
  const editorialMemoryOpen = ref(false);
  const editorialMemory = ref<EditorialMemory>({
    conventions: {},
    examples: {},
    convention_count: 0,
    example_count: 0,
  });
  const metadataRerunFamily = ref("all");
  const metadataHumanValues = ref<Record<string, Set<string>>>({});
  const metadataObservedValues = ref<Record<string, string[]>>({});

  watch(options.selectedRecordId, () => {
    metadataSavingField.value = "";
    metadataSavedField.value = "";
  });

  const metadataKnownValues = computed<Record<string, string[]>>(() => {
    const out: Record<string, Set<string>> = {};
    for (const [field, values] of Object.entries(metadataObservedValues.value)) {
      for (const value of values) {
        if (!isUsableMetadataSuggestion(value)) continue;
        (out[field] ??= new Set()).add(value.trim());
      }
    }
    // Build-wide observed values come from the server (metadata_facets), so suggestions no longer
    // depend on which queue page happens to be loaded.
    for (const [field, values] of Object.entries(metadataHumanValues.value)) {
      for (const value of values) (out[field] ??= new Set()).add(value);
    }
    return Object.fromEntries(
      Object.entries(out).map(([field, values]) => [
        field,
        [...values].sort((a, b) => a.localeCompare(b)),
      ]),
    );
  });

  function rememberMetadataValues(field: string, value: unknown) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (!isUsableMetadataSuggestion(item)) continue;
      (metadataHumanValues.value[field] ??= new Set()).add(item.trim());
    }
  }

  function applyOptimisticMetadata(changes: Record<string, unknown>) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return null;
    const buildId = options.currentBuild.value.build_id;
    const recordId = options.selectedRecord.value.record_id;
    const expectedRevision = Number(options.selectedRecord.value.record_revision || 1);
    const row: CorpusRecord = {
      ...options.selectedRecord.value,
      ...changes,
      record_revision: expectedRevision + 1,
    } as CorpusRecord;

    options.selectedRecord.value = row;
    metadataDraft.value = JSON.stringify(options.recordMetadata(row), null, 2);
    options.applyRecordToQueue(row);
    metadataEditorDirty.value = false;
    try {
      localStorage.removeItem(options.metadataDraftKey(buildId, recordId));
    } catch {
      // Browser storage is optional.
    }
    return { buildId, recordId, expectedRevision };
  }

  /**
   * Apply a review decision as locally authoritative before persistence finishes.
   *
   * Canonical FieldAssertions still come from the server. The temporary
   * `optimistic_review` marker only tells the review UI not to let that older
   * canonical projection keep a just-decided field open while its serialized
   * mutation is in flight.
   */
  function applyOptimisticMetadataDecision(
    values: Record<string, unknown>,
    confirmedAbsentFields: ReadonlySet<string> = new Set(),
    extraChanges: Record<string, unknown> = {},
  ) {
    const record = options.selectedRecord.value;
    if (!record) return null;
    const decidedFields = new Set(Object.keys(values));
    const fieldStatus = { ...(record.metadata_field_status || {}) } as Record<
      string,
      Record<string, unknown>
    >;
    for (const [field, value] of Object.entries(values)) {
      const absent = confirmedAbsentFields.has(field);
      fieldStatus[field] = {
        ...(fieldStatus[field] || {}),
        status: absent ? "confirmed_absent" : "human_confirmed",
        method: "human",
        derivation_method: "human",
        authority_status: "human_confirmed",
        evaluation_status: absent ? "no_supported_value" : "value_supported",
        value_status: absent ? "confirmed_absent" : "present",
        value_source: "human",
        verification_status: "reviewed",
        proposed_value: absent ? null : value,
        suggested_absence: false,
        optimistic_review: true,
      };
    }
    const withoutDecided = (fields: string[] | undefined) =>
      (fields || []).filter((field) => !decidedFields.has(String(field)));
    const incompleteFields = withoutDecided(record.metadata_incomplete_fields);
    const reviewFields = withoutDecided(record.metadata_review_fields);
    const metadataComplete = incompleteFields.length === 0 && reviewFields.length === 0;
    const issueCodes = (record.review_issue_codes || []).filter(
      (code) => !(metadataComplete && code === "metadata"),
    );
    let reviewState = record.review_state;
    if (metadataComplete && reviewState === "metadata") {
      reviewState = issueCodes.includes("source")
        ? "source"
        : issueCodes.includes("topology")
          ? "topology"
          : "ready";
    }
    return applyOptimisticMetadata({
      ...extraChanges,
      ...values,
      metadata_field_status: fieldStatus,
      metadata_incomplete_fields: incompleteFields,
      metadata_review_fields: reviewFields,
      acceptance_blocking_fields: withoutDecided(record.acceptance_blocking_fields),
      metadata_complete: metadataComplete,
      metadata_needs_attention: !metadataComplete,
      metadata_attention_reasons: metadataComplete ? [] : record.metadata_attention_reasons || [],
      review_issue_codes: issueCodes,
      review_state: reviewState,
    });
  }

  async function saveMetadata() {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const viewport = options.captureReviewViewport();
    let changes: Record<string, unknown>;
    try {
      changes = JSON.parse(metadataDraft.value);
    } catch {
      options.setMessage(options.t("pdf_corpus.metadata_invalid"), "error");
      return;
    }
    const context = applyOptimisticMetadata(changes);
    if (!context) return;
    await options.restoreReviewViewport(viewport);
    options.queueRecordRequest(context.recordId, Object.keys(changes), (rebase) =>
      corpusBuilderApi.patchMetadata(
        context.buildId,
        context.recordId,
        changes,
        rebase ? undefined : context.expectedRevision,
      ),
    );
  }

  /**
   * Save a field's cited spans. The server replaces the whole entry, so spans cited from other records are carried
   * over unless `externalBlockIds` replaces them; editing the record's own spans must never drop them.
   */
  async function persistEvidence(field: string, blockIds: string[], externalBlockIds?: string[]) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const viewport = options.captureReviewViewport();
    const existing = options.selectedRecord.value.metadata_evidence?.[field];
    const externalIds = Array.from(
      new Set((externalBlockIds ?? existing?.external_block_ids ?? []).map(String)),
    );
    const buildId = options.currentBuild.value.build_id;
    const recordId = options.selectedRecord.value.record_id;
    const expectedRevision = Number(options.selectedRecord.value.record_revision || 1);
    const evidence = {
      ...(options.selectedRecord.value.metadata_evidence || {}),
      [field]: {
        ...(existing || {}),
        block_ids: blockIds,
        external_block_ids: externalIds,
        confidence: existing?.confidence ?? 1,
        reason: existing?.reason || options.t("pdf_corpus.human_evidence_reason"),
      },
    };
    const row: CorpusRecord = {
      ...options.selectedRecord.value,
      metadata_evidence: evidence,
      record_revision: expectedRevision + 1,
    } as CorpusRecord;

    options.selectedRecord.value = row;
    metadataDraft.value = JSON.stringify(options.recordMetadata(row), null, 2);
    options.applyRecordToQueue(row);
    await options.restoreReviewViewport(viewport);
    options.queueRecordRequest(recordId, [field], (rebase) =>
      corpusBuilderApi.patchEvidence(
        buildId,
        recordId,
        field,
        blockIds,
        existing?.confidence ?? 1,
        existing?.reason || options.t("pdf_corpus.human_evidence_reason"),
        rebase ? undefined : expectedRevision,
        externalIds,
      ),
    );
  }

  /** Replace the spans `field` cites from other records, keeping its own spans and its value unchanged. */
  async function setExternalEvidenceBlocks(field: string, blockIds: string[]) {
    if (!options.currentBuild.value || !options.selectedRecord.value || !field) return;
    const own = (options.selectedRecord.value.metadata_evidence?.[field]?.block_ids || []).map(
      String,
    );
    await persistEvidence(field, own, blockIds);
  }

  async function assignEvidenceBlock(field: string, blockId: string) {
    if (!options.currentBuild.value || !options.selectedRecord.value || !field || !blockId) return;
    options.selectedEvidenceField.value = field;
    const existing = options.selectedRecord.value.metadata_evidence?.[field];
    const ids = new Set((existing?.block_ids || []).map(String));
    if (ids.has(blockId)) return;
    ids.add(blockId);
    await persistEvidence(field, Array.from(ids));
  }

  async function toggleEvidenceBlock(blockId: string) {
    if (
      !options.currentBuild.value ||
      !options.selectedRecord.value ||
      !options.selectedEvidenceField.value
    ) {
      return;
    }
    const field = options.selectedEvidenceField.value;
    const existing = options.selectedRecord.value.metadata_evidence?.[field];
    const ids = new Set((existing?.block_ids || []).map(String));
    if (ids.has(blockId)) ids.delete(blockId);
    else ids.add(blockId);
    await persistEvidence(field, Array.from(ids));
  }

  /** Replace the selected field's cited spans with exactly `blockIds` (used by select all / clear). */
  async function setEvidenceBlocks(blockIds: string[]) {
    const field = options.selectedEvidenceField.value;
    if (!options.currentBuild.value || !options.selectedRecord.value || !field) return;
    await persistEvidence(field, Array.from(new Set(blockIds.map(String))));
  }

  async function requeueCurrentRecord() {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    options.busy.value = "record";
    try {
      const availableProfileIds = new Set(
        options.providerProfiles.value.map((profile) => profile.id),
      );
      const profileId =
        [options.llmActionProviderId.value, options.selectedProviderId.value].find(
          (id) => Boolean(id) && availableProfileIds.has(id),
        ) ||
        options.providerProfiles.value[0]?.id ||
        "";
      if (!profileId) throw new Error(options.t("pdf_corpus.no_provider_profile"));
      const actionPayload = options.directProfilePayloadWithModel(
        profileId,
        options.llmActionModel.value,
      ) || {
        provider_profile_id: profileId,
        model: options.llmActionModel.value || undefined,
      };
      await corpusBuilderApi.requeueMetadata(
        options.currentBuild.value.build_id,
        options.selectedRecord.value.record_id,
        actionPayload,
      );
      await options.refreshBuild();
      options.setMessage(options.t("pdf_corpus.requeue_requested"));
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  /**
   * Save one reviewed value. With `evidenceBlockId` the selected text's source block is bound
   * as that value's evidence in the same request (and the same optimistic update), so the
   * reviewer never leaves the field list.
   */
  async function resolveMetadataField(
    field: string,
    value: unknown,
    evidenceBlockId = "",
    humanSource?: HumanEvidenceSource,
  ) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    rememberMetadataValues(field, value);
    const existingEvidence = options.selectedRecord.value.metadata_evidence?.[field];
    const evidenceIds = evidenceBlockId
      ? Array.from(new Set([...(existingEvidence?.block_ids || []).map(String), evidenceBlockId]))
      : undefined;
    const externalIds = humanSource?.externalBlockIds?.map(String);
    const viewport = options.captureReviewViewport();
    metadataSavingField.value = field;
    metadataSavedField.value = "";
    const evidenceChanged = Boolean(externalIds?.length || evidenceIds);
    const context = applyOptimisticMetadataDecision(
      { [field]: value },
      new Set(),
      evidenceChanged
        ? {
            metadata_evidence: {
              ...(options.selectedRecord.value.metadata_evidence || {}),
              [field]: {
                ...(existingEvidence || {}),
                ...(externalIds?.length ? { external_block_ids: externalIds } : {}),
                ...(evidenceIds ? { block_ids: evidenceIds } : {}),
                confidence: existingEvidence?.confidence ?? 1,
                reason: existingEvidence?.reason || options.t("pdf_corpus.human_evidence_reason"),
              },
            },
          }
        : {},
    );
    if (!context) {
      metadataSavingField.value = "";
      return;
    }
    // The value is already applied optimistically. Release the editor before the
    // first await so a slow/stalled persistence request cannot leave Record Review
    // frozen in "Saving…". The mutation queue still serializes canonical writes.
    metadataSavingField.value = "";
    metadataSavedField.value = field;
    await options.restoreReviewViewport(viewport, { inspector: true });
    options.queueRecordRequest(
      context.recordId,
      [field],
      async (rebase) => {
        const result = await corpusBuilderApi.metadataDecision(
          context.buildId,
          context.recordId,
          field,
          value,
          rebase ? undefined : context.expectedRevision,
          false,
          evidenceIds,
          humanSource,
        );
        options.applyAuthoritativeRecord(result.record, result.build);
        return result;
      },
      async () => {
        // Roll the optimistic value back to what the server holds. Do not clear a
        // newer field's success marker when rapid saves are queued for one record.
        if (
          options.selectedRecordId.value === context.recordId &&
          metadataSavedField.value === field
        ) {
          metadataSavedField.value = "";
        }
        await options.refreshRecords(false, context.recordId);
      },
    );
  }

  async function resolveMetadataSuggestions(changes: Record<string, unknown>) {
    if (
      !options.currentBuild.value ||
      !options.selectedRecord.value ||
      !Object.keys(changes).length
    ) {
      return;
    }
    for (const [field, value] of Object.entries(changes)) {
      rememberMetadataValues(field, value);
    }
    const viewport = options.captureReviewViewport();
    metadataSavingField.value = "__batch__";
    metadataSavedField.value = "";
    const context = applyOptimisticMetadataDecision(changes);
    if (!context) {
      metadataSavingField.value = "";
      return;
    }
    // Batch decisions are optimistic too: do not hold the entire metadata panel
    // in a Saving state while the serialized request is in flight.
    metadataSavingField.value = "";
    await options.restoreReviewViewport(viewport, { inspector: true });
    options.queueRecordRequest(
      context.recordId,
      Object.keys(changes),
      async (rebase) => {
        const result = await corpusBuilderApi.metadataDecisionBatch(
          context.buildId,
          context.recordId,
          changes,
          rebase ? undefined : context.expectedRevision,
        );
        options.applyAuthoritativeRecord(result.record, result.build);
        const summary = describeDecisionResult(result, options.tf);
        options.setMessage(summary.message, summary.tone);
        return result;
      },
      async () => {
        await options.refreshRecords(false, context.recordId);
      },
    );
  }

  async function resolveMetadataNoValue(field: string) {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const viewport = options.captureReviewViewport();
    metadataSavingField.value = field;
    metadataSavedField.value = "";
    const context = applyOptimisticMetadataDecision({ [field]: null }, new Set([field]));
    if (!context) {
      metadataSavingField.value = "";
      return;
    }
    metadataSavingField.value = "";
    metadataSavedField.value = field;
    await options.restoreReviewViewport(viewport, { inspector: true });
    options.queueRecordRequest(
      context.recordId,
      [field],
      async (rebase) => {
        const result = await corpusBuilderApi.metadataDecision(
          context.buildId,
          context.recordId,
          field,
          null,
          rebase ? undefined : context.expectedRevision,
          true,
        );
        options.applyAuthoritativeRecord(result.record, result.build);
        return result;
      },
      async () => {
        // Roll the optimistic value back to what the server holds without
        // clobbering feedback from a newer queued decision.
        if (
          options.selectedRecordId.value === context.recordId &&
          metadataSavedField.value === field
        ) {
          metadataSavedField.value = "";
        }
        await options.refreshRecords(false, context.recordId);
      },
    );
  }

  async function clearMetadataSuggestionCache() {
    if (
      !window.confirm(
        options.t(
          "pdf_corpus.clear_metadata_cache_confirm",
          "Clear remembered metadata suggestions? This will not change reviewed records or their history.",
        ),
      )
    ) {
      return;
    }
    options.busy.value = "metadata-cache";
    try {
      const result = await corpusBuilderApi.clearAllMetadataCache();
      options.setMessage(
        options.tf(
          "pdf_corpus.metadata_cache_cleared",
          "Cleared {count} remembered suggestion(s).",
          { count: result.cleared },
        ),
      );
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function runMetadataEnrichment(payload: {
    providerProfileId: string;
    model: string;
    families: string[];
    scope: string;
    passes: number;
    recordIds: string[];
  }) {
    if (!options.currentBuild.value) return;
    options.busy.value = "metadata-enrichment";
    try {
      const actionPayload = options.directProfilePayloadWithModel(
        payload.providerProfileId,
        payload.model,
      ) || {
        provider_profile_id: payload.providerProfileId,
        model: payload.model || undefined,
      };
      options.currentBuild.value = await corpusBuilderApi.rerunMetadataEnrichment(
        options.currentBuild.value.build_id,
        {
          ...actionPayload,
          families: payload.families,
          scope: payload.scope,
          passes: payload.passes,
          record_ids: payload.recordIds,
        },
      );
      metadataEnrichmentOpen.value = false;
      options.syncBuildInRail(options.currentBuild.value);
      options.registerBuildOperation(options.currentBuild.value);
      options.startPolling();
      options.setMessage(options.t("pdf_corpus.metadata_enrichment_started"));
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function openEditorialMemory() {
    if (!options.currentBuild.value) return;
    options.busy.value = "editorial-memory";
    try {
      editorialMemory.value = await corpusBuilderApi.editorialMemory(
        options.currentBuild.value.build_id,
      );
      editorialMemoryOpen.value = true;
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function resetEditorialMemory() {
    if (!options.currentBuild.value) return;
    options.busy.value = "editorial-memory";
    try {
      editorialMemory.value = await corpusBuilderApi.resetEditorialMemory(
        options.currentBuild.value.build_id,
      );
      options.setMessage(options.t("pdf_corpus.editorial_memory_reset_done"));
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  function handleMetadataDirty(value: boolean) {
    metadataEditorDirty.value = value;
  }

  function showMetadataSource(field: string) {
    options.selectedEvidenceField.value = field;
    options.reviewInspectorTab.value = "evidence";
    const ids = allEvidenceBlockIds(options.selectedRecord.value?.metadata_evidence?.[field]);
    const first = options.sourceBlocks.value.find((block) => ids.includes(block.block_id));
    if (first) {
      options.selectedPdfPage.value = Number(first.page || options.selectedPdfPage.value);
    }
  }

  async function rerunMetadata() {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    const viewport = options.captureReviewViewport();
    options.busy.value = "record";
    try {
      const profileId = options.llmActionProviderId.value || options.selectedProviderId.value;
      const payload = {
        ...(options.directProfilePayloadWithModel(profileId, options.llmActionModel.value) || {
          provider_profile_id: profileId,
          model: options.llmActionModel.value || undefined,
        }),
      } as Record<string, unknown>;
      if (metadataRerunFamily.value !== "all") {
        payload.families = [metadataRerunFamily.value];
      }
      const row = await corpusBuilderApi.rerunMetadata(
        options.currentBuild.value.build_id,
        options.selectedRecord.value.record_id,
        payload,
      );
      options.selectedRecord.value = row;
      metadataDraft.value = JSON.stringify(options.recordMetadata(row), null, 2);
      await options.refreshBuild();
      await options.refreshRecords(false, row.record_id);
      await options.restoreReviewViewport(viewport);
      options.reviewInspectorTab.value = "metadata";
      options.setMessage(
        metadataRerunFamily.value === "all"
          ? options.t("pdf_corpus.metadata_rerun")
          : options.tf("pdf_corpus.metadata_family_rerun", {
              family: options.t(
                `pdf_corpus.metadata_family.${metadataRerunFamily.value}`,
                metadataRerunFamily.value,
              ),
            }),
      );
    } catch (exc) {
      await options.restoreReviewViewport(viewport);
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function applyBulkMetadata(payload: {
    changes: Record<string, unknown>;
    applyToAll: boolean;
  }) {
    if (!options.currentBuild.value) return;
    options.busy.value = "bulk-metadata";
    try {
      const result = await corpusBuilderApi.bulkMetadata(
        options.currentBuild.value.build_id,
        payload.changes,
        {
          recordIds: payload.applyToAll ? [] : Array.from(options.selectedReviewIds.value),
          applyToAll: payload.applyToAll,
          reviewQueue: options.reviewQueue.value,
          query: options.recordQuery.value,
        },
      );
      bulkMetadataOpen.value = false;
      await options.refreshBuild();
      await options.refreshRecords(false, options.selectedRecordId.value);
      options.setMessage(
        options.tf("pdf_corpus.bulk_metadata_applied", {
          count: result.changed,
        }),
      );
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  return {
    metadataSavingField,
    metadataSavedField,
    metadataDraft,
    bulkMetadataOpen,
    metadataEnrichmentOpen,
    metadataEditorDirty,
    editorialMemoryOpen,
    editorialMemory,
    metadataRerunFamily,
    metadataHumanValues,
    metadataObservedValues,
    metadataKnownValues,
    rememberMetadataValues,
    saveMetadata,
    assignEvidenceBlock,
    toggleEvidenceBlock,
    setEvidenceBlocks,
    setExternalEvidenceBlocks,
    requeueCurrentRecord,
    resolveMetadataField,
    resolveMetadataSuggestions,
    resolveMetadataNoValue,
    clearMetadataSuggestionCache,
    runMetadataEnrichment,
    openEditorialMemory,
    resetEditorialMemory,
    handleMetadataDirty,
    showMetadataSource,
    rerunMetadata,
    applyBulkMetadata,
  };
}
