/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

// The dialogs for editing, merging, subsetting and cleaning records and for the upsert queue, drawn as HTML strings. Moved
// verbatim from the legacy runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "activeFile"
  | "allRows"
  | "api"
  | "applyRecordChanges"
  | "bulkEditRowsForScope"
  | "cleanRows"
  | "clearRecordUpdates"
  | "cloneAuditValue"
  | "dbUnavailableReason"
  | "decorateDisabledControls"
  | "download"
  | "downloadBlob"
  | "fieldEditor"
  | "fileJsonl"
  | "formatTimestamp"
  | "hasCorpusDb"
  | "historyVersionChanges"
  | "idbDelete"
  | "jsonPretty"
  | "label"
  | "loadSubsetProfiles"
  | "localRecordKey"
  | "navigateTo"
  | "needsReviewItems"
  | "openMessageModal"
  | "parseBulkFieldValue"
  | "parseEditor"
  | "pendingChangesForRow"
  | "pendingUpsertRows"
  | "persistFileNow"
  | "persistPrefs"
  | "recordDbStatus"
  | "recordFields"
  | "recordHistoryVersions"
  | "refreshPresenceForRows"
  | "removeFromUpsertQueue"
  | "renderView"
  | "restoreRecordHistoryVersion"
  | "sameValue"
  | "saveSubsetProfiles"
  | "selectedIndex"
  | "selectedRecord"
  | "selectedReviewItems"
  | "shell"
  | "showAppModal"
  | "subsetRuleMatches"
  | "toast"
  | "tr"
  | "trf"
  | "uid"
  | "upsertRows";
type Deps = { state: Loose; fileTimers: Map<string, ReturnType<typeof setTimeout>> } & Record<
  Helper,
  Fn
>;

/** The groups of fields the record editor shows, in order. */
const EDITOR_GROUPS = [
  {
    name: "Source",
    fields: [
      "record_id",
      "work",
      "document_author",
      "edition",
      "year",
      "page_start",
      "page_end",
      "region_type",
      "region_author",
      "primary_text",
      "canonical_work_id",
      "pdf_file",
      "pdf_pages",
    ],
  },
  {
    name: "Discourse",
    fields: [
      "speaker",
      "position_holder",
      "target",
      "discourse_role",
      "proposition_status",
      "semantic_function",
      "stance",
      "claim_scope",
    ],
  },
  {
    name: "Quotation provenance",
    fields: [
      "is_direct_quote",
      "quoted_speaker",
      "quoted_author",
      "quoted_work",
      "quoted_position_holder",
      "quoted_addressee",
      "quoted_referent",
      "quotation_chain",
    ],
  },
  { name: "Indexing", fields: ["topics", "concepts", "persons", "works_referenced"] },
  {
    name: "Quality / review",
    fields: [
      "attribution_confidence",
      "semantic_classification_confidence",
      "extraction_quality",
      "needs_review",
      "review_reason",
    ],
  },
  {
    name: "Language / translation",
    fields: ["document_language", "original_language", "document_is_translation", "translator"],
  },
  { name: "Citation", fields: ["inline_citation", "full_citation"] },
  { name: "Text", fields: ["text", "text_length"] },
];

