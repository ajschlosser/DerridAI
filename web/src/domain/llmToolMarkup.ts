/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

type Tr = (key: string, fallback?: string) => string;
type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function llmToolResultDialogHtml(
  input: { title: string; job: Any; result: Any; body: string; actions: string },
  tr: Tr,
): string {
  const { title, job, result, body, actions } = input;
  return `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(job.provider || "")} · ${esc(job.model || result.model || "")}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db">${body}</div><div class="da"><button class="btn" data-close>${esc(tr("common.close", "Close"))}</button>${actions}</div>`;
}

export function llmToolResultBody(
  task: string,
  job: Any,
  result: Any,
  deps: { tr: Tr; trf: Trf; ragGradeHtml: (grade: Any) => string },
): { body: string; actions: string } {
  const { tr, trf, ragGradeHtml } = deps;
  if (task === "pdf_clean_text") {
    return {
      body: `<section class="card-inset"><div class="cardhead"><b>${esc(tr("jobs.tool.cleaned_text", "Cleaned page text"))}</b></div><pre class="llm-tool-text">${esc(result.text || "")}</pre></section>`,
      actions: `<button class="btn primary" id="useToolText">${esc(tr("jobs.tool.use_page_text", "Use as current page text"))}</button>`,
    };
  }
  if (task === "pdf_draft_record") {
    return {
      body: `<pre class="rag-json">${esc(JSON.stringify(result.record || {}, null, 2))}</pre>`,
      actions: `<button class="btn primary" id="openToolDraft">${esc(tr("jobs.tool.review_draft", "Review / add draft"))}</button>`,
    };
  }
  if (task === "pdf_link_record") {
    return {
      body: `<div class="llm-tool-match"><b>${esc(result.match?.record_id || tr("jobs.tool.no_match", "No supported match"))}</b><p>${esc(result.match?.reason || "")}</p></div>`,
      actions: result.match?.key
        ? `<button class="btn primary" id="applyToolLink">${esc(tr("jobs.tool.review_link", "Review & link page"))}</button>`
        : "",
    };
  }
  if (task === "rag_grade") {
    const question = job.request?.question || "";
    const body = `${question ? `<section class="llm-tool-context"><span>${esc(tr("jobs.tool.question", "Question / prompt"))}</span><p>${esc(question)}</p></section>` : ""}${result.response_cache_error ? `<div class="info warn">${esc(trf("jobs.tool.grade_cache_failed", "The grade completed, but saving it to the response cache failed: {error}", { error: result.response_cache_error }))}</div>` : ""}${ragGradeHtml(result.grade || {})}`;
    return { body, actions: "" };
  }
  if (task === "rag_grade_batch") {
    const errors = Array.isArray(result.errors) && result.errors.length;
    const body = `<section class="bulk-grade-result"><div class="compare-result-summary"><div><strong>${Number(result.graded || 0).toLocaleString()}</strong><span>${esc(tr("jobs.tool.graded", "graded"))}</span></div><div><strong>${Number(result.failed || 0).toLocaleString()}</strong><span>${esc(tr("jobs.tool.failed", "failed"))}</span></div><div><strong>${Number(result.total || 0).toLocaleString()}</strong><span>${esc(tr("jobs.tool.responses", "responses"))}</span></div></div>${errors ? `<details><summary>${esc(trf("jobs.tool.errors_n", "Errors ({count})", { count: result.errors.length }))}</summary><pre class="rag-json">${esc(JSON.stringify(result.errors, null, 2))}</pre></details>` : `<div class="info">${esc(tr("jobs.tool.all_processed", "All cached responses were processed."))}</div>`}</section>`;
    return { body, actions: "" };
  }
  return { body: `<pre class="rag-json">${esc(JSON.stringify(result, null, 2))}</pre>`, actions: "" };
}

