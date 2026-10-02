/* Copyright 2026 Aaron John Schlosser, PhD. */

import { openMessageDialog } from "../composables/messageDialog";
import { openMixedWorkValuesDialog as openMixedWorkValues } from "../composables/mixedWorkValuesDialog";
import { openWorkMetadataEditorDialog } from "../composables/workMetadataEditor";
import { openWorkMetadataLlmDialog as openWorkMetadataLlm } from "../composables/workMetadataLlmDialog";
import { openWorkMetadataProposalDialog as openWorkMetadataProposal } from "../composables/workMetadataProposalDialog";
import { openRemoveWorkDialog } from "../composables/removeWorkDialog";
import { openSeparateWorksDialog } from "../composables/separateWorksDialog";
import {
  canonicalWorkSourceType,
  representativeWorkMetadata,
  workMetadataSourceGroups,
  workSourceType,
} from "./workMetadata";
import { toast } from "../composables/notifications";

// The dialogs for a work's metadata and for removing or separating works, drawn as HTML strings. Moved verbatim from the
// legacy runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "api"
  | "applyRecordChanges"
  | "clearFileDerivedState"
  | "cloneAuditValue"
  | "display"
  | "jobLabel"
  | "label"
  | "navigateTo"
  | "parseProposedMetadataValue"
  | "parseWorkMetadataValue"
  | "persistFileNow"
  | "persistPrefs"
  | "providerProfile"
  | "providerProfiles"
  | "providerRequestConfig"
  | "recordStores"
  | "refreshStores"
  | "renderView"
  | "representativeWorkMetadata"
  | "shell"
  | "startJobPolling"
  | "syncJobProgressToasts"
  | "tr"
  | "trf"
  | "uid"
  | "uniqueWorkValues"
  | "workIndex"
  | "workMetadataControlSpec";
type Deps = { state: Loose; corpusCache: Loose } & Record<Helper, Fn>;

/** The metadata fields a work carries, in the order the work editor shows them. */
const WORK_METADATA_FIELDS = [
  "work",
  "source_type",
  "document_type",
  "document_title",
  "short_title",
  "original_title",
  "document_author",
  "container_title",
  "journal_title",
  "editor",
  "edition",
  "volume",
  "issue",
  "pages",
  "year",
  "publication_year",
  "publisher",
  "publication_place",
  "translator",
  "document_language",
  "original_language",
  "document_is_translation",
  "canonical_work_id",
  "isbn",
  "doi",
  "url",
  "full_citation",
  "cover_url",
];

