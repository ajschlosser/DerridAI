/* Copyright 2026 Aaron John Schlosser, PhD. */

import { mountOperationsPanel } from "../runtime/operationsPanelHost";
import { subscribeToJobChanges, touchJobs } from "../state/jobsState";
import { esc, icon } from "./html";

// The operations panel host, the RAG progress panel and the corpus-builds home card: bridging the runtime's jobs to the
// Vue operations panel, and the small HTML fragments the dashboard/RAG view render around it. Moved verbatim from the
// legacy runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "api"
  | "cancelBackgroundJob"
  | "formatTimestamp"
  | "humanDuration"
  | "isResearcher"
  | "jobElapsedSeconds"
  | "openJobDetails"
  | "openJobResults"
  | "openLlmTaskLauncher"
  | "openMessageModal"
  | "operationViewModel"
  | "persistPrefs"
  | "pruneClientJobState"
  | "ragGradeEvidencePayload"
  | "ragGradeHtml"
  | "refreshJobs"
  | "showAppModal"
  | "toast"
  | "tr"
  | "trf";
type Deps = { state: Loose } & Record<Helper, Fn>;

const RAG_STAGE_ORDER: Array<[string, string, string]> = [
  ["query_metadata", "rag.stage.query_metadata", "Query decomposition"],
  ["retrieval", "rag.stage.retrieval", "Vector retrieval"],
  ["deduplicate", "rag.stage.deduplicate", "Deduplication / rank fusion"],
  ["rerank", "rag.stage.rerank", "Reranking"],
  ["context", "rag.stage.context", "Evidence packaging"],
  ["generation", "rag.stage.generation", "Answer generation"],
  ["bind_sources", "rag.stage.bind_sources", "Citation/source binding"],
  ["response_cache", "rag.stage.response_cache", "Response cache"],
  ["auto_grade", "rag.stage.auto_grade", "Automatic grade"],
];