export function llmTaskLauncherHtml(
  input: {
    title: string;
    description: string;
    contextText: string;
    sameModel: boolean;
    profiles: Any[];
    profile: Any;
    status: Any;
    task: string;
    runMode: string;
    isResearcher: boolean;
    providerDisplayName: (item: Any) => string;
  },
  tr: Tr,
): string {
  const {
    title,
    description,
    contextText,
    sameModel,
    profiles,
    profile,
    status,
    task,
    runMode,
    isResearcher,
    providerDisplayName,
  } = input;
  const thinkOptions = [
    ["false", tr("jobs.tool.think_off", "Off")],
    ["true", tr("jobs.tool.think_on", "On")],
    ["low", tr("jobs.tool.think_low", "Low")],
    ["medium", tr("jobs.tool.think_medium", "Medium")],
    ["high", tr("jobs.tool.think_high", "High")],
  ];
  const runModeOptions =
    task === "rag_grade_batch"
      ? `<option value="background" selected>${esc(tr("jobs.tool.background", "Background operation"))}</option>`
      : isResearcher
        ? `<option value="foreground" selected>${esc(tr("jobs.tool.foreground", "Interactive foreground"))}</option>`
        : `<option value="background" ${runMode === "background" ? "selected" : ""}>${esc(tr("jobs.tool.background", "Background operation"))}</option><option value="foreground" ${runMode === "foreground" ? "selected" : ""}>${esc(tr("jobs.tool.foreground", "Interactive foreground"))}</option>`;
  const ollamaType = tr("jobs.tool.ollama", "Ollama");
  const openaiType = tr("jobs.tool.openai_compat", "OpenAI-compatible");
  return `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(description)}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db llm-tool-body">
      ${contextText ? `<section class="llm-tool-context"><span>${esc(tr("jobs.tool.question", "Question / prompt"))}</span><p>${esc(contextText)}</p></section>` : ""}
      ${sameModel ? `<div class="info warn"><b>${esc(tr("jobs.tool.same_model_title", "Same-model grading warning."))}</b> ${esc(tr("jobs.tool.same_model_help", "This provider/model was also used to generate the RAG answer. Self-grading can be systematically biased; use a different model for a more independent evaluation."))}</div>` : ""}
      <div class="llm-tool-grid">
        <div class="field field-wide"><label>${esc(tr("jobs.tool.provider_profile", "Provider profile"))}</label><select class="control" id="toolProvider">${profiles.map((item: Any) => `<option value="${esc(item.id)}" ${item.id === profile.id ? "selected" : ""}>${esc(providerDisplayName(item))} · ${item.type === "ollama" ? ollamaType : openaiType}</option>`).join("")}</select></div>
        <div class="field"><label>${esc(tr("jobs.tool.run_mode", "Run mode"))}</label><select class="control" id="toolRunMode" ${isResearcher || task === "rag_grade_batch" ? "disabled" : ""}>${runModeOptions}</select></div>
        <div class="field field-wide"><label>${esc(tr("providers.model", "Model"))}</label><input class="control" id="toolModel" value="${esc(profile.type === "openai" && profile.model_mode === "auto" ? "auto" : profile.model || "")}" ${profile.type === "openai" && profile.model_mode === "auto" ? "disabled" : ""}></div>
        <div class="field"><label>${esc(tr("jobs.tool.max_concurrent", "Max concurrent requests"))}</label><input class="control" value="${esc(profile.max_concurrent_requests ?? 1)}" disabled></div>
        ${
          profile.type === "ollama"
            ? `<div class="field"><label>${esc(tr("providers.context", "Context tokens"))}</label><input class="control" id="toolCtx" type="number" value="${esc(profile.num_ctx ?? 16384)}"></div><div class="field"><label>${esc(tr("providers.think", "Think"))}</label><select class="control" id="toolThink">${thinkOptions
                .map(
                  ([v, l]) =>
                    `<option value="${v}" ${String(profile.think ?? "false") === v ? "selected" : ""}>${esc(l)}</option>`,
                )
                .join("")}</select></div>`
            : ""
        }
        <div class="field"><label>${esc(tr("providers.max_output", "Max output tokens"))}</label><input class="control" id="toolPredict" type="number" value="${esc(profile.num_predict ?? 4096)}"></div>
        <div class="field"><label>${esc(tr("providers.temperature", "Temperature"))}</label><input class="control" id="toolTemp" type="number" step="0.01" value="${esc(profile.temperature ?? 0)}"></div>
        <div class="field"><label>${esc(tr("providers.top_p", "Top P"))}</label><input class="control" id="toolTopP" type="number" step="0.01" value="${esc(profile.top_p ?? 1)}"></div>
        <div class="field"><label>${esc(tr("providers.seed", "Seed"))}</label><input class="control" id="toolSeed" type="number" value="${esc(profile.seed ?? "")}"></div>
        <div class="field field-wide"><label>${esc(tr("jobs.tool.advanced_json", "Advanced options JSON"))}</label><textarea id="toolExtra" spellcheck="false">${esc(profile.extra_options || "{}")}</textarea></div>
      </div>
      <div class="tools llm-tool-profile-actions"><button class="btn small" id="toolWarm">${icon("spark")}${esc(tr("jobs.tool.warm", "Warm this provider"))}</button>${isResearcher ? "" : `<button class="btn small" id="toolProviders">${icon("gear")}${esc(tr("pdf.manage_providers", "Manage LLM providers"))}</button>`}<span class="note" id="toolStatus">${status.available ? esc(tr("jobs.tool.endpoint_ready", "Endpoint ready")) : esc(status.error || tr("providers.not_verified", "Not verified"))}</span></div>
    </div>
    <div class="da"><button class="btn" data-close>${esc(tr("common.cancel", "Cancel"))}</button><button class="btn primary" id="runLlmTask">${icon("spark")}${esc(runMode === "background" ? tr("jobs.tool.start_background", "Start background operation") : tr("jobs.tool.run_now", "Run now"))}</button></div>`;
}