export function createWorkDialogs(deps: Deps) {
  const {
    state,
    api,
    applyRecordChanges,
    clearFileDerivedState,
    cloneAuditValue,
    corpusCache,
    display,
    jobLabel,
    label,
    navigateTo,
    parseProposedMetadataValue,
    parseWorkMetadataValue,
    persistFileNow,
    persistPrefs,
    providerProfile,
    providerProfiles,
    providerRequestConfig,
    recordStores,
    refreshStores,
    renderView,
    shell,
    startJobPolling,
    syncJobProgressToasts,
    tr,
    trf,
    uid,
    uniqueWorkValues,
    workIndex,
    workMetadataControlSpec,
  } = deps;
  function openMixedWorkValuesDialog(work: Any, field: Any, rows: Any) {
    const values = uniqueWorkValues(rows, field);
    openMixedWorkValues({
      work: String(work),
      fieldLabel: label(field),
      recordCount: rows.length,
      values: values.map((entry: Any) => ({
        text: entry.value == null || entry.value === "" ? null : String(display(entry.value)),
        files: [...entry.files].map(String),
        count: entry.count,
      })),
    });
  }
  function openWorkMetadataEditor(work: Any, rows: Any) {
    if (!rows?.length) return toast(tr("works.no_records_found"), { tone: "warning" });
    const available = [
      ...new Set([
        ...WORK_METADATA_FIELDS,
        ...rows.flatMap((row: Any) =>
          Object.keys(row.record).filter((field) =>
            /^(document_|publication_|canonical_|publisher$|translator$|isbn$|full_citation$)/.test(
              field,
            ),
          ),
        ),
      ]),
    ].filter((field) => field !== "updates");
    openWorkMetadataEditorDialog({
      work: String(work),
      recordCount: rows.length,
      fileCount: new Set(rows.map((row: Any) => row.file.name)).size,
      fields: available.map((field) => workMetadataControlSpec(field, rows)),
      inspectMixed: (field) => openMixedWorkValuesDialog(work, field, rows),
      apply: async ({ values }) => {
        const selected = Object.keys(values);
        const changes: Any = {};
        try {
          for (const field of selected)
            changes[field] = parseWorkMetadataValue(field, { value: values[field] }, rows);
        } catch (error: Any) {
          toast(error.message, { tone: "danger" });
          return false;
        }
        if (
          !(await openMessageDialog({
            title: tr("works.apply_metadata_confirm"),
            message: trf("works.apply_fields_to_records", {
              fields: selected.length,
              records: rows.length,
              work,
            }),
            confirmLabel: tr("works.apply_metadata"),
            cancelLabel: tr("ui.cancel"),
          }))
        )
          return false;
        const batchId = uid();
        let changedRecords = 0,
          fieldChanges = 0;
        const touchedFiles = new Set();
        for (const row of rows) {
          const count = applyRecordChanges(row.file, row.index, changes, {
            source: "work_metadata",
            batchId,
            reason: `Bulk work metadata update for ${work}`,
          });
          if (count) {
            changedRecords++;
            fieldChanges += count;
            touchedFiles.add(row.file);
          }
        }
        for (const file of touchedFiles) await persistFileNow(file);
        shell();
        renderView();
        toast(
          trf("works.metadata_applied", {
            records: changedRecords.toLocaleString(),
            fields: fieldChanges.toLocaleString(),
          }),
          { tone: "success" },
        );
        return true;
      },
    });
  }
  function openWorkMetadataLlmDialog(items: Any) {
    const works = (items || []).filter((item: Any) => item?.work && item?.rows?.length);
    if (!works.length) return toast(tr("works.no_work_metadata_rows"), { tone: "warning" });
    const sourceScopes = works.flatMap((item: Any) =>
      workMetadataSourceGroups(item).map((scope) => ({ ...scope, work: item.work })),
    );
    const sourceTypeLabel = (sourceType: string) =>
      tr(
        `works.source_type_${canonicalWorkSourceType(sourceType)}`,
        canonicalWorkSourceType(sourceType).replace(/_/g, " "),
      );
    const sourceScopeCounts = new Map<string, number>();
    for (const scope of sourceScopes) {
      sourceScopeCounts.set(scope.sourceType, (sourceScopeCounts.get(scope.sourceType) || 0) + 1);
    }
    const sourceScopeSummary = [...sourceScopeCounts]
      .map(([sourceType, count]) => `${count} ${sourceTypeLabel(sourceType)}`)
      .join(" · ");
    const sample = sourceScopes.slice(0, 6).map((scope: Any) => ({
      work: String(scope.work),
      sourceTypeLabel: sourceTypeLabel(scope.sourceType),
    }));
    openWorkMetadataLlm({
      scopeCount: sourceScopes.length,
      scopeSummary: sourceScopeSummary,
      sample,
      profiles: providerProfiles(),
      defaultProfileId: state.appConfig.default_provider_profile || "",
      manageProviders: async () => {
        const ok = await openMessageDialog({
          title: tr("works.leave_metadata_title"),
          message: tr("works.leave_metadata_help"),
          confirmLabel: tr("works.open_providers"),
          cancelLabel: tr("ui.cancel"),
        });
        if (ok) navigateTo("providers");
        return ok;
      },
      start: async (profileId: string) => {
        const profile = providerProfile(profileId);
        if (!profile) return void toast(tr("works.provider_required"), { tone: "warning" });
        const config = providerRequestConfig(profile, { textReview: false });
        if (!config?.model)
          return void toast(tr("works.provider_model_required"), { tone: "warning" });
        const payload = sourceScopes.map((scope: Any) => ({
          work: scope.work,
          source_type_scope: scope.sourceType,
          current_metadata: {
            ...representativeWorkMetadata(scope.rows),
            source_type: scope.sourceType,
            source_types: [scope.sourceType],
          },
        }));
        const job = await api("/api/jobs/llm-tool", {
          method: "POST",
          body: JSON.stringify({
            task: "work_metadata",
            label:
              sourceScopes.length === 1
                ? `${tr("works.populate_metadata_llm", "Populate metadata with LLM")} · ${sourceScopes[0].work}`
                : trf("works.populate_all_metadata_label", "Populate metadata · {count} works", {
                    count: sourceScopes.length,
                  }),
            provider_profile_id: profile.id,
            max_concurrent_requests: config.max_concurrent_requests,
            work_metadata: {
              works: payload,
              provider: config.provider,
              model: config.model,
              base_url: config.base_url,
              api_key: config.api_key,
              generation: config.ollama,
              provider_profile_id: profile.id,
            },
          }),
        });
        state.jobs = [job, ...state.jobs.filter((existing: Any) => existing.id !== job.id)];
        syncJobProgressToasts();
        startJobPolling();
        toast(
          trf(
            "works.metadata_lookup_started",
            "Metadata lookup started for {count} source group(s).",
            { count: sourceScopes.length },
          ),
          { tone: "success" },
        );
        if (state.view === "home")
          window.dispatchEvent(new CustomEvent("derridai:dashboard-refresh"));
      },
    });
  }
  function openWorkMetadataProposalResult(job: Any) {
    const proposals = Array.isArray(job.result?.proposals) ? job.result.proposals : [];
    const map = workIndex();
    const flattened: Any[] = [];
    for (const proposal of proposals) {
      const item = map.get(String(proposal.work || ""));
      if (!item) continue;
      const scopedRows = proposal.source_type_scope
        ? item.rows.filter(
            (row: Any) =>
              workSourceType(row) === canonicalWorkSourceType(proposal.source_type_scope),
          )
        : item.rows;
      if (!scopedRows.length) continue;
      const scopedItem = { ...item, rows: scopedRows, count: scopedRows.length };
      const current = representativeWorkMetadata(scopedRows);
      for (const [field, proposed] of Object.entries(proposal.changes || {}))
        flattened.push({
          proposal,
          item: scopedItem,
          field,
          current: current[field],
          proposed,
          rationale: proposal.rationale?.[field] || proposal.match_reason || "",
        });
    }
    const unmatched = proposals
      .filter(
        (item: Any) => item.error || (item.message && !Object.keys(item.changes || {}).length),
      )
      .map((item: Any) => ({
        work: String(item.work ?? ""),
        message: item.error || item.message || "",
      }));
    openWorkMetadataProposal({
      jobLabel: jobLabel(job),
      unmatched,
      entries: flattened.map((entry) => ({
        work: String(entry.item.work),
        recordCount: entry.item.count,
        fieldLabel: label(entry.field),
        current: String(display(entry.current)),
        proposed:
          entry.proposed == null
            ? ""
            : typeof entry.proposed === "object"
              ? JSON.stringify(entry.proposed)
              : String(entry.proposed),
        rationale: entry.rationale || "",
        confidence:
          entry.proposal.confidence != null ? Number(entry.proposal.confidence || 0) : null,
      })),
      apply: async (selections) => {
        const grouped = new Map();
        try {
          for (const { index, value: text } of selections) {
            const entry = flattened[index];
            if (!entry) continue;
            const value = parseProposedMetadataValue(text, entry.proposed);
            const groupKey = `${entry.item.work}::${entry.proposal.source_type_scope || "unknown"}`;
            if (!grouped.has(groupKey))
              grouped.set(groupKey, { item: entry.item, changes: {}, rationale: {} });
            const group = grouped.get(groupKey);
            group.changes[entry.field] = value;
            group.rationale[entry.field] = entry.rationale;
          }
        } catch (error: Any) {
          toast(error.message, { tone: "danger" });
          return false;
        }
        const batchId = uid();
        let changedRecords = 0,
          fieldChanges = 0;
        const touchedFiles = new Set();
        for (const group of grouped.values())
          for (const row of group.item.rows) {
            const count = applyRecordChanges(row.file, row.index, group.changes, {
              source: "work_metadata_llm",
              model: job.model,
              batchId,
              reason: `LLM-assisted bibliographic metadata update for ${group.item.work}`,
              rationale: group.rationale,
            });
            if (count) {
              changedRecords++;
              fieldChanges += count;
              touchedFiles.add(row.file);
            }
          }
        for (const file of touchedFiles) await persistFileNow(file);
        state.jobApplied[job.id] = new Date().toISOString();
        persistPrefs();
        shell();
        renderView();
        toast(
          trf("works.metadata_applied", {
            records: changedRecords.toLocaleString(),
            fields: fieldChanges.toLocaleString(),
          }),
          { tone: "success" },
        );
        return true;
      },
    });
  }
  async function openRemoveWorkModal(work: Any, rows: Any) {
    const fileCounts = new Map();
    for (const row of rows) fileCounts.set(row.file, (fileCounts.get(row.file) || 0) + 1);
    const dbStore =
      state.activeStore && recordStores().some((store: Any) => store.name === state.activeStore)
        ? state.activeStore
        : "";
    openRemoveWorkDialog({
      work: String(work),
      files: [...fileCounts].map(([file, count]) => ({ id: file.id, name: file.name, count })),
      dbStore,
      confirm: async ({ fileIds, removeDb }) => {
        let localDeleted = 0,
          dbDeleted = 0,
          mirrored = 0;
        for (const fileId of fileIds) {
          const file = state.files.find((item: Any) => item.id === fileId);
          if (!file) continue;
          const before = file.records.length;
          file.records = file.records.filter(
            (record: Any) => String(record.work || "(Untitled work)") !== work,
          );
          const removed = before - file.records.length;
          if (removed) {
            localDeleted += removed;
            clearFileDerivedState(file.id);
            file.dirty = new Set([file.records.length ? 0 : -1]);
            await persistFileNow(file);
          }
        }
        if (removeDb) {
          const result = await api(
            `/api/stores/${encodeURIComponent(dbStore)}/works/${encodeURIComponent(work)}`,
            { method: "DELETE" },
          );
          dbDeleted = Number(result.deleted || 0);
          mirrored = Object.values(result.mirrored_deletes || {}).reduce(
            (sum: number, value: Any) => sum + Number(value || 0),
            0,
          );
          state.storeWorksStore = "";
          if (state.storePresence[dbStore]) state.storePresence[dbStore] = {};
          if (state.storePresenceIds[dbStore]) state.storePresenceIds[dbStore] = {};
          await refreshStores();
        }
        persistPrefs();
        shell();
        renderView();
        toast(
          trf("works.removed_summary", {
            work,
            local: localDeleted.toLocaleString(),
            db: removeDb
              ? trf("works.removed_db", " · {db} DB{mirror}", {
                  db: dbDeleted.toLocaleString(),
                  mirror: mirrored
                    ? trf("works.removed_mirror", " · {count} language mirror", {
                        count: mirrored.toLocaleString(),
                      })
                    : "",
                })
              : "",
          }),
          { tone: "success" },
        );
      },
    });
  }
  async function openSeparateWorksModal() {
    const workKey = (record: Any) =>
      String(record?.work || record?.document_title || "").trim() || tr("works.untitled");
    const eligible = state.files.filter((file: Any) => {
      const works = new Set(
        file.records
          .map((record: Any) => String(record?.work || record?.document_title || "").trim())
          .filter(Boolean),
      );
      return works.size > 1;
    });
    if (!eligible.length) return toast(tr("works.no_multi_work_jsonl"), { tone: "warning" });
    openSeparateWorksDialog({
      sources: eligible.map((file: Any) => {
        const groups = new Map<string, number>();
        for (const record of file.records) {
          const work = workKey(record);
          groups.set(work, (groups.get(work) || 0) + 1);
        }
        return {
          id: file.id,
          name: file.name,
          recordCount: file.records.length,
          groups: [...groups].map(([work, count]) => ({
            work,
            count,
            defaultChecked: work !== tr("works.untitled"),
          })),
        };
      }),
      confirm: async ({ fileId, works: selected, removeFromSource }) => {
        const file = state.files.find((item: Any) => item.id === fileId);
        if (!file) return;
        const selectedSet = new Set(selected);
        const created = [];
        for (const work of selected) {
          const records = file.records
            .filter(
              (record: Any) =>
                (String(record?.work || record?.document_title || "").trim() ||
                  tr("works.untitled")) === work,
            )
            .map(cloneAuditValue);
          if (!records.length) continue;
          const stem =
            work
              .replace(/[^a-z0-9]+/gi, "-")
              .replace(/^-|-$/g, "")
              .slice(0, 80) || "untitled-work";
          const derived = {
            id: uid(),
            name: `${stem}.jsonl`,
            records,
            errors: [],
            dirty: new Set(),
            imported_at: new Date().toISOString(),
            derived_from: { type: "work_separation", source_file: file.name, work },
          };
          state.files.push(derived);
          await persistFileNow(derived);
          created.push(derived);
        }
        if (removeFromSource) {
          file.records = file.records.filter(
            (record: Any) =>
              !selectedSet.has(
                String(record?.work || record?.document_title || "").trim() || tr("works.untitled"),
              ),
          );
          file.dirty = new Set(file.records.map((_: Any, index: Any) => index));
          await persistFileNow(file);
        }
        if (created.length) state.activeFileId = created[0].id;
        corpusCache.fields = null;
        persistPrefs();
        shell();
        renderView();
        toast(trf("works.created_tabs", { count: created.length }), {
          tone: "success",
        });
      },
    });
  }
  return {
    openMixedWorkValuesDialog,
    openWorkMetadataEditor,
    openWorkMetadataLlmDialog,
    openWorkMetadataProposalResult,
    openRemoveWorkModal,
    openSeparateWorksModal,
  };
}