export function createRecordDialogs(deps: Deps) {
  const {
    state,
    activeFile,
    allRows,
    api,
    applyRecordChanges,
    bulkEditRowsForScope,
    cleanRows,
    clearRecordUpdates,
    cloneAuditValue,
    dbUnavailableReason,
    decorateDisabledControls,
    download,
    downloadBlob,
    fieldEditor,
    fileJsonl,
    fileTimers,
    formatTimestamp,
    hasCorpusDb,
    historyVersionChanges,
    idbDelete,
    jsonPretty,
    label,
    loadSubsetProfiles,
    localRecordKey,
    navigateTo,
    needsReviewItems,
    openMessageModal,
    parseBulkFieldValue,
    parseEditor,
    pendingChangesForRow,
    pendingUpsertRows,
    persistFileNow,
    persistPrefs,
    recordDbStatus,
    recordFields,
    recordHistoryVersions,
    refreshPresenceForRows,
    removeFromUpsertQueue,
    renderView,
    restoreRecordHistoryVersion,
    sameValue,
    saveSubsetProfiles,
    selectedIndex,
    selectedRecord,
    selectedReviewItems,
    shell,
    showAppModal,
    subsetRuleMatches,
    toast,
    tr,
    trf,
    uid,
    upsertRows,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  function openMergeDialog() {
    if (state.files.length < 2) return toast("Open at least two JSONL files to merge");
    const dialog = document.createElement("dialog");
    dialog.className = "merge-dialog";
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">Merge JSONL tabs</h2><div class="dialog-subtitle">Choose any subset. The selected source tabs will be replaced in the workspace by the merged tab.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db"><div class="merge-actions"><button class="btn small" id="mergeSelectAll">Select all</button><button class="btn small" id="mergeSelectNone">Clear</button></div><div class="merge-file-list">${state.files.map((file: Any) => `<label class="merge-file-item"><input type="checkbox" data-merge-file="${file.id}" checked><span><b>${esc(file.name)}</b><small>${file.records.length.toLocaleString()} records</small></span></label>`).join("")}</div><div class="field"><label>Merged file name</label><input class="control" id="mergeName" value="derridai-merged.jsonl"></div><label class="check-item"><input type="checkbox" id="mergeDownload"><span>Download merged JSONL immediately</span></label><div class="info">Unselected tabs remain unchanged. Selected tabs are removed from the workspace after the merge is created; their underlying source files on disk are not deleted.</div></div><div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="mergeCreate">Merge and replace selected tabs</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((x: Any) => (x.onclick = close));
    dialog.querySelector("#mergeSelectAll").onclick = () =>
      dialog.querySelectorAll("[data-merge-file]").forEach((x: Any) => (x.checked = true));
    dialog.querySelector("#mergeSelectNone").onclick = () =>
      dialog.querySelectorAll("[data-merge-file]").forEach((x: Any) => (x.checked = false));
    dialog.querySelector("#mergeCreate").onclick = async () => {
      const ids = [...dialog.querySelectorAll("[data-merge-file]:checked")].map(
        (x) => x.dataset.mergeFile,
      );
      const files = state.files.filter((file: Any) => ids.includes(file.id));
      if (!files.length) return toast("Select at least one file");
      const firstIndex = Math.min(...files.map((file: Any) => state.files.indexOf(file)));
      const name = (
        dialog.querySelector("#mergeName").value.trim() || "derridai-merged.jsonl"
      ).replace(/\s+/g, "-");
      const records = files.flatMap((file: Any) =>
        file.records.map((record: Any) => cloneAuditValue(record)),
      );
      const merged = {
        id: uid(),
        name: name.endsWith(".jsonl") ? name : `${name}.jsonl`,
        records,
        errors: files.flatMap((file: Any) => file.errors || []),
        dirty: new Set(records.map((_: Any, index: Any) => index)),
        imported_at: new Date().toISOString(),
        merged_from: files.map((file: Any) => file.name),
      };

      const removedIds = new Set<Any>(files.map((file: Any) => file.id));
      state.files = state.files.filter((file: Any) => !removedIds.has(file.id));
      state.files.splice(firstIndex, 0, merged);

      for (const id of removedIds) {
        delete state.selected[id];
        delete state.searches[id];
        delete state.pages[id];
        delete state.sorts[id];
        if (fileTimers.has(id)) {
          clearTimeout(fileTimers.get(id));
          fileTimers.delete(id);
        }
        await idbDelete("files", id).catch((error: Any) =>
          console.error("Could not remove merged source tab from IndexedDB", error),
        );
      }
      state.reviewSelection = new Set(
        [...state.reviewSelection].filter((key) => !removedIds.has(String(key).split("::")[0])),
      );
      for (const store of Object.keys(state.upsertState || {})) {
        for (const key of Object.keys(state.upsertState[store] || {})) {
          if (removedIds.has(String(key).split("::")[0])) delete state.upsertState[store][key];
        }
      }
      for (const store of Object.keys(state.upsertIgnored || {})) {
        for (const key of Object.keys(state.upsertIgnored[store] || {})) {
          if (removedIds.has(String(key).split("::")[0])) delete state.upsertIgnored[store][key];
        }
      }
      for (const bucket of [state.storePresence, state.storePresenceIds]) {
        for (const store of Object.keys(bucket || {})) {
          for (const key of Object.keys(bucket[store] || {})) {
            if (removedIds.has(String(key).split("::")[0])) delete bucket[store][key];
          }
        }
      }

      await persistFileNow(merged);
      state.activeFileId = merged.id;
      if (dialog.querySelector("#mergeDownload").checked) download(merged.name, fileJsonl(merged));
      persistPrefs();
      close();
      navigateTo("list", { fileId: merged.id });
      toast(
        `Merged and replaced ${files.length} tabs · ${records.length.toLocaleString()} records`,
      );
    };
  }
  function openSubsetBuilder() {
    if (!state.files.length) return toast("Load one or more JSONL files first");
    const dialog = document.createElement("dialog");
    dialog.className = "subset-dialog";
    const fields = recordFields().filter((field: Any) => !field.startsWith("_"));
    const sourceOptions = [
      `<option value="active">Active JSONL · ${esc(activeFile()?.name || "")}</option>`,
      `<option value="all">All loaded JSONL files</option>`,
      ...state.files.map(
        (file: Any) =>
          `<option value="${esc(file.id)}">Only ${esc(file.name)} · ${file.records.length.toLocaleString()} records</option>`,
      ),
    ].join("");
    const fieldOptions = fields
      .map(
        (field: Any) =>
          `<option value="${esc(field)}">${esc(label(field))} · ${esc(field)}</option>`,
      )
      .join("");
    const operatorOptions = [
      ["equals", "Equals"],
      ["not_equals", "Does not equal"],
      ["contains", "Contains"],
      ["not_contains", "Does not contain"],
      ["array_contains", "Array contains exact value"],
      ["exists", "Exists / non-empty"],
      ["missing", "Missing / empty"],
      ["truthy", "Truthy"],
      ["falsy", "Falsy"],
      ["regex", "Regular expression"],
    ]
      .map(([value, name]) => `<option value="${value}">${name}</option>`)
      .join("");
    const profiles = loadSubsetProfiles();
    dialog.innerHTML = `<div class="dh subset-dialog-head"><div><span class="section-label">Corpus utility</span><h2 class="dialog-title">Create JSONL subset</h2><div class="dialog-subtitle">Build reusable record filters without editing the source JSONL.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db subset-body subset-body-v3">
    <section class="subset-config-card"><div class="subset-config-copy"><b>Source & output</b><span>Choose the loaded records to filter and the name of the derived JSONL tab.</span></div><div class="subset-head-grid"><div class="field"><label>Source</label><select class="control" id="subsetSource">${sourceOptions}</select></div><div class="field"><label>New JSONL tab name</label><input class="control" id="subsetName" value="${esc((activeFile()?.name || "subset.jsonl").replace(/\.jsonl$/i, ""))}-subset.jsonl"></div><label class="check-item subset-case"><input type="checkbox" id="subsetCase"><span>Case-sensitive matching</span></label></div></section>
    <section class="subset-config-card"><div class="subset-config-copy"><b>Saved filter profile</b><span>Reuse common corpus slices such as primary Derrida text, one language, or records needing review.</span></div><div class="subset-profile-row"><select class="control" id="subsetProfile"><option value="">No saved profile</option>${profiles.map((profile: Any) => `<option value="${esc(profile.id)}">${esc(profile.name)}</option>`).join("")}</select><button class="btn small" id="saveSubsetProfile">${icon("plus")}Save current</button><button class="btn small danger" id="deleteSubsetProfile" disabled>Delete</button></div></section>
    <section class="subset-config-card subset-filter-card"><div class="subset-config-copy"><b>Filter expression</b><span>Conditions are readable, grouped explicitly, and previewed against the selected source as you edit.</span></div><div class="subset-expression" id="subsetExpression"></div><div class="subset-builder-actions"><button class="btn small" id="addSubsetRule">${icon("plus")}Condition</button><button class="btn small" id="addSubsetGroup">${icon("plus")}Group</button><span class="subset-match-count" id="subsetPreview">Add at least one condition.</span></div><div class="subset-expression-preview" id="subsetExpressionPreview"></div></section>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn" id="createSubsetDownload">Create & download</button><button class="btn primary" id="createSubset">Create subset tab</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    const expression = dialog.querySelector("#subsetExpression");
    let previewTimer: Any = null;
    const schedulePreview = () => {
      clearTimeout(previewTimer);
      previewTimer = setTimeout(updatePreview, 120);
    };

    const subsetAutocompleteExcluded = new Set([
      "text",
      "extracted_text",
      "extractedText",
      "raw_text",
      "ocr_text",
    ]);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- moved verbatim; the row markup ignores these defaults
    function ruleHtml({ field = "work", operator = "equals", value = "" } = {}) {
      return `<div class="subset-rule-core"><select class="control subset-field">${fieldOptions}</select><select class="control subset-operator">${operatorOptions}</select><input class="control subset-value" placeholder="${esc(tr("subset.value", "Value"))}" autocomplete="off"><datalist class="subset-value-options"></datalist><button class="btn icon-only danger subset-remove" type="button" title="${esc(tr("subset.remove_condition", "Remove condition"))}" aria-label="${esc(tr("subset.remove_condition", "Remove condition"))}">${icon("close")}</button></div>`;
    }
    function initializeRule(row: Any, { field = "work", operator = "equals", value = "" } = {}) {
      row.querySelector(".subset-field").value = fields.includes(field) ? field : fields[0] || "";
      row.querySelector(".subset-operator").value = operator;
      row.querySelector(".subset-value").value = value;
      const input = row.querySelector(".subset-value"),
        datalist = row.querySelector(".subset-value-options");
      const listId = `subset-values-${uid()}`;
      datalist.id = listId;
      const syncSuggestions = () => {
        const fieldName = row.querySelector(".subset-field").value;
        if (subsetAutocompleteExcluded.has(fieldName)) {
          input.removeAttribute("list");
          datalist.innerHTML = "";
          input.title = tr(
            "subset.autocomplete_large_field",
            "Autocomplete is disabled for large text fields.",
          );
          return;
        }
        const values = new Set<Any>();
        for (const { record } of selectedRows()) {
          const raw = record?.[fieldName];
          const items = Array.isArray(raw) ? raw : [raw];
          for (const item of items) {
            if (item === null || item === undefined || typeof item === "object") continue;
            const text = String(item).trim();
            if (text) values.add(text);
          }
        }
        const ordered = [...values].sort((a, b) =>
          a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }),
        );
        datalist.innerHTML = ordered
          .map((option) => `<option value="${esc(option)}"></option>`)
          .join("");
        if (ordered.length) {
          input.setAttribute("list", listId);
          input.title = trf(
            "subset.autocomplete_count",
            "{count} unique values from the selected JSONL source.",
            { count: ordered.length.toLocaleString() },
          );
        } else {
          input.removeAttribute("list");
          input.title = "";
        }
      };
      const syncValue = () => {
        const noValue = ["exists", "missing", "truthy", "falsy"].includes(
          row.querySelector(".subset-operator").value,
        );
        input.disabled = noValue;
        input.placeholder = noValue
          ? tr("subset.no_value", "No value required")
          : tr("subset.value", "Value");
        if (noValue) input.value = "";
        if (noValue) input.removeAttribute("list");
        else syncSuggestions();
      };
      row.querySelectorAll("select,input").forEach((control: Any) =>
        control.addEventListener("input", () => {
          syncValue();
          schedulePreview();
        }),
      );
      row.querySelector(".subset-remove").onclick = () => {
        const group = row.closest(".subset-group");
        row.remove();
        if (group && !group.querySelector(".subset-group-rules .subset-rule-row")) group.remove();
        normalizeTopJoins();
        updatePreview();
      };
      syncValue();
    }
    function topJoinHtml() {
      return `<select class="control subset-join"><option value="AND">AND</option><option value="OR">OR</option></select>`;
    }
    function addTopRule(config = {}) {
      const item = document.createElement("div");
      item.className = "subset-expression-item subset-top-rule";
      item.dataset.kind = "rule";
      item.innerHTML = `${topJoinHtml()}<div class="subset-rule-row">${ruleHtml(config)}</div>`;
      expression.appendChild(item);
      initializeRule(item.querySelector(".subset-rule-row"), config);
      item.querySelector(".subset-join").addEventListener("change", schedulePreview);
      normalizeTopJoins();
      updatePreview();
    }
    function addGroup({ mode = "OR", rules = null }: Any = {}) {
      const item = document.createElement("div");
      item.className = "subset-expression-item subset-group";
      item.dataset.kind = "group";
      item.innerHTML = `${topJoinHtml()}<div class="subset-group-box"><div class="subset-group-head"><div><b>Grouped conditions</b><span>Parentheses: evaluate this block as one boolean value</span></div><div class="tools"><select class="control subset-group-mode"><option value="OR">Match ANY (OR)</option><option value="AND">Match ALL (AND)</option></select><button class="btn tiny" type="button" data-add-group-rule>${icon("plus")}Condition</button><button class="btn tiny danger" type="button" data-remove-group>Remove group</button></div></div><div class="subset-group-rules"></div></div>`;
      expression.appendChild(item);
      item.querySelector(".subset-group-mode").value = mode;
      const list = item.querySelector(".subset-group-rules");
      const addInner = (config = {}) => {
        const row = document.createElement("div");
        row.className = "subset-rule-row";
        row.innerHTML = ruleHtml(config);
        list.appendChild(row);
        initializeRule(row, config);
        updatePreview();
      };
      (rules?.length
        ? rules
        : [
            { field: "topics", operator: "array_contains", value: "" },
            { field: "concepts", operator: "array_contains", value: "" },
          ]
      ).forEach(addInner);
      item.querySelector("[data-add-group-rule]").onclick = () =>
        addInner({
          field: fields.includes("topics") ? "topics" : fields[0],
          operator: "contains",
          value: "",
        });
      item.querySelector("[data-remove-group]").onclick = () => {
        item.remove();
        normalizeTopJoins();
        updatePreview();
      };
      item.querySelector(".subset-group-mode").addEventListener("change", schedulePreview);
      item.querySelector(".subset-join").addEventListener("change", schedulePreview);
      normalizeTopJoins();
      updatePreview();
    }
    function normalizeTopJoins() {
      [...expression.querySelectorAll(":scope > .subset-expression-item")].forEach(
        (item, index) => {
          const join = item.querySelector(":scope > .subset-join");
          join.disabled = index === 0;
          if (index === 0) join.value = "AND";
        },
      );
    }
    function selectedRows() {
      const source = dialog.querySelector("#subsetSource").value;
      if (source === "all") return allRows();
      if (source === "active") {
        const file = activeFile();
        return file ? file.records.map((record: Any, index: Any) => ({ file, record, index })) : [];
      }
      const file = state.files.find((item: Any) => item.id === source);
      return file ? file.records.map((record: Any, index: Any) => ({ file, record, index })) : [];
    }
    function readRule(row: Any) {
      return {
        field: row.querySelector(".subset-field").value,
        operator: row.querySelector(".subset-operator").value,
        value: row.querySelector(".subset-value").value,
      };
    }
    function readExpression() {
      return [...expression.querySelectorAll(":scope > .subset-expression-item")].map(
        (item, index) => {
          const base = {
            join: index === 0 ? "AND" : item.querySelector(":scope > .subset-join").value,
            type: item.dataset.kind,
          };
          if (item.dataset.kind === "group")
            return {
              ...base,
              mode: item.querySelector(".subset-group-mode").value,
              rules: [...item.querySelectorAll(".subset-group-rules .subset-rule-row")].map(
                readRule,
              ),
            };
          return { ...base, rule: readRule(item.querySelector(".subset-rule-row")) };
        },
      );
    }
    function itemMatches(record: Any, item: Any, caseSensitive: Any) {
      if (item.type === "group") {
        const values = item.rules.map((rule: Any) =>
          subsetRuleMatches(record, rule, caseSensitive),
        );
        return item.mode === "AND" ? values.every(Boolean) : values.some(Boolean);
      }
      return subsetRuleMatches(record, item.rule, caseSensitive);
    }
    function recordMatchesExpression(record: Any, items: Any, caseSensitive: Any) {
      if (!items.length) return false;
      const groups = [];
      let group = [];
      for (const item of items) {
        if (item.join === "OR" && group.length) {
          groups.push(group);
          group = [];
        }
        group.push(item);
      }
      if (group.length) groups.push(group);
      return groups.some((itemsInAndGroup) =>
        itemsInAndGroup.every((item) => itemMatches(record, item, caseSensitive)),
      );
    }
    function expressionText(items: Any) {
      const oneRule = (rule: Any) =>
        `${label(rule.field)} ${dialog.querySelector(`.subset-operator option[value="${CSS.escape(rule.operator)}"]`)?.textContent || rule.operator}${["exists", "missing", "truthy", "falsy"].includes(rule.operator) ? "" : ` “${rule.value}”`}`;
      return items
        .map((item: Any, index: Any) => {
          const prefix = index ? ` ${item.join} ` : "";
          if (item.type === "group")
            return `${prefix}(${item.rules.map(oneRule).join(` ${item.mode} `)})`;
          return `${prefix}${oneRule(item.rule)}`;
        })
        .join("");
    }
    function matchedRows() {
      const items = readExpression();
      if (!items.length) return [];
      const caseSensitive = dialog.querySelector("#subsetCase").checked;
      return selectedRows().filter(({ record }: Any) =>
        recordMatchesExpression(record, items, caseSensitive),
      );
    }
    function updatePreview() {
      const items = readExpression(),
        sourceCount = selectedRows().length,
        matched = items.length ? matchedRows().length : 0;
      dialog.querySelector("#subsetPreview").textContent = items.length
        ? `${matched.toLocaleString()} of ${sourceCount.toLocaleString()} source records match`
        : "Add at least one condition.";
      dialog.querySelector("#subsetExpressionPreview").innerHTML = items.length
        ? `<b>Expression</b><code>${esc(expressionText(items))}</code>`
        : "";
      decorateDisabledControls(dialog);
    }
    const refreshSubsetSuggestions = () =>
      expression
        .querySelectorAll(".subset-rule-row")
        .forEach((row: Any) =>
          row.querySelector(".subset-field")?.dispatchEvent(new Event("input", { bubbles: false })),
        );
    const applyProfile = (profile: Any) => {
      expression.innerHTML = "";
      for (const item of profile?.expression || []) {
        if (item?.type === "group") {
          addGroup({ mode: item.mode || "OR", rules: item.rules || [] });
          const added = expression.lastElementChild;
          if (added && item.join) added.querySelector(":scope > .subset-join").value = item.join;
        } else if (item?.rule) {
          addTopRule(item.rule);
          const added = expression.lastElementChild;
          if (added && item.join) added.querySelector(":scope > .subset-join").value = item.join;
        }
      }
      dialog.querySelector("#subsetCase").checked = Boolean(profile?.caseSensitive);
      normalizeTopJoins();
      refreshSubsetSuggestions();
      updatePreview();
    };
    const profileSelect = dialog.querySelector("#subsetProfile");
    profileSelect?.addEventListener("change", () => {
      const profile = loadSubsetProfiles().find((item: Any) => item.id === profileSelect.value);
      dialog.querySelector("#deleteSubsetProfile").disabled = !profile;
      if (profile) applyProfile(profile);
    });
    dialog.querySelector("#saveSubsetProfile")?.addEventListener("click", async () => {
      const items = readExpression();
      if (!items.length) return toast("Add at least one condition before saving a profile");
      const name = prompt("Filter profile name");
      if (!name?.trim()) return;
      const profiles = loadSubsetProfiles();
      const profile = {
        id: uid(),
        name: name.trim(),
        expression: items,
        caseSensitive: dialog.querySelector("#subsetCase").checked,
        created_at: new Date().toISOString(),
      };
      profiles.push(profile);
      saveSubsetProfiles(profiles);
      profileSelect.insertAdjacentHTML(
        "beforeend",
        `<option value="${esc(profile.id)}">${esc(profile.name)}</option>`,
      );
      profileSelect.value = profile.id;
      dialog.querySelector("#deleteSubsetProfile").disabled = false;
      toast(`Saved filter profile “${profile.name}”`, { tone: "success" });
    });
    dialog.querySelector("#deleteSubsetProfile")?.addEventListener("click", () => {
      const id = profileSelect.value;
      if (!id) return;
      const profiles = loadSubsetProfiles();
      const profile = profiles.find((item: Any) => item.id === id);
      saveSubsetProfiles(profiles.filter((item: Any) => item.id !== id));
      profileSelect.querySelector(`option[value="${CSS.escape(id)}"]`)?.remove();
      profileSelect.value = "";
      dialog.querySelector("#deleteSubsetProfile").disabled = true;
      if (profile) toast(`Deleted filter profile “${profile.name}”`);
    });
    dialog.querySelector("#addSubsetRule").onclick = () =>
      addTopRule({
        field: fields.includes("work") ? "work" : fields[0],
        operator: "equals",
        value: "",
      });
    dialog.querySelector("#addSubsetGroup").onclick = () => addGroup();
    dialog.querySelector("#subsetSource")?.addEventListener("change", () => {
      refreshSubsetSuggestions();
      schedulePreview();
    });
    dialog.querySelector("#subsetCase")?.addEventListener("change", schedulePreview);
    const createSubset = async (downloadFile: Any) => {
      const items = readExpression();
      const rows = matchedRows();
      if (!items.length) return toast("Add at least one subset condition");
      if (!rows.length) return toast("No records match the subset expression");
      let name = dialog.querySelector("#subsetName").value.trim() || "subset.jsonl";
      if (!name.toLowerCase().endsWith(".jsonl")) name += ".jsonl";
      const file = {
        id: uid(),
        name,
        records: rows.map(({ record }: Any) => cloneAuditValue(record)),
        errors: [],
        dirty: new Set(),
        imported_at: new Date().toISOString(),
        subset: {
          created_at: new Date().toISOString(),
          source: dialog.querySelector("#subsetSource").value,
          logic: "grouped_boolean_v2",
          expression: items,
        },
      };
      state.files.push(file);
      state.activeFileId = file.id;
      await persistFileNow(file);
      if (downloadFile) {
        const blob = new Blob(
          [file.records.map((record: Any) => JSON.stringify(record)).join("\n") + "\n"],
          { type: "application/x-ndjson" },
        );
        downloadBlob(blob, name);
      }
      close();
      navigateTo("list", { fileId: file.id });
      toast(`Created ${name} with ${file.records.length.toLocaleString()} records`);
    };
    dialog.querySelector("#createSubset").onclick = () => createSubset(false);
    dialog.querySelector("#createSubsetDownload").onclick = () => createSubset(true);
    addTopRule({
      field: fields.includes("document_author") ? "document_author" : fields[0],
      operator: "equals",
      value: "Jacques Derrida",
    });
  }
  function openBulkFieldEditor({ rows = null, title = "Bulk edit one field" } = {}) {
    if (!state.files.length) return toast("Load JSONL records first");
    const dialog = document.createElement("dialog");
    dialog.className = "bulk-field-dialog";
    const fields = recordFields().filter(
      (field: Any) => field !== "updates" && !field.startsWith("_"),
    );
    const selectedCount = selectedReviewItems().length;
    const activeCount = activeFile()?.records.length || 0;
    const currentWork = selectedRecord()?.work || "";
    const fixedRows: Any = Array.isArray(rows) ? rows : null;
    const defaultScope = fixedRows ? "fixed" : selectedCount ? "selected" : "active";
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">Apply one field value consistently across a selected record set. Every actual change is audited.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db bulk-field-body">
    ${fixedRows ? `<div class="info">${fixedRows.length.toLocaleString()} records are in this operation.</div>` : `<div class="field"><label>Target records</label><select class="control" id="bulkFieldScope"><option value="selected" ${defaultScope === "selected" ? "selected" : ""} ${selectedCount ? "" : "disabled"}>Selected records (${selectedCount.toLocaleString()})</option><option value="active" ${defaultScope === "active" ? "selected" : ""}>Active JSONL (${activeCount.toLocaleString()})</option>${currentWork ? `<option value="work">Current work: ${esc(currentWork)}</option>` : ""}<option value="all">All loaded records (${allRows().length.toLocaleString()})</option></select></div>`}
    <div class="field"><label>Field</label><select class="control" id="bulkFieldName">${fields.map((field: Any) => `<option value="${esc(field)}">${esc(label(field))} · ${esc(field)}</option>`).join("")}</select></div>
    <div class="field"><label>New value</label><textarea id="bulkFieldValue" spellcheck="false" placeholder="Enter the new value. Arrays/objects use JSON. Enter __NULL__ for null."></textarea><div class="note" id="bulkFieldHint"></div></div>
    <label class="check-item"><input type="checkbox" id="bulkFieldOnlyDifferent" checked><span>Only modify records whose value actually differs</span></label>
  </div>
  <div class="da"><button class="btn" data-close>Cancel</button><button class="btn primary" id="applyBulkField">${icon("check")}Apply field update</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));

    const currentRows = () =>
      fixedRows || bulkEditRowsForScope(dialog.querySelector("#bulkFieldScope")?.value || "active");
    let lastHintField = "";
    const updateHint = () => {
      const field = dialog.querySelector("#bulkFieldName").value;
      const target = currentRows();
      const rawValues = target.slice(0, 300).map((row: Any) => row.record?.[field]);
      const values = [...new Set(rawValues.map((value: Any) => JSON.stringify(value)))];
      dialog.querySelector("#bulkFieldHint").textContent =
        `${target.length.toLocaleString()} target records · ${values.length} distinct current value${values.length === 1 ? "" : "s"}${values.length > 8 ? " (sampled)" : ""}`;
      const input = dialog.querySelector("#bulkFieldValue");
      if (values.length === 1 && (lastHintField !== field || !input.value.trim())) {
        const only = rawValues[0];
        input.value =
          only === null
            ? "__NULL__"
            : Array.isArray(only) || (only && typeof only === "object")
              ? JSON.stringify(only, null, 2)
              : String(only ?? "");
      } else if (lastHintField !== field && values.length !== 1) input.value = "";
      lastHintField = field;
    };
    dialog.querySelector("#bulkFieldScope")?.addEventListener("change", updateHint);
    dialog.querySelector("#bulkFieldName").addEventListener("change", updateHint);
    updateHint();

    dialog.querySelector("#applyBulkField").onclick = async () => {
      const target = currentRows();
      if (!target.length) return toast("No records are in the selected scope");
      const field = dialog.querySelector("#bulkFieldName").value;
      let value;
      try {
        value = parseBulkFieldValue(field, dialog.querySelector("#bulkFieldValue").value, target);
      } catch (error: Any) {
        return toast(error.message);
      }
      const changing = target.filter((row: Any) => !sameValue(row.record?.[field], value));
      if (!changing.length) return toast("Every target record already has that value");
      if (
        !(await openMessageModal({
          title: "Apply bulk field update?",
          message: `Set ${field} on ${changing.length.toLocaleString()} record${changing.length === 1 ? "" : "s"}?`,
          confirmLabel: "Apply update",
          cancelLabel: "Cancel",
        }))
      )
        return;
      const batchId = uid();
      let fieldChanges = 0;
      for (const row of changing) {
        fieldChanges += applyRecordChanges(
          row.file,
          row.index,
          { [field]: cloneAuditValue(value) },
          {
            source: "bulk_field_edit",
            batchId,
            reason: `Bulk edit ${field}`,
          },
        );
      }
      close();
      shell();
      renderView();
      toast(
        `Updated ${field} on ${changing.length.toLocaleString()} records · ${fieldChanges.toLocaleString()} audited changes`,
      );
    };
  }
  function openOcrCleanupDialog() {
    if (!state.files.length) return toast("Load JSONL records first");
    const dialog = document.createElement("dialog");
    const selected = selectedReviewItems();
    const active = activeFile();
    dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">Clean OCR Artifacts</h2><div class="dialog-subtitle">Conservative ligature, zero-width character, and broken line-hyphen cleanup. No paraphrasing.</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db ocr-clean-options"><button class="scope-card" data-scope="active" ${active ? "" : "disabled"}><b>Active JSONL tab</b><span>${active ? `${active.records.length.toLocaleString()} records · ${esc(active.name)}` : "No active tab"}</span></button><button class="scope-card" data-scope="selected" ${selected.length ? "" : "disabled"}><b>Selected records</b><span>${selected.length.toLocaleString()} currently selected</span></button><button class="scope-card" data-scope="review"><b>Needs-review records</b><span>${needsReviewItems().length.toLocaleString()} flagged records</span></button><button class="scope-card" data-scope="all"><b>All loaded records</b><span>${allRows().length.toLocaleString()} records across ${state.files.length} tabs</span></button></div><div class="da"><button class="btn" data-close>Cancel</button></div>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
    dialog.querySelectorAll("[data-scope]").forEach(
      (button: Any) =>
        (button.onclick = async () => {
          let rows = [];
          if (button.dataset.scope === "active" && active)
            rows = active.records.map((record: Any, index: Any) => ({
              file: active,
              record,
              index,
            }));
          else if (button.dataset.scope === "selected")
            rows = selected.map((item: Any) => ({
              file: item.file,
              record: item.record,
              index: item.index,
            }));
          else if (button.dataset.scope === "review")
            rows = needsReviewItems().map((item: Any) => ({
              file: item.file,
              record: item.record,
              index: item.index,
            }));
          else rows = allRows();
          if (!rows.length) return toast("No records in that scope");
          close();
          if (
            await openMessageModal({
              title: "Run OCR cleanup?",
              message: `Run conservative OCR cleanup on ${rows.length.toLocaleString()} records?`,
              confirmLabel: "Run cleanup",
              cancelLabel: "Cancel",
            })
          )
            cleanRows(rows);
        }),
    );
  }
  function openEditor() {
    const f = activeFile(),
      i = selectedIndex(f),
      r = selectedRecord();
    if (!r) return;
    const dialog = document.createElement("dialog");
    const used = new Set();
    const groups = [];
    for (const group of EDITOR_GROUPS) {
      const fields = group.fields.filter((k: Any) => k in r);
      if (!fields.length) continue;
      fields.forEach((k: Any) => used.add(k));
      groups.push(
        `<section class="editor-section"><h3>${esc(group.name)}</h3><div class="editor-grid">${fields.map((k: Any) => fieldEditor(k, r[k])).join("")}</div></section>`,
      );
    }
    const other = Object.keys(r).filter((k) => !used.has(k) && k !== "updates");
    if (other.length)
      groups.push(
        `<section class="editor-section"><h3>Other fields</h3><div class="editor-grid">${other.map((k) => fieldEditor(k, r[k])).join("")}</div></section>`,
      );
    dialog.innerHTML = `<form><div class="dh"><div><h2 class="dialog-title">Edit record</h2><div class="dialog-subtitle">${esc(r.record_id || "")} · ${esc(r.work || f.name)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body">${groups.join("")}</div><div class="da"><div class="llm-footer-note">Changes stay local until you export or upsert them.</div><button class="btn" type="button" data-close>Cancel</button><button class="btn primary">${icon("check")}Save changes</button></div></form>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    dialog.querySelectorAll("[data-close]").forEach(
      (b: Any) =>
        (b.onclick = () => {
          dialog.close();
          dialog.remove();
        }),
    );
    dialog.querySelector("form").onsubmit = (e: Any) => {
      e.preventDefault();
      const next = { ...r };
      try {
        dialog
          .querySelectorAll("[data-key]")
          .forEach((el: Any) => (next[el.dataset.key] = parseEditor(el)));
      } catch (error: Any) {
        openMessageModal({
          title: "Could not save record",
          message: error.message,
          tone: "danger",
        });
        return;
      }
      if ("text_length" in next) next.text_length = String(next.text || "").length;
      const changes: Any = {};
      for (const [field, value] of Object.entries(next))
        if (field !== "updates" && !sameValue(r[field], value)) changes[field] = value;
      const count = applyRecordChanges(f, i, changes, { source: "manual" });
      dialog.close();
      dialog.remove();
      shell();
      renderView();
      count
        ? toast(`Saved ${count} tracked change${count === 1 ? "" : "s"}`, { tone: "success" })
        : toast("No changes to save");
    };
  }
  function openStoreRecordEditor(record: Any) {
    const chromaId = record._chroma_id;
    if (!chromaId) return toast(tr("record.no_storage_id", "This Chroma record has no storage ID"));
    const dialog = document.createElement("dialog");
    const editable = Object.keys(record).filter(
      (k) =>
        k !== "_chroma_id" &&
        k !== "updates" &&
        k !== "_updates_count" &&
        !k.startsWith("_researcher_"),
    );
    dialog.innerHTML = `<form><div class="dh"><div><h2 class="dialog-title">Edit Chroma record</h2><div class="dialog-subtitle">${esc(chromaId)} · ${esc(state.activeStore)}</div></div><button class="btn icon-only" type="button" data-close>${icon("close")}</button></div><div class="db editor-body"><div class="info">Saving updates this record in place under the same Chroma ID and regenerates its embedding when the configured embedding provider allows it.</div><section class="editor-section"><h3>Record</h3><div class="editor-grid">${editable.map((k) => fieldEditor(k, record[k])).join("")}</div></section></div><div class="da"><button class="btn" type="button" data-close>Cancel</button><button class="btn primary">${icon("check")}Save to Chroma</button></div></form>`;
    document.body.appendChild(dialog);
    showAppModal(dialog);
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    dialog.querySelectorAll("[data-close]").forEach((b: Any) => (b.onclick = close));
    dialog.querySelector("form").onsubmit = async (e: Any) => {
      e.preventDefault();
      const raw = { ...record };
      delete raw._chroma_id;
      const changes: Any = {};
      try {
        dialog.querySelectorAll("[data-key]").forEach((el: Any) => {
          const value = parseEditor(el);
          if (!sameValue(raw[el.dataset.key], value)) changes[el.dataset.key] = value;
        });
      } catch (error: Any) {
        openMessageModal({
          title: "Could not parse edited record",
          message: error.message,
          tone: "danger",
        });
        return;
      }
      if (!Object.keys(changes).length) return close();
      const timestamp = new Date().toISOString(),
        batchId = uid();
      const auditEntries = Object.entries(changes).map(([field, newValue]) => ({
        field_name: field,
        old_value: cloneAuditValue(raw[field]),
        new_value: cloneAuditValue(newValue),
        timestamp,
        source: "chroma_manual",
        batch_id: batchId,
        initiated_by: state.userContext?.username || null,
      }));
      try {
        await api(
          `/api/stores/${encodeURIComponent(state.activeStore)}/records/${encodeURIComponent(chromaId)}`,
          {
            method: "PATCH",
            body: JSON.stringify({
              changes,
              audit_entries: auditEntries,
              document_field: "text",
              embedding_field: "embedding",
            }),
          },
        );
        state.storeWorksStore = "";
        close();
        toast("Chroma record updated", { tone: "success" });
        renderView();
      } catch (error: Any) {
        toast(`Chroma update failed: ${error.message}`, { tone: "danger" });
      }
    };
  }
  function openRecordHistoryBrowser(file: Any, index: Any) {
    const record = file?.records?.[index];
    if (!record) return;
    let versions = recordHistoryVersions(record);
    if (versions.length <= 1) return toast("This record has no update history");
    let cursor = versions.length - 1;
    const dialog = document.createElement("dialog");
    dialog.className = "record-history-dialog";
    const close = () => {
      dialog.close();
      dialog.remove();
    };
    const render = () => {
      versions = recordHistoryVersions(file.records[index]);
      cursor = Math.max(0, Math.min(cursor, versions.length - 1));
      const version = versions[cursor];
      const previous = cursor > 0 ? versions[cursor - 1] : null;
      const changed = previous ? historyVersionChanges(previous.record, version.record) : [];
      const currentIndex = versions.length - 1;
      const isCurrent = cursor === currentIndex;
      const text = String(version.record.text || "");
      dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">Record history</h2><div class="dialog-subtitle">${esc(file.records[index]?.record_id || `Record ${index + 1}`)} · ${versions.length - 1} saved change set${versions.length - 1 === 1 ? "" : "s"}</div></div><button class="btn icon-only" data-close title="${esc(tr("ui.close", "Close"))}" aria-label="${esc(tr("ui.close", "Close"))}">${icon("close")}</button></div>
      <div class="db record-history-body">
        <div class="history-version-nav">
          <button class="btn" id="historyOlder" ${cursor <= 0 ? `disabled data-disabled-reason="Already at the original record."` : ""}>← Older</button>
          <div class="history-version-position"><b>${esc(version.label)}${isCurrent ? " · Current" : ""}</b><span>${version.timestamp ? esc(formatTimestamp(version.timestamp)) : "Before tracked edits"}${version.source ? ` · ${esc(version.source)}` : ""}${version.model ? ` · ${esc(version.model)}` : ""}</span></div>
          <button class="btn" id="historyNewer" ${cursor >= currentIndex ? `disabled data-disabled-reason="Already at the newest version."` : ""}>Newer →</button>
        </div>
        <div class="history-version-summary"><span><b>${changed.length}</b> field${changed.length === 1 ? "" : "s"} changed in this version</span><span><b>${text.trim() ? text.trim().split(/\s+/).length : 0}</b> words</span><span><b>${text.length.toLocaleString()}</b> characters</span></div>
        ${changed.length ? `<div class="history-version-diffs">${changed.map((field: Any) => `<details class="history-version-diff"><summary><b>${esc(label(field))}</b><span>changed</span></summary><div class="history-diff-values"><div><small>Previous</small><pre>${esc(jsonPretty(previous?.record?.[field]))}</pre></div><div><small>This version</small><pre>${esc(jsonPretty(version.record?.[field]))}</pre></div></div></details>`).join("")}</div>` : `<div class="info">This is the reconstructed original state before tracked updates.</div>`}
        <details class="history-record-preview"><summary>Preview this version</summary><div class="history-preview-meta"><b>${esc(version.record.work || "Untitled work")}</b><span>${esc(version.record.document_author || "")} · ${esc(version.record.year || "")}</span></div><div class="history-preview-text">${esc(text.slice(0, 5000))}${text.length > 5000 ? "…" : ""}</div></details>
      </div>
      <div class="da record-history-actions"><button class="btn danger secondary-danger" id="historyClear">Delete audit history…</button><span class="dialog-action-spacer"></span><button class="btn" data-close>Close</button><button class="btn" id="historyUndoAll" ${cursor === 0 && isCurrent ? "disabled" : ""}>Restore original</button><button class="btn primary" id="historyRestore" ${isCurrent ? `disabled data-disabled-reason="This is already the current version."` : ""}>Restore this version</button></div>`;
      dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
      dialog.querySelector("#historyOlder").onclick = () => {
        cursor--;
        render();
      };
      dialog.querySelector("#historyNewer").onclick = () => {
        cursor++;
        render();
      };
      dialog.querySelector("#historyRestore").onclick = async () => {
        if (isCurrent) return;
        const count = restoreRecordHistoryVersion(file, index, version);
        if (!count) return toast("No record fields needed restoring");
        versions = recordHistoryVersions(file.records[index]);
        cursor = versions.length - 1;
        shell();
        renderView();
        render();
        toast(`Restored ${count} field${count === 1 ? "" : "s"} from ${version.label}`);
      };
      dialog.querySelector("#historyUndoAll").onclick = async () => {
        const original = versions[0];
        if (
          !(await openMessageModal({
            title: "Restore original record?",
            message:
              "Restore every field to its state before the tracked update history? The restoration itself will be recorded, so you can move forward again later.",
            confirmLabel: "Restore original",
            cancelLabel: "Cancel",
          }))
        )
          return;
        const count = restoreRecordHistoryVersion(file, index, original);
        if (!count) return toast("The record already matches its original tracked state");
        versions = recordHistoryVersions(file.records[index]);
        cursor = versions.length - 1;
        shell();
        renderView();
        render();
        toast(`Restored original record state · ${count} fields changed`);
      };
      dialog.querySelector("#historyClear").onclick = async () => {
        if (!(await clearRecordUpdates(file, index))) return;
        close();
        shell();
        renderView();
        toast("Record update history cleared");
      };
      decorateDisabledControls(dialog);
    };
    document.body.appendChild(dialog);
    showAppModal(dialog);
    render();
  }
  async function openUpsertQueue() {
    if (!hasCorpusDb())
      return openMessageModal({
        title: "Vector database required",
        message: dbUnavailableReason(),
        confirmLabel: "OK",
      });
    if (!state.activeStore) return toast("Select a Chroma collection first");
    if (allRows().length) await refreshPresenceForRows(allRows());
    const _rows = pendingUpsertRows();
    const dialog = document.createElement("dialog");
    dialog.className = "queue-dialog wide-queue-dialog";

    const render = () => {
      const currentRows = pendingUpsertRows();
      dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(tr("vector.unsynced_changes", "Unsynced local changes"))}</h2><div class="dialog-subtitle">${esc(state.activeStore)} · ${currentRows.length} ${esc(tr("dynamic.records", "records"))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db">
      <div class="queue-explainer"><b>${esc(tr("vector.unsynced_changes_what", "What is this list?"))}</b><p>${esc(tr("vector.unsynced_changes_help", "These are browser-workspace records that changed since their last confirmed sync, plus records DerridAI has confirmed are missing from the selected collection. Removing an item suppresses only its current version; a later change queues it again."))}</p></div><div class="queue-bulk-actions">${currentRows.length ? `<button class="btn small" id="queueSelectAll">${esc(tr("ui.select_all", "Select all"))}</button><button class="btn small" id="queueSelectNone">${esc(tr("ui.clear_selection", "Clear selection"))}</button>` : ""}</div>
      <div class="upsert-queue-list">${
        currentRows
          .map((row: Any) => {
            const info = recordDbStatus(row.file, row.index, row.record);
            const key = localRecordKey(row.file, row.index);
            const changes = pendingChangesForRow(row);
            return `<section class="upsert-queue-card">
          <div class="upsert-queue-head">
            <label class="upsert-queue-item"><input type="checkbox" data-upsert-key="${esc(key)}" checked><span><b>${esc(row.record.record_id || `Record ${row.index + 1}`)}</b><small>${esc(row.record.work || row.file.name)} · ${esc(row.file.name)}</small></span><span class="db-status ${info.kind}"><i></i>${esc(info.label)}</span></label>
            <div class="tools"><button class="btn small" data-review-queue="${esc(key)}">Review ${changes.length} change${changes.length === 1 ? "" : "s"}</button><button class="btn small danger" data-remove-queue="${esc(key)}">Remove from queue</button></div>
          </div>
          <div class="queue-change-list hidden" data-queue-changes="${esc(key)}">${changes.map((change: Any) => `<div class="queue-change-row"><b>${esc(label(change.field_name || "field"))}</b><span>${esc(change.source || "manual")}${change.timestamp ? ` · ${esc(formatTimestamp(change.timestamp))}` : ""}</span><details><summary>Values</summary><div class="queue-change-values"><pre>${esc(jsonPretty(change.old_value))}</pre><span>→</span><pre>${esc(jsonPretty(change.new_value))}</pre></div></details></div>`).join("")}</div>
        </section>`;
          })
          .join("") ||
        `<div class="llm-empty">${esc(tr("vector.no_unsynced_changes", "No confirmed unsynced local changes."))}</div>`
      }</div>
    </div>
    <div class="da"><button class="btn" data-close>Close</button>${currentRows.length ? `<button class="btn primary" id="upsertQueued">${icon("database")}${esc(tr("vector.sync_selected", "Sync selected"))}</button>` : ""}</div>`;

      const close = () => {
        dialog.close();
        dialog.remove();
      };
      dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
      dialog
        .querySelector("#queueSelectAll")
        ?.addEventListener("click", () =>
          dialog.querySelectorAll("[data-upsert-key]").forEach((box: Any) => (box.checked = true)),
        );
      dialog
        .querySelector("#queueSelectNone")
        ?.addEventListener("click", () =>
          dialog.querySelectorAll("[data-upsert-key]").forEach((box: Any) => (box.checked = false)),
        );
      dialog.querySelectorAll("[data-review-queue]").forEach(
        (button: Any) =>
          (button.onclick = () => {
            const panel = dialog.querySelector(
              `[data-queue-changes="${CSS.escape(button.dataset.reviewQueue)}"]`,
            );
            panel?.classList.toggle("hidden");
          }),
      );
      dialog.querySelectorAll("[data-remove-queue]").forEach(
        (button: Any) =>
          (button.onclick = () => {
            const row = currentRows.find(
              (item: Any) => localRecordKey(item.file, item.index) === button.dataset.removeQueue,
            );
            if (row) {
              removeFromUpsertQueue(row);
              render();
              shell();
            }
          }),
      );
      dialog.querySelector("#upsertQueued")?.addEventListener("click", async () => {
        const selected = new Set(
          [...dialog.querySelectorAll("[data-upsert-key]:checked")].map((x) => x.dataset.upsertKey),
        );
        const chosen = currentRows.filter((row: Any) =>
          selected.has(localRecordKey(row.file, row.index)),
        );
        if (!chosen.length) return toast("Select at least one queued record");
        close();
        await upsertRows(chosen, "queued records");
        shell();
        renderView();
      });
    };

    document.body.appendChild(dialog);
    showAppModal(dialog);
    render();
  }
  return {
    openMergeDialog,
    openSubsetBuilder,
    openBulkFieldEditor,
    openOcrCleanupDialog,
    openEditor,
    openStoreRecordEditor,
    openRecordHistoryBrowser,
    openUpsertQueue,
  };
}
