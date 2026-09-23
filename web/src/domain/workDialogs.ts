/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

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
  | "decorateDisabledControls"
  | "display"
  | "jobLabel"
  | "label"
  | "navigateTo"
  | "openMessageModal"
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
  | "showAppModal"
  | "startJobPolling"
  | "syncJobProgressToasts"
  | "toast"
  | "tr"
  | "trf"
  | "uid"
  | "uniqueWorkValues"
  | "workIndex"
  | "workMetadataControl"
  | "workflowProviderSelectHtml"
  | "workflowProviderSummaryHtml";
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
    decorateDisabledControls,
    display,
    jobLabel,
    label,
    navigateTo,
    openMessageModal,
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
    representativeWorkMetadata,
    shell,
    showAppModal,
    startJobPolling,
    syncJobProgressToasts,
    toast,
    tr,
    trf,
    uid,
    uniqueWorkValues,
    workIndex,
    workMetadataControl,
    workflowProviderSelectHtml,
    workflowProviderSummaryHtml,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  function openMixedWorkValuesDialog(work: Any, field: Any, rows: Any) {
    const values = uniqueWorkValues(rows, field);
    const dialog = document.createElement("dialog");
    dialog.className = "mixed-values-dialog";
    dialog.setAttribute("aria-labelledby", "mixedValuesTitle");
    dialog.innerHTML = `<div class="dh"><div><span class="section-label">${esc(tr("works.metadata_variants", "Metadata variants"))}</span><h2 class="dialog-title" id="mixedValuesTitle">${esc(label(field))}</h2><div class="dialog-subtitle">${esc(work)} · ${values.length.toLocaleString()} ${esc(tr("works.unique_values", "unique values"))} · ${rows.length.toLocaleString()} ${esc(tr("dynamic.records", "records"))}</div></div><button class="btn icon-only" type="button" data-close aria-label="${esc(tr("ui.close", "Close"))}">${icon("close")}</button></div><div class="db mixed-values-body"><p class="note">${esc(tr("works.mixed_values_help", "These are the distinct values currently present across records for this work. Counts help distinguish a dominant value from an isolated inconsistency before you bulk-edit metadata."))}</p><div class="mixed-values-list">${values.map((entry: Any, index: Any) => `<article class="mixed-value-row"><span class="mixed-value-rank">${index + 1}</span><div class="mixed-value-copy"><b>${esc(entry.value == null || entry.value === "" ? tr("ui.unset", "Unset") : display(entry.value))}</b><small>${esc([...entry.files].slice(0, 3).join(" · "))}${entry.files.size > 3 ? ` · +${entry.files.size - 3}` : ""}</small></div><span class="mixed-value-count">${entry.count.toLocaleString()} <small>${esc(entry.count === 1 ? tr("dynamic.record_one", "record") : tr("dynamic.records", "records"))}</small></span></article>`).join("")}</div></div><div class="da"><button class="btn primary" type="button" data-close>${esc(tr("ui.done", "Done"))}</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
  }
  function openWorkMetadataEditor(work: Any, rows: Any) {
    if (!rows?.length) return toast(tr("works.no_records_found", "No records found for this work"));
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
    const dialog = document.createElement("dialog");
    dialog.className = "work-metadata-dialog";
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(tr("works.edit_work_metadata", "Edit work metadata"))}</h2><div class="dialog-subtitle">${esc(work)} · ${esc(trf("works.associated_records_files", "{records} associated records across {files} files", { records: rows.length.toLocaleString(), files: new Set(rows.map((row: Any) => row.file.name)).size }))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db work-metadata-body"><div class="info">${esc(tr("works.edit_metadata_apply_help", "Check Apply only for fields that should be changed across every associated record. Changing work renames the work for all loaded records. Every modified field is written to each record's updates history."))}</div><div class="work-meta-table">${available.map((field) => workMetadataControl(field, rows)).join("")}</div></div>
  <div class="da"><button class="btn" data-close>${esc(tr("ui.cancel", "Cancel"))}</button><button class="btn primary" id="applyWorkMetadata">${esc(trf("works.apply_selected_to_records", "Apply selected metadata to {count} records", { count: rows.length.toLocaleString() }))}</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    dialog
      .querySelectorAll("[data-inspect-mixed-field]")
      .forEach(
        (button: Any) =>
          (button.onclick = () =>
            openMixedWorkValuesDialog(work, button.dataset.inspectMixedField, rows)),
      );
    dialog.querySelector("#applyWorkMetadata").onclick = async () => {
      const selected = [...dialog.querySelectorAll("[data-work-meta-apply]:checked")].map(
        (box) => box.dataset.workMetaApply,
      );
      if (!selected.length)
        return toast(tr("works.select_field_to_apply", "Select at least one work metadata field to apply"));
      const changes: Any = {};
      try {
        for (const field of selected) {
          const control = dialog.querySelector(`[data-work-meta-value="${CSS.escape(field)}"]`);
          changes[field] = parseWorkMetadataValue(field, control, rows);
        }
      } catch (error: Any) {
        return toast(error.message);
      }
      if (
        !(await openMessageModal({
          title: tr("works.apply_metadata_confirm", "Apply work metadata?"),
          message: trf(
            "works.apply_fields_to_records",
            "Apply {fields} metadata field(s) to all {records} records associated with {work}?",
            { fields: selected.length, records: rows.length, work },
          ),
          confirmLabel: tr("works.apply_metadata", "Apply metadata"),
          cancelLabel: tr("ui.cancel", "Cancel"),
        }))
      )
        return;
      const applyButton = dialog.querySelector("#applyWorkMetadata");
      if (applyButton) {
        applyButton.disabled = true;
        applyButton.textContent = tr("works.applying_metadata", "Applying metadata…");
      }
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
      close();
      shell();
      renderView();
      toast(
        trf(
          "works.metadata_applied",
          "Updated {records} records · {fields} tracked field changes",
          { records: changedRecords.toLocaleString(), fields: fieldChanges.toLocaleString() },
        ),
        { tone: "success" },
      );
    };
  }
  function openWorkMetadataLlmDialog(items: Any) {
    const works = (items || []).filter((item: Any) => item?.work && item?.rows?.length);
    if (!works.length)
      return toast(
        tr("works.no_work_metadata_rows", "No work records are available for metadata lookup."),
      );
    const profiles = providerProfiles();
    const selectedId = state.appConfig.default_provider_profile || profiles[0]?.id || "";
    const dialog = document.createElement("dialog");
    dialog.className = "workflow-dialog work-metadata-llm-dialog";
    const sample = works
      .slice(0, 6)
      .map((item: Any) => `<span>${esc(item.work)}</span>`)
      .join("");
    dialog.innerHTML = `<div class="workflow-dialog-header"><div class="workflow-heading"><span class="workflow-icon">${icon("spark")}</span><div><p>${esc(tr("works.metadata_workflow_kicker", "Bibliographic enrichment"))}</p><h2>${esc(tr("works.populate_metadata_llm", "Populate metadata with LLM"))}</h2><span>${esc(tr("works.populate_metadata_help", "DerridAI searches format-appropriate public bibliographic sources (Open Library, Google Books, and Crossref), asks the selected LLM to identify the best match, then returns proposed metadata changes for review. Nothing is applied automatically."))}</span></div></div><button class="icon-btn workflow-close" data-close title="${esc(tr("ui.close", "Close"))}">×</button></div>
    <ol class="workflow-steps"><li class="active"><span>1</span><b>${esc(tr("works.step_scope", "Works"))}</b></li><li class="active"><span>2</span><b>${esc(tr("works.step_provider", "Provider profile"))}</b></li><li><span>3</span><b>${esc(tr("works.step_review", "Review proposals"))}</b></li></ol>
    <div class="workflow-form"><section class="workflow-section"><div class="workflow-section-copy"><b>${esc(tr("works.lookup_scope", "Lookup scope"))}</b><span>${esc(trf("works.lookup_scope_help", "Retrieve bibliographic metadata for {count} work(s).", { count: works.length.toLocaleString() }))}</span></div><div class="work-metadata-scope"><strong>${works.length.toLocaleString()} ${esc(tr("dynamic.works", "works"))}</strong><div class="work-metadata-sample">${sample}${works.length > 6 ? `<span>+${works.length - 6}</span>` : ""}</div><small>${esc(tr("works.metadata_fields_help", "Proposals can include source type, container/journal, volume/issue/pages, publisher, year, edition, translator/editor, ISBN/DOI, language, MLA citation, and cover image."))}</small></div></section>
    <section class="workflow-section"><div class="workflow-section-copy"><b>${esc(tr("works.provider_profile", "Provider profile"))}</b><span>${esc(tr("works.provider_profile_help", "Uses the same configured provider profiles as RAG, PDF tools, and LLM review."))}</span></div><div class="workflow-provider-area">${workflowProviderSelectHtml(selectedId)}<button type="button" class="btn small" id="manageWorkProviders">${esc(tr("language.manage_providers", "Manage provider profiles"))}</button></div></section>
    <section class="workflow-review-strip"><span class="workflow-summary-icon">${icon("history")}</span><span><b>${esc(tr("works.background_operation", "Background operation"))}</b><small>${esc(tr("works.background_operation_help", "You can leave the Works page. Open the completed operation to review and apply proposed changes."))}</small></span><span><b>${esc(tr("works.catalog_source", "Catalogue source"))}</b><small>${esc(tr("works.catalog_source_names", "Open Library · Google Books · Crossref"))}</small></span></section></div>
    <div class="workflow-actions"><button class="btn" data-close>${esc(tr("ui.cancel", "Cancel"))}</button><button class="btn primary" id="startWorkMetadata" ${profiles.length ? "" : `disabled data-disabled-reason="${esc(tr("works.no_provider_profiles_help", "Create an LLM provider profile before populating work metadata."))}"`}>${icon("spark")}${esc(tr("works.start_metadata_lookup", "Start background lookup"))}</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    decorateDisabledControls(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    dialog.querySelector("#workMetadataProvider")?.addEventListener("change", (event: Any) => {
      const profile = providerProfile(event.target.value);
      const summary = dialog.querySelector("#workMetadataProviderSummary");
      if (summary) summary.innerHTML = workflowProviderSummaryHtml(profile);
    });
    dialog.querySelector("#manageWorkProviders")?.addEventListener("click", async () => {
      const ok = await openMessageModal({
        title: tr("works.leave_metadata_title", "Open provider profiles?"),
        message: tr(
          "works.leave_metadata_help",
          "This will close the metadata workflow and navigate to LLM Providers. Your lookup has not started yet.",
        ),
        confirmLabel: tr("works.open_providers", "Open providers"),
        cancelLabel: tr("ui.cancel", "Cancel"),
      });
      if (!ok) return;
      close();
      navigateTo("providers");
    });
    dialog.querySelector("#startWorkMetadata")?.addEventListener("click", async () => {
      const profileId = dialog.querySelector("#workMetadataProvider")?.value || selectedId;
      const profile = providerProfile(profileId);
      if (!profile) return toast(tr("works.provider_required", "Select an LLM provider profile."));
      const config = providerRequestConfig(profile, { textReview: false });
      if (!config?.model)
        return toast(
          tr(
            "works.provider_model_required",
            "The selected provider profile does not have a model configured.",
          ),
        );
      const payload = works.map((item: Any) => ({
        work: item.work,
        current_metadata: representativeWorkMetadata(item.rows),
      }));
      const button = dialog.querySelector("#startWorkMetadata");
      button.disabled = true;
      button.textContent = tr("works.starting_metadata_lookup", "Starting…");
      try {
        const job = await api("/api/jobs/llm-tool", {
          method: "POST",
          body: JSON.stringify({
            task: "work_metadata",
            label:
              works.length === 1
                ? `${tr("works.populate_metadata_llm", "Populate metadata with LLM")} · ${works[0].work}`
                : trf("works.populate_all_metadata_label", "Populate metadata · {count} works", {
                    count: works.length,
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
        close();
        toast(
          trf("works.metadata_lookup_started", "Metadata lookup started for {count} work(s).", {
            count: works.length,
          }),
        );
        if (state.view === "home")
          window.dispatchEvent(new CustomEvent("derridai:dashboard-refresh"));
      } catch (error: Any) {
        button.disabled = false;
        button.innerHTML = `${icon("spark")}${esc(tr("works.start_metadata_lookup", "Start background lookup"))}`;
        openMessageModal({
          title: tr("works.metadata_lookup_failed", "Could not start metadata lookup"),
          message: error.message || String(error),
          tone: "danger",
        });
      }
    });
  }
  function openWorkMetadataProposalResult(job: Any) {
    const proposals = Array.isArray(job.result?.proposals) ? job.result.proposals : [];
    const map = workIndex();
    const flattened: Any[] = [];
    for (const proposal of proposals) {
      const item = map.get(String(proposal.work || ""));
      if (!item) continue;
      const current = representativeWorkMetadata(item.rows);
      for (const [field, proposed] of Object.entries(proposal.changes || {}))
        flattened.push({
          proposal,
          item,
          field,
          current: current[field],
          proposed,
          rationale: proposal.rationale?.[field] || proposal.match_reason || "",
        });
    }
    const dialog = document.createElement("dialog");
    dialog.className = "work-metadata-proposal-dialog";
    const errors = proposals.filter(
      (item: Any) => item.error || (item.message && !Object.keys(item.changes || {}).length),
    );
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(tr("works.review_metadata_proposals", "Review work metadata proposals"))}</h2><div class="dialog-subtitle">${esc(jobLabel(job))} · ${flattened.length.toLocaleString()} ${esc(tr("works.proposed_field_changes", "proposed field changes"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db work-proposal-body">${errors.length ? `<div class="info warn">${esc(trf("works.metadata_no_match_count", "{count} work(s) had no usable catalogue match or returned an error.", { count: errors.length }))}</div>` : ""}<div class="work-proposal-toolbar"><button class="btn small" id="selectAllWorkProposals">${esc(tr("ui.select_all", "Select all"))}</button><button class="btn small" id="clearWorkProposals">${esc(tr("ui.clear", "Clear"))}</button><span class="note">${esc(tr("works.proposal_edit_help", "Edit proposed values if needed, then apply selected fields across every loaded record belonging to that work."))}</span></div>${flattened.length ? `<div class="work-proposal-table-wrap"><table class="work-proposal-table"><thead><tr><th></th><th>${esc(tr("nav.works", "Work"))}</th><th>${esc(tr("works.field", "Field"))}</th><th>${esc(tr("works.current_value", "Current"))}</th><th>${esc(tr("works.proposed_value", "Proposed"))}</th><th>${esc(tr("works.source_reason", "Source / reason"))}</th></tr></thead><tbody>${flattened.map((entry, index) => `<tr><td><input type="checkbox" data-work-proposal-select="${index}" checked></td><td><b>${esc(entry.item.work)}</b><small>${entry.item.count.toLocaleString()} ${esc(tr("dynamic.records", "records"))}</small></td><td>${esc(label(entry.field))}</td><td><div class="proposal-current">${esc(display(entry.current))}</div></td><td><textarea class="control proposal-value" data-work-proposal-value="${index}" rows="2">${esc(entry.proposed == null ? "" : typeof entry.proposed === "object" ? JSON.stringify(entry.proposed) : String(entry.proposed))}</textarea></td><td><small>${esc(entry.rationale || tr("works.catalogue_selected", "Public bibliographic catalogue match selected by the LLM."))}</small>${entry.proposal.confidence != null ? `<span class="proposal-confidence">${Math.round(Number(entry.proposal.confidence || 0) * 100)}%</span>` : ""}</td></tr>`).join("")}</tbody></table></div>` : `<div class="llm-empty">${esc(tr("works.no_metadata_changes", "No metadata changes were proposed."))}</div>`}${errors.length ? `<details class="work-proposal-errors"><summary>${esc(tr("works.unmatched_works", "Unmatched / failed works"))}</summary>${errors.map((item: Any) => `<div><b>${esc(item.work)}</b><span>${esc(item.error || item.message || tr("works.no_catalogue_match", "No catalogue match"))}</span></div>`).join("")}</details>` : ""}</div><div class="da"><button class="btn" data-close>${esc(tr("ui.close", "Close"))}</button><button class="btn primary" id="applyWorkProposals" ${flattened.length ? "" : "disabled"}>${icon("check")}${esc(tr("works.apply_selected_metadata", "Apply selected metadata"))}</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    decorateDisabledControls(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    dialog
      .querySelector("#selectAllWorkProposals")
      ?.addEventListener("click", () =>
        dialog
          .querySelectorAll("[data-work-proposal-select]")
          .forEach((box: Any) => (box.checked = true)),
      );
    dialog
      .querySelector("#clearWorkProposals")
      ?.addEventListener("click", () =>
        dialog
          .querySelectorAll("[data-work-proposal-select]")
          .forEach((box: Any) => (box.checked = false)),
      );
    dialog.querySelector("#applyWorkProposals")?.addEventListener("click", async () => {
      const selected = [...dialog.querySelectorAll("[data-work-proposal-select]:checked")]
        .map((box) => Number(box.dataset.workProposalSelect))
        .filter((index) => flattened[index]);
      if (!selected.length)
        return toast(
          tr("works.select_metadata_changes", "Select at least one proposed metadata change."),
        );
      const grouped = new Map();
      try {
        for (const index of selected) {
          const entry = flattened[index];
          const control = dialog.querySelector(`[data-work-proposal-value="${index}"]`);
          const value = parseProposedMetadataValue(control.value, entry.proposed);
          if (!grouped.has(entry.item.work))
            grouped.set(entry.item.work, { item: entry.item, changes: {}, rationale: {} });
          const group = grouped.get(entry.item.work);
          group.changes[entry.field] = value;
          group.rationale[entry.field] = entry.rationale;
        }
      } catch (error: Any) {
        return toast(error.message);
      }
      const _recordCount = [...grouped.values()].reduce(
        (sum, group) => sum + group.item.rows.length,
        0,
      );
      const applyButton = dialog.querySelector("#applyWorkProposals");
      if (applyButton) {
        applyButton.disabled = true;
        applyButton.textContent = tr("works.applying_metadata", "Applying metadata…");
      }
      const batchId = uid();
      let changedRecords = 0,
        fieldChanges = 0;
      const touchedFiles = new Set();
      try {
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
        close();
        shell();
        renderView();
        toast(
          trf(
            "works.metadata_applied",
            "Updated {records} records · {fields} tracked field changes",
            { records: changedRecords.toLocaleString(), fields: fieldChanges.toLocaleString() },
          ),
          { tone: "success" },
        );
      } catch (error: Any) {
        if (applyButton) {
          applyButton.disabled = false;
          applyButton.textContent = tr("works.apply_selected_metadata", "Apply selected metadata");
        }
        toast(error.message || String(error), { tone: "danger" });
      }
    });
  }
  async function openRemoveWorkModal(work: Any, rows: Any) {
    const fileCounts = new Map();
    for (const row of rows) fileCounts.set(row.file, (fileCounts.get(row.file) || 0) + 1);
    const dialog = document.createElement("dialog");
    dialog.className = "message-dialog danger remove-work-dialog";
    const dbStore =
      state.activeStore && recordStores().some((store: Any) => store.name === state.activeStore)
        ? state.activeStore
        : "";
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(tr("works.remove_entire", "Remove entire work"))}</h2><div class="dialog-subtitle">${esc(work)} · ${esc(tr("works.destructive_operation", "destructive operation"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db remove-work-body"><div class="info warn">${esc(tr("works.remove_help", "Remove every record for this work from selected loaded JSONL files and, optionally, from the selected Chroma collection. Primary collection deletion also removes matching records from its language collections."))}</div>
    <div class="remove-work-files">${[...fileCounts].map(([file, count]) => `<label class="check-item"><input type="checkbox" data-remove-work-file="${esc(file.id)}" checked><span><b>${esc(file.name)}</b><small>${esc(trf("works.matching_records", "{count} matching record(s)", { count: count.toLocaleString() }))}</small></span></label>`).join("")}</div>
    <label class="check-item"><input type="checkbox" id="removeWorkDb" ${dbStore ? "" : `disabled data-disabled-reason="${esc(tr("works.select_or_create_db", "Select or create a corpus vector database first."))}" title="${esc(tr("works.select_or_create_db", "Select or create a corpus vector database first."))}"`}><span><b>${esc(tr("works.also_remove_chroma", "Also remove from Chroma"))}</b><small>${dbStore ? esc(dbStore) : esc(tr("works.select_collection", "Select a corpus collection first."))}</small></span></label></div>
    <div class="da"><button class="btn" data-close>${esc(tr("ui.cancel", "Cancel"))}</button><button class="btn danger" id="confirmRemoveWork">${esc(tr("works.remove_work", "Remove work"))}</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    dialog.querySelector("#confirmRemoveWork").onclick = async () => {
      const fileIds = [...dialog.querySelectorAll("[data-remove-work-file]:checked")].map(
        (input) => input.dataset.removeWorkFile,
      );
      const removeDb = Boolean(dialog.querySelector("#removeWorkDb")?.checked && dbStore);
      if (!fileIds.length && !removeDb)
        return toast(
          tr("works.select_file_or_chroma", "Select at least one JSONL file or the Chroma collection"),
        );
      const button = dialog.querySelector("#confirmRemoveWork");
      button.disabled = true;
      button.textContent = tr("works.removing", "Removing…");
      let localDeleted = 0,
        dbDeleted = 0,
        mirrored = 0;
      try {
        for (const fileId of fileIds) {
          const file = state.files.find((item: Any) => item.id === fileId);
          if (!file) continue;
          const before = file.records.length;
          file.records = file.records.filter(
            (record: Any) => String(record.work || tr("works.untitled", "Untitled work")) !== work,
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
        close();
        persistPrefs();
        shell();
        renderView();
        toast(
          trf(
            "works.removed_summary",
            "Removed “{work}” · {local} local record(s){db}",
            {
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
            },
          ),
        );
      } catch (error: Any) {
        button.disabled = false;
        button.textContent = tr("works.remove_work", "Remove work");
        openMessageModal({
          title: tr("works.remove_failed", "Could not remove work"),
          message: error.message,
          tone: "danger",
        });
      }
    };
  }
  async function openSeparateWorksModal() {
    const eligible = state.files.filter((file: Any) => {
      const works = new Set(
        file.records
          .map((record: Any) => String(record?.work || record?.document_title || "").trim())
          .filter(Boolean),
      );
      return works.size > 1;
    });
    if (!eligible.length)
      return toast(tr("works.no_multi_work_jsonl", "No loaded JSONL file contains multiple named works"));
    const dialog = document.createElement("dialog");
    dialog.className = "work-separate-dialog";
    const options = eligible
      .map(
        (file: Any) =>
          `<option value="${esc(file.id)}">${esc(file.name)} · ${file.records.length.toLocaleString()} ${esc(tr("dynamic.records", "records"))}</option>`,
      )
      .join("");
    dialog.innerHTML = `<div class="dh"><div><span class="section-label">${esc(tr("works.jsonl_organization", "JSONL organization"))}</span><h2 class="dialog-title">${esc(tr("works.separate_works_title", "Separate works from a JSONL file"))}</h2><div class="dialog-subtitle">${esc(tr("works.separate_works_help", "Create one derived JSONL tab per selected work while preserving record metadata and audit history."))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db separate-works-body"><div class="field"><label>${esc(tr("works.source_jsonl", "Source JSONL"))}</label><select class="control" id="separateWorksSource">${options}</select></div><div id="separateWorksList" class="separate-works-list"></div><label class="check-item"><input type="checkbox" id="separateWorksRemove"><span>${esc(tr("works.remove_separated", "Remove separated records from the source tab after creating the new tabs"))}</span></label><div class="info">${esc(tr("works.separate_nondestructive_help", "By default this is non-destructive: new tabs are created as copies. Enable removal only when you want to partition the original loaded JSONL."))}</div></div><div class="da"><button class="btn" data-close>${esc(tr("ui.cancel", "Cancel"))}</button><button class="btn primary" id="separateWorksCreate">${esc(tr("works.separate_selected", "Separate selected works"))}</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    const source = () =>
      state.files.find(
        (file: Any) => file.id === dialog.querySelector("#separateWorksSource").value,
      );
    const renderList = () => {
      const file = source();
      const groups = new Map();
      for (const record of file?.records || []) {
        const work =
          String(record?.work || record?.document_title || "").trim() || tr("works.untitled", "Untitled work");
        if (!groups.has(work)) groups.set(work, []);
        groups.get(work).push(record);
      }
      dialog.querySelector("#separateWorksList").innerHTML = [...groups.entries()]
        .map(
          ([work, records]) =>
            `<label class="separate-work-row"><input type="checkbox" data-separate-work="${esc(work)}" ${work === tr("works.untitled", "Untitled work") ? "" : "checked"}><span><b>${esc(work)}</b><small>${records.length.toLocaleString()} ${esc(tr("dynamic.records", "records"))}</small></span></label>`,
        )
        .join("");
    };
    dialog.querySelector("#separateWorksSource").addEventListener("change", renderList);
    renderList();
    dialog.querySelector("#separateWorksCreate").onclick = async () => {
      const file = source();
      const selected = [...dialog.querySelectorAll("[data-separate-work]:checked")].map(
        (box) => box.dataset.separateWork,
      );
      if (!selected.length) return toast(tr("works.select_at_least_one", "Select at least one work"));
      const selectedSet = new Set(selected);
      const created = [];
      for (const work of selected) {
        const records = file.records
          .filter(
            (record: Any) =>
              (String(record?.work || record?.document_title || "").trim() ||
                tr("works.untitled", "Untitled work")) ===
              work,
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
      if (dialog.querySelector("#separateWorksRemove").checked) {
        file.records = file.records.filter(
          (record: Any) =>
            !selectedSet.has(
              String(record?.work || record?.document_title || "").trim() ||
              tr("works.untitled", "Untitled work"),
            ),
        );
        file.dirty = new Set(file.records.map((_: Any, index: Any) => index));
        await persistFileNow(file);
      }
      if (created.length) state.activeFileId = created[0].id;
      close();
      corpusCache.fields = null;
      persistPrefs();
      shell();
      renderView();
      toast(trf("works.created_tabs", "Created {count} work JSONL tab(s)", { count: created.length }), {
        tone: "success",
      });
    };
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