export function pdfDraftRecordHtml(
  input: { title: string; page: number; recordJson: string; files: Any[]; stores: Any[] },
  deps: { tr: Tr; trf: Trf },
): string {
  const { tr, trf } = deps;
  const { title, page, recordJson, files, stores } = input;
  const chromaDisabled = stores.length
    ? ""
    : `disabled data-disabled-reason="${esc(tr("jobs.draft.chroma_required", "Create or restore a corpus vector database before upserting PDF drafts."))}" title="${esc(tr("jobs.draft.chroma_required", "Create or restore a corpus vector database before upserting PDF drafts."))}"`;
  return `<div class="dh"><div><h2 class="dialog-title">${esc(tr("jobs.draft.title", "Draft record from PDF page"))}</h2><div class="dialog-subtitle">${esc(title)} · ${esc(trf("jobs.draft.subtitle", "page {page} · unsaved draft", { page }))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
  <div class="db pdf-draft-body">
    <div class="info warn">${esc(tr("jobs.draft.warn", "This is a draft generated by an LLM. Review attribution, page metadata, quotation provenance, and text before saving."))}</div>
    <textarea class="pdf-draft-json" id="pdfDraftJson" spellcheck="false">${esc(recordJson)}</textarea>
    <div class="pdf-draft-targets">
      <div class="field"><label>${esc(tr("jobs.draft.jsonl", "JSONL destination"))}</label><select class="control" id="pdfDraftFile"><option value="">${esc(tr("jobs.draft.no_jsonl", "Do not add to JSONL"))}</option>${files.map((file: Any) => `<option value="${esc(file.id)}">${esc(file.name)} · ${esc(trf("jobs.draft.file_records", "{count} records", { count: file.records.length }))}</option>`).join("")}</select></div>
      <div class="field"><label>${esc(tr("jobs.draft.chroma", "Chroma destination"))}</label><select class="control" id="pdfDraftStore" ${chromaDisabled}><option value="">${esc(stores.length ? tr("jobs.draft.no_chroma", "Do not upsert to Chroma") : tr("jobs.draft.no_db", "No corpus database available"))}</option>${stores.map((store: Any) => `<option value="${esc(store.name)}">${esc(store.name)} · ${esc(trf("jobs.draft.file_records", "{count} records", { count: Number(store.count || 0).toLocaleString() }))}</option>`).join("")}</select></div>
    </div>
  </div>
  <div class="da"><button class="btn" data-close>${esc(tr("common.cancel", "Cancel"))}</button><button class="btn primary" id="savePdfDraft">${icon("check")}${esc(tr("jobs.draft.add", "Add draft"))}</button></div>`;
}