export function createOperationsPanelBridge(deps: Deps) {
  const {
    state,
    api,
    cancelBackgroundJob,
    formatTimestamp,
    humanDuration,
    isResearcher,
    jobElapsedSeconds,
    openJobDetails,
    openJobResults,
    openLlmTaskLauncher,
    openMessageModal,
    operationViewModel,
    persistPrefs,
    pruneClientJobState,
    ragGradeEvidencePayload,
    ragGradeHtml,
    refreshJobs,
    showAppModal,
    toast,
    tr,
    trf,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  function notifyOperationsChanged() {
    touchJobs();
  }
  function operationsBridge() {
    return {
      snapshot: () => (state.jobs || []).map(operationViewModel),
      subscribe: (listener: Any) => subscribeToJobChanges(listener),
      refresh: async () => {
        await refreshJobs({ rerender: true });
      },
      openDetails: (id: Any) => {
        void openJobDetails(id);
      },
      openResult: (id: Any) => {
        void openJobResults(id);
      },
      cancel: async (id: Any) => {
        await cancelBackgroundJob(id);
      },
      remove: async (id: Any) => {
        await api(`/api/jobs/${encodeURIComponent(id)}`, { method: "DELETE" });
        pruneClientJobState(id);
        persistPrefs();
        await refreshJobs({ rerender: true });
      },
      clearFinished: async () => {
        await api("/api/jobs", { method: "DELETE" });
        await refreshJobs({ rerender: true });
      },
    };
  }
  function renderOperationsPanel() {
    // A placeholder only: the Vue panel is mounted into it by mountOperationsPanelHost().
    return `<div id="operationsPanelHost"></div>`;
  }
  function mountOperationsPanelHost() {
    mountOperationsPanel(document.querySelector("#operationsPanelHost"), operationsBridge());
  }
  function refreshOperationsPanelOnly() {
    notifyOperationsChanged();
    if (state.view === "rag") refreshRagProgressPanel();
  }
  function wireCorpusBuildsHomeCard(root = document) {
    root.querySelector("#dashCorpusBuilder")?.addEventListener("click", () =>
      window.dispatchEvent(
        new CustomEvent("derridai:navigate-native", {
          detail: { path: "/pdf?mode=builder", runtimeView: "pdf" },
        }),
      ),
    );
    root
      .querySelectorAll("[data-dashboard-corpus-build]")
      .forEach((button: Any) =>
        button.addEventListener("click", () => openJobResults(button.dataset.dashboardCorpusBuild)),
      );
  }
  function refreshCorpusBuildsHomeCardOnly() {
    const current = document.querySelector(".dashboard-corpus-builds");
    if (!current) return;
    const holder = document.createElement("div");
    holder.innerHTML = renderCorpusBuildsHomeCard();
    const replacement = holder.firstElementChild;
    if (replacement) current.replaceWith(replacement);
    wireCorpusBuildsHomeCard();
  }
  async function gradeRagResponse({
    question,
    answer,

    evidence = [],
    responseRecordId = null,
    generationProvider = null,
    generationModel = null,
  }: Any) {
    openLlmTaskLauncher({
      task: "rag_grade",
      title: tr("rag.grade_title", "Analyze & grade RAG response"),
      description: tr(
        "rag.grade_help",
        "Grade relevance, source binding, attribution, fidelity, precision, coverage, and interpretive usefulness.",
      ),
      contextText: question,
      generationProvider,
      generationModel,
      payload: {
        question,
        answer,
        evidence: ragGradeEvidencePayload(evidence),
        response_record_id: responseRecordId,
        generation_provider: generationProvider,
        generation_model: generationModel,
      },
      onForegroundResult: async (result: Any) => {
        const dialog = document.createElement("dialog");
        dialog.className = "rag-grade-dialog";
        dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(tr("rag.grade_result_title", "RAG response grade"))}</h2><div class="dialog-subtitle">${esc(tr("rag.grade_result_help", "Saved with the cached RAG query when a response-cache record is available."))}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div><div class="db">${ragGradeHtml(result.grade || {})}</div><div class="da"><button class="btn" data-close>${esc(tr("common.close", "Close"))}</button></div>`;
        document.body.appendChild(dialog);
        showAppModal(dialog);
        const close = () => {
          dialog.close();
          dialog.remove();
        };
        dialog.querySelectorAll("[data-close]").forEach((button: Any) => (button.onclick = close));
      },
    });
  }
  async function removeRagJob(jobId: Any) {
    const job = state.jobs.find((item: Any) => item.id === jobId);
    if (!job) return pruneClientJobState(jobId);
    if (["queued", "running", "cancelling"].includes(job.status))
      return toast(tr("rag.cancel_before_remove", "Cancel the RAG pipeline before removing it"));
    const approved = await openMessageModal({
      title: tr("rag.remove_title", "Remove RAG pipeline result?"),
      message: trf(
        "rag.remove_help",
        "Remove this {status} RAG pipeline and its retained result from activity history?",
        { status: job.status },
      ),
      tone: "danger",
      confirmLabel: tr("rag.remove_confirm", "Remove pipeline"),
      cancelLabel: tr("common.cancel", "Cancel"),
    });
    if (!approved) return;
    try {
      await api(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" });
      pruneClientJobState(jobId);
      persistPrefs();
      refreshRagProgressPanel();
      if (state.view === "home") refreshOperationsPanelOnly();
      toast(tr("rag.pipeline_removed", "RAG pipeline removed"));
    } catch (error: Any) {
      if (String(error?.message || "").includes("404")) {
        pruneClientJobState(jobId);
        persistPrefs();
        refreshRagProgressPanel();
        return toast(tr("rag.already_removed", "RAG pipeline was already removed"));
      }
      openMessageModal({
        title: tr("rag.remove_failed", "Could not remove RAG pipeline"),
        message: error.message,
        tone: "danger",
      });
    }
  }
  async function clearFinishedRagJobs() {
    const finished = state.jobs.filter(
      (job: Any) => job.type === "rag" && !["queued", "running", "cancelling"].includes(job.status),
    );
    if (!finished.length) return toast(tr("rag.none_to_clear", "There are no past RAG results to clear"));
    if (
      !(await openMessageModal({
        title: tr("rag.clear_past_title", "Clear past RAG results?"),
        message: trf(
          "rag.clear_past_help",
          "Clear {count} finished RAG operation(s) and their retained results?",
          { count: finished.length },
        ),
        tone: "danger",
        confirmLabel: tr("rag.clear_results", "Clear results"),
        cancelLabel: tr("ui.cancel", "Cancel"),
      }))
    )
      return;
    let removed = 0,
      failed = 0;
    for (const job of finished) {
      try {
        await api(`/api/jobs/${encodeURIComponent(job.id)}`, { method: "DELETE" });
        pruneClientJobState(job.id);
        removed++;
      } catch (error) {
        failed++;
        console.warn("Could not remove RAG job", job.id, error);
      }
    }
    await refreshJobs();
    refreshRagProgressPanel();
    toast(
      failed
        ? trf(
            "rag.cleared_past_failed",
            "Cleared {count} past RAG result(s) · {failed} could not be removed",
            { count: removed, failed },
          )
        : trf("rag.cleared_past", "Cleared {count} past RAG result(s)", { count: removed }),
    );
  }
  function ragProgressPanelHtml() {
    const allRagJobs = state.jobs.filter((job: Any) => job.type === "rag");
    const jobs = allRagJobs.slice(0, 12);
    const activeCount = allRagJobs.filter((job: Any) =>
      ["queued", "running", "cancelling"].includes(job.status),
    ).length;
    const finishedCount = allRagJobs.length - activeCount;
    const param = (key: string, fallback: string, value: unknown) =>
      trf(key, fallback, { value: value == null || value === "" ? "—" : String(value) });
    return `<section class="card rag-live-panel" id="ragProgressPanel">
    <div class="cardhead"><div><b>${esc(tr("rag.activity_title", "RAG pipeline activity"))}</b><div class="note">${esc(trf("rag.activity_summary", "{active} active · {finished} past result(s) · stage, model, parameters, and timing refresh automatically", { active: activeCount, finished: finishedCount }))}</div></div><div class="tools"><button class="btn small" id="ragRefreshJobs">${icon("refresh")}${esc(tr("ui.refresh", "Refresh"))}</button>${finishedCount ? `<button class="btn small danger" id="ragClearFinished">${esc(tr("rag.clear_past", "Clear past results"))}</button>` : ""}</div></div>
    <div class="rag-live-jobs">${
      jobs
        .map((job: Any) => {
          const active = ["queued", "running", "cancelling"].includes(job.status);
          const request = job.request || {};
          const stageOrder = RAG_STAGE_ORDER.filter(
            ([stage]) => stage !== "auto_grade" || request.auto_grade,
          );
          const stageIndex = stageOrder.findIndex(([stage]) => stage === job.stage);
          const generation = request.generation || {};
          const elapsed = humanDuration(jobElapsedSeconds(job));
          const totalLabel = job.finished_at
            ? trf("rag.total_time", "Total {time}", { time: elapsed })
            : trf("rag.elapsed_time", "Elapsed {time}", { time: elapsed });
          const sourceStore = state.stores.find(
            (store: Any) => store.name === job.source_collection,
          );
          const stageEvents = (job.events || []).filter(
            (event: Any) => event.stage === job.stage && event.timestamp,
          );
          const stageStart = stageEvents.length
            ? new Date(stageEvents[0].timestamp).getTime()
            : null;
          const stageElapsed = Number.isFinite(stageStart as Any)
            ? humanDuration(Math.max(0, (Date.now() - (stageStart as Any)) / 1000))
            : "—";
          const scheduler = job.provider === "openai"
            ? tr("rag.param.scheduler_uncapped", "scheduler uncapped")
            : param(
                "rag.param.scheduler",
                "scheduler {value}",
                `${job.scheduling?.active_when_started ?? state.health?.rag_concurrency?.ollama_active ?? "—"}/${job.scheduling?.limit ?? state.appConfig.ollama_rag_concurrency ?? 1}`,
              );
          const params = [
            param("rag.param.started_by", "started by {value}", job.owner || "—"),
            param("rag.param.provider", "provider {value}", job.provider || "—"),
            param("rag.param.generation", "generation {value}", job.model || "—"),
            param(
              "rag.param.embedding",
              "embedding {value}",
              sourceStore?.embedding_model || sourceStore?.embedding_provider || "—",
            ),
            param(
              "rag.param.reranker",
              "reranker model {value}",
              request.cross_encoder_model || request.reranker || "—",
            ),
            param("rag.param.languages", "languages {value}", (request.locales || []).join("+") || "—"),
            param("rag.param.retrieval", "retrieval {value}", (request.search_types || []).join("+") || "—"),
            param("rag.param.k", "k {value}", request.k ?? "—"),
            param("rag.param.fetch", "fetch {value}", request.fetch_k ?? "—"),
            param("rag.param.lambda", "λ {value}", request.lambda_mult ?? "—"),
            param("rag.param.rrf", "RRF {value}", request.rrf_k ?? "—"),
            param("rag.param.topn", "topN {value}", request.rerank_top_n ?? "—"),
            param(
              "rag.param.auto_grade",
              "auto-grade {value}",
              request.auto_grade ? tr("ui.on", "On") : tr("ui.off", "Off"),
            ),
            param("rag.param.num_ctx", "num_ctx {value}", generation.num_ctx ?? "—"),
            param("rag.param.num_predict", "num_predict {value}", generation.num_predict ?? "—"),
            scheduler,
            param("rag.param.stage_time", "stage time {value}", stageElapsed),
          ];
          const statusLabel = tr(`operations.status.${job.status}`, String(job.status || ""));
          return `<article class="rag-live-job">
        <div class="rag-live-job-head"><div><b>${esc(job.prompt || tr("rag.query", "RAG query"))}</b><span>${esc(job.source_collection || "")} · ${esc(job.model || job.provider || "")} · ${esc(totalLabel)}</span></div><span class="job-status ${esc(job.status)}">${esc(statusLabel)}</span></div>
        <div class="rag-live-params">${params.map((value) => `<span>${esc(value)}</span>`).join("")}</div>
        <div class="rag-stage-rail">${stageOrder
          .map(([_stage, key, fallback], index: Any) => {
            const done = job.status === "completed" || index < stageIndex;
            const current = active && index === stageIndex;
            const stageState = current
              ? job.stage_detail || tr("rag.stage.running", "Running…")
              : done
                ? tr("rag.stage.complete", "Complete")
                : tr("rag.stage.pending", "Pending");
            return `<div class="rag-stage-node ${done ? "done" : ""} ${current ? "current" : ""}"><i>${done ? "✓" : index + 1}</i><div><b>${esc(tr(key, fallback))}</b><span>${esc(stageState)}</span></div></div>`;
          })
          .join("")}</div>
        <div class="rag-live-detail">${job.status === "cancelling" || job.cancel_requested ? esc(tr("rag.cancellation_wait", "Cancellation requested · waiting for the current pipeline call to reach a safe checkpoint.")) : esc(job.stage_detail || job.fatal_error || tr("operations.status.queued", "Queued"))}</div>
        <div class="rag-live-footer"><div class="rag-live-timing"><span>${esc(totalLabel)}</span><span>${job.started_at ? esc(trf("operations.panel.started", "Started {when}", { when: formatTimestamp(job.started_at) })) : esc(tr("rag.not_started", "Not started"))}</span>${job.finished_at ? `<span>${esc(trf("operations.panel.finished", "Finished {when}", { when: formatTimestamp(job.finished_at) }))}</span>` : ""}</div><div class="tools"><button class="btn small" data-rag-job-details="${job.id}">${esc(tr("rag.details_timeline", "Details / timeline"))}</button>${job.status === "completed" ? `<button class="btn small primary" data-rag-job-result="${job.id}">${esc(tr("operations.panel.action_open_result", "Open result"))}</button>` : ""}${active ? (job.cancel_requested || job.status === "cancelling" ? `<button class="btn small" disabled>${esc(tr("operations.cancelling", "Cancelling…"))}</button>` : `<button class="btn small danger" data-rag-job-cancel="${job.id}">${esc(tr("operations.panel.action_cancel", "Cancel"))}</button>`) : `<button class="btn small danger" data-rag-job-remove="${job.id}">${esc(tr("operations.panel.action_remove", "Remove"))}</button>`}</div></div>
      </article>`;
        })
        .join("") || `<div class="llm-empty">${esc(tr("rag.empty", "No RAG jobs yet. Start one below."))}</div>`
    }</div>
  </section>`;
  }
  function wireRagProgressPanel() {
    const panel = document.querySelector("#ragProgressPanel");
    if (!panel) return;
    panel.querySelector("#ragRefreshJobs")?.addEventListener("click", () => refreshJobs());
    panel.querySelector("#ragClearFinished")?.addEventListener("click", clearFinishedRagJobs);
    panel
      .querySelectorAll("[data-rag-job-details]")
      .forEach(
        (button: Any) => (button.onclick = () => openJobDetails(button.dataset.ragJobDetails)),
      );
    panel
      .querySelectorAll("[data-rag-job-result]")
      .forEach(
        (button: Any) => (button.onclick = () => openJobResults(button.dataset.ragJobResult)),
      );
    panel
      .querySelectorAll("[data-rag-job-cancel]")
      .forEach(
        (button: Any) => (button.onclick = () => cancelBackgroundJob(button.dataset.ragJobCancel)),
      );
    panel
      .querySelectorAll("[data-rag-job-remove]")
      .forEach((button: Any) => (button.onclick = () => removeRagJob(button.dataset.ragJobRemove)));
  }
  function refreshRagProgressPanel() {
    const current = document.querySelector("#ragProgressPanel");
    if (!current) return;
    const holder = document.createElement("div");
    holder.innerHTML = ragProgressPanelHtml();
    const replacement = holder.firstElementChild;
    if (replacement) current.replaceWith(replacement);
    wireRagProgressPanel();
  }
  function renderCorpusBuildsHomeCard() {
    if (isResearcher()) return "";
    const builds = (state.jobs || []).filter((job: Any) => job.type === "pdf_corpus").slice(0, 4);
    const active = builds.filter((job: Any) =>
      ["queued", "running", "cancelling"].includes(job.status),
    ).length;
    return `<section class="card dashboard-corpus-builds" aria-label="${esc(tr("pdf_corpus.home_title", "Corpus builds"))}">
    <div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("pdf")}</span><b>${esc(tr("pdf_corpus.home_title", "Corpus builds"))}</b>${active ? `<span class="dashboard-corpus-active">${active} ${esc(tr("operations.active", "active"))}</span>` : ""}</div><button class="dashboard-text-link" id="dashCorpusBuilder">${esc(tr("pdf_corpus.open_builder", "Open Corpus Builder"))} →</button></div>
    <p class="dashboard-corpus-help">${esc(tr("pdf_corpus.home_help", "Recent PDF-to-corpus pipelines stay visible here even after you leave Corpus Builder."))}</p>
    <div class="dashboard-corpus-list">${
      builds.length
        ? builds
            .map((job: Any) => {
              const pct = Math.max(0, Math.min(100, Math.round(Number(job.progress || 0) * 100)));
              const status = job.raw_status || job.status || "unknown";
              return `<button type="button" class="dashboard-corpus-row" data-dashboard-corpus-build="${esc(job.id)}"><span class="dashboard-corpus-state ${esc(job.status || "")}" aria-hidden="true"></span><span class="dashboard-corpus-copy"><b>${esc(job.source_filename || tr("pdf_corpus.source_pdf", "Source PDF"))}</b><small>${esc(String(status).replaceAll("_", " "))} · ${esc(String(job.stage_detail || job.stage || ""))}</small></span><span class="dashboard-corpus-progress"><b>${pct}%</b><i><span style="width:${pct}%"></span></i></span></button>`;
            })
            .join("")
        : `<div class="dashboard-corpus-empty">${esc(tr("pdf_corpus.home_empty", "No corpus builds yet. Start with a source PDF in Corpus Builder."))}</div>`
    }</div>
  </section>`;
  }
  return {
    notifyOperationsChanged,
    operationsBridge,
    renderOperationsPanel,
    mountOperationsPanelHost,
    refreshOperationsPanelOnly,
    wireCorpusBuildsHomeCard,
    refreshCorpusBuildsHomeCardOnly,
    gradeRagResponse,
    removeRagJob,
    clearFinishedRagJobs,
    ragProgressPanelHtml,
    wireRagProgressPanel,
    refreshRagProgressPanel,
    renderCorpusBuildsHomeCard,
  };
}
