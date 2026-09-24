/* Copyright 2026 Aaron John Schlosser, PhD. */
import { isActiveJobStatus } from "./operationsDock";
import { formatDuration } from "./operationsPanel";
import { bindCopy } from "../i18n/bindCopy";

// Presentation of background jobs for the Operations panel: labels, facts, subtitles and progress text.
// Moved verbatim from the legacy runtime; the state it used to read is now passed in as dependencies.

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

interface Deps {
  tr: (key: string, fallback?: string) => string;
  trf: (key: string, fallbackOrValues?: string | Record<string, unknown>, values?: Record<string, unknown>) => string;
  getLocale: () => string;
  getStores: () => Loose[];
  providerProfiles: () => Loose[];
  providerDisplayName: (profile: Loose) => string;
}

export function createOperationPresenters(deps: Deps) {
  const { tr, trf } = bindCopy(deps.tr, deps.trf);
  const OPERATION_FACT_NAMES: Record<string, [string, string]> = {
    started_by: ["operations.fact.started_by", "Started by"],
    model: ["operations.fact.model", "Model"],
    fields: ["operations.fact.fields", "Fields"],
    current_record: ["operations.fact.current_record", "Current record"],
    pending_results: ["operations.fact.pending_results", "Pending results"],
    pending_changes: ["operations.fact.pending_changes", "Pending changes"],
    unprocessed_records: ["operations.fact.unprocessed_records", "Unprocessed records"],
    accepted: ["operations.fact.accepted", "Accepted"],
    rejected: ["operations.fact.rejected", "Rejected"],
    decision: ["operations.fact.decision", "Decision"],
    generation: ["operations.fact.generation", "Generation"],
    embedding: ["operations.fact.embedding", "Embedding"],
    reranker: ["operations.fact.reranker", "Reranker"],
    collection: ["operations.fact.collection", "Collection"],
    stage: ["operations.fact.stage", "Stage"],
    languages: ["operations.fact.languages", "Languages"],
    retrieval: ["operations.fact.retrieval", "Retrieval"],
    auto_grade: ["operations.fact.auto_grade", "Auto-grade"],
    operation: ["operations.fact.operation", "Operation"],
    provider: ["operations.fact.provider", "Provider"],
    max_concurrent: ["operations.fact.max_concurrent", "Max concurrent"],
    top_n: ["operations.fact.top_n", "Top N"],
    pdf: ["operations.fact.pdf", "PDF"],
    page: ["operations.fact.page", "Page"],
    cached_response: ["operations.fact.cached_response", "Cached response"],
    scope: ["operations.fact.scope", "Scope"],
    records: ["operations.fact.records", "Records"],
    committed: ["operations.fact.committed", "Committed"],
    language_mirrors: ["operations.fact.language_mirrors", "Language mirrors"],
    total_time: ["operations.fact.total_time", "Total time"],
    elapsed: ["operations.fact.elapsed", "Elapsed"],
  };
  function jobLabel(job: Loose) {
    if (job.type === "rag") return tr("operations.job.rag");
    if (job.type === "upsert") return tr("operations.job.upsert");
    if (job.type === "pdf_corpus") return tr("pdf_corpus.operation_label");
    if (job.type === "llm_tool") {
      const known: Record<string, string> = {
        pdf_clean_text: tr("operations.job.pdf_clean_text"),
        pdf_draft_record: tr("operations.job.pdf_draft_record"),
        pdf_link_record: tr("operations.job.pdf_link_record"),
        rag_grade: tr("operations.job.rag_grade"),
        rag_grade_batch: tr("operations.job.rag_grade_batch"),
        work_metadata: tr("works.populate_metadata_llm"),
      };
      return (
        job.label || known[job.tool || job.mode] || tr("operations.job.llm_tool")
      );
    }
    return job.mode === "auto"
      ? tr("operations.job.auto")
      : tr("operations.job.review");
  }
  function jobProviderSummary(job: Loose) {
    if (job.type === "upsert")
      return [job.label, job.store_name || "collection"].filter(Boolean).join(" · ");
    const profile = job.provider_profile_id
      ? deps.providerProfiles().find((item) => item.id === job.provider_profile_id)
      : null;
    const providerName = profile ? deps.providerDisplayName(profile) : job.provider || "";
    const model = job.model || "";
    return [providerName, model].filter(Boolean).join(" · ");
  }
  function jobElapsedSeconds(job: Loose) {
    const start = job.started_at ? new Date(job.started_at).getTime() : null;
    if (!Number.isFinite(start)) return 0;
    const end = job.finished_at ? new Date(job.finished_at).getTime() : Date.now();
    return Math.max(0, (end - (start as number)) / 1000);
  }
  function humanDuration(seconds: number) {
    return formatDuration(seconds, deps.getLocale());
  }
  function fact(id: string) {
    const [key, fallback] = OPERATION_FACT_NAMES[id];
    return tr(key, fallback);
  }
  function decisionLabel(state: unknown) {
    const id = String(state || "pending");
    return tr(`operations.decision.${id}`, id.replaceAll("_", " "));
  }
  function operationIcon(job: Loose) {
    if (job.type === "pdf_corpus") return "pdf";
    if (job.type === "upsert") return "database";
    if (job.type === "rag") return "spark";
    if (job.type === "llm_tool") {
      const kind = String(job.tool || job.mode || job.label || "").toLowerCase();
      if (kind.includes("policy")) return "lock";
      if (kind.includes("language")) return "language";
      if (kind.includes("pdf")) return "pdf";
      return "gear";
    }
    return "edit";
  }
  function operationResultKind(job: Loose) {
    const active = isActiveJobStatus(job.status);
    if (job.type === "llm" && Number(job.pending_result_count || 0) > 0)
      return active ? "review-partial" : "review";
    if (["rag", "llm_tool"].includes(job.type) && job.status === "completed") return "result";
    if (job.type === "pdf_corpus" && ["completed", "blocked"].includes(job.status)) return "build";
    return null;
  }
  function operationSubtitle(job: Loose) {
    if (job.status === "cancelling" || job.cancel_requested)
      return tr("operations.sub.cancelling");
    if (job.type === "rag")
      return String(job.stage_detail || job.stage || tr("operations.sub.queued"));
    if (job.type === "upsert")
      return `${job.store_name || tr("operations.sub.collection")} · ${job.completed}/${job.total} ${tr("operations.sub.committed")}${Object.keys(job.mirrored || {}).length ? ` · ${tr("operations.sub.mirrors_active")}` : ""}`;
    if (job.type === "pdf_corpus")
      return `${job.source_filename || tr("pdf_corpus.source_pdf")} · ${job.stage_detail || job.stage || job.raw_status || tr("operations.sub.queued")}${job.unresolved_regions ? ` · ${Number(job.unresolved_regions).toLocaleString()} ${tr("pdf_corpus.unresolved_regions")}` : ""}`;
    // Provider and model appear in the facts, and the label is the row title: say only what is new.
    if (job.type === "llm_tool") {
      const detail = String(job.stage_detail || "");
      return detail && detail !== jobLabel(job) ? detail : "";
    }
    return `${job.completed}/${job.total} ${tr("operations.sub.records")}${job.current_record_id ? ` · ${tr("operations.sub.current")} ${job.current_record_id}` : ""}${job.failed ? ` · ${job.failed} ${tr("operations.sub.failed")}` : ""}`;
  }
  function jobProgressText(job: Loose, style?: string) {
    const total = Number(job.total || 0),
      done = Number(job.completed || 0),
      pct = Math.round(total ? (done / total) * 100 : 0);
    // A PDF corpus build reports a synthetic count (source blocks x weighted
    // stage progress), not a real tally, so show only the honest percentage.
    if (job.type === "pdf_corpus") {
      if (job.status === "completed")
        return tr("operations.progress_build_complete");
      return trf("operations.progress_overall", { percent: pct });
    }
    return style === "of"
      ? trf("operations.progress_of", {
          done: done.toLocaleString(),
          total: total.toLocaleString(),
          percent: pct,
        })
      : `${done}/${total} (${pct}%)`;
  }
  function operationDetailPairs(job: Loose) {
    const request = job.request || {};
    const pairs = [];
    if (job.owner) pairs.push([fact("started_by"), job.owner]);
    if (job.type === "llm") {
      pairs.push(
        [fact("model"), job.model || job.provider || "—"],
        [fact("fields"), (job.fields || []).join(", ") || "—"],
        [fact("current_record"), job.current_record_id || "—"],
        [fact("pending_results"), job.pending_result_count ?? 0],
        [fact("pending_changes"), job.pending_change_count ?? 0],
        [
          fact("unprocessed_records"),
          job.remaining_record_count ?? Math.max(0, (job.total || 0) - (job.completed || 0)),
        ],
        [
          fact("accepted"),
          trf("operations.fact.result_field_counts", {
            results: job.accepted_results || 0,
            fields: job.accepted_fields || 0,
          }),
        ],
        [
          fact("rejected"),
          trf("operations.fact.result_field_counts", {
            results: job.rejected_results || 0,
            fields: job.rejected_fields || 0,
          }),
        ],
        [fact("decision"), decisionLabel(job.resolution_state || "pending")],
      );
      if (request.generation && Object.keys(request.generation).length)
        pairs.push([fact("generation"), JSON.stringify(request.generation)]);
    } else if (job.type === "rag") {
      const sourceStore = deps.getStores().find((store) => store.name === job.source_collection);
      pairs.push(
        [fact("generation"), job.model || job.provider || "—"],
        [fact("embedding"), sourceStore?.embedding_model || sourceStore?.embedding_provider || "—"],
        [fact("reranker"), request.cross_encoder_model || request.reranker || "—"],
        [fact("collection"), job.source_collection || "—"],
        [fact("stage"), job.stage || "—"],
        [fact("languages"), (request.locales || []).join(", ") || "—"],
        [fact("retrieval"), (request.search_types || []).join(" + ") || "—"],
        ["k / fetch_k", `${request.k ?? "—"} / ${request.fetch_k ?? "—"}`],
        ["RRF k", request.rrf_k ?? "—"],
        [fact("top_n"), request.rerank_top_n ?? "—"],
      );
      if (request.auto_grade) {
        const gradeProfile = request.auto_grade_provider_profile_id
          ? deps
              .providerProfiles()
              .find((item) => item.id === request.auto_grade_provider_profile_id)
          : null;
        pairs.push([
          fact("auto_grade"),
          `${gradeProfile ? deps.providerDisplayName(gradeProfile) : request.auto_grade_provider || job.provider || "grader"} · ${request.auto_grade_model || job.model || "model"}`,
        ]);
      }
    } else if (job.type === "pdf_corpus") {
      pairs.push(
        [tr("pdf_corpus.source_pdf"), job.source_filename || "—"],
        [tr("pdf_corpus.stage"), job.stage || "—"],
        [tr("pdf_corpus.records"), job.record_count ?? 0],
        [tr("pdf_corpus.need_review"), job.review_count ?? 0],
        [tr("pdf_corpus.unresolved_regions"), job.unresolved_regions ?? 0],
        [
          tr("pdf_corpus.concurrent_requests"),
          job.max_concurrent_requests ?? 1,
        ],
      );
    } else if (job.type === "llm_tool") {
      pairs.push(
        [fact("operation"), job.label || job.tool || job.mode || "LLM tool"],
        [fact("provider"), job.provider || "—"],
        [fact("model"), job.model || "—"],
        [fact("stage"), job.stage || "—"],
        [fact("max_concurrent"), job.max_concurrent_requests ?? "—"],
      );
      if (request.pdf_file)
        pairs.push([fact("pdf"), request.pdf_file], [fact("page"), request.pdf_page ?? "—"]);
      if (request.response_record_id)
        pairs.push([fact("cached_response"), request.response_record_id]);
    } else if (job.type === "upsert") {
      pairs.push(
        [fact("collection"), job.store_name || "—"],
        [fact("scope"), job.label || request.label || tr("operations.sub.records")],
        [fact("records"), job.total ?? 0],
        [fact("committed"), job.completed ?? 0],
        [fact("current_record"), job.current_record_id || "—"],
      );
      const mirrors = Object.entries(job.mirrored || {})
        .map(([name, count]) => `${name}: ${count}`)
        .join(" · ");
      if (mirrors) pairs.push([fact("language_mirrors"), mirrors]);
    }
    pairs.push([
      fact(job.finished_at ? "total_time" : "elapsed"),
      humanDuration(jobElapsedSeconds(job)),
    ]);
    return pairs;
  }
  function operationViewModel(job: Loose) {
    // Facts already shown elsewhere in the row (owner, operation name, stage) are left out.
    const skip = new Set([
      fact("started_by"),
      fact("operation"),
      fact("stage"),
      fact("total_time"),
      tr("pdf_corpus.stage"),
    ]);
    const facts = operationDetailPairs(job)
      .filter(
        ([name, value]) =>
          !skip.has(String(name)) &&
          String(value ?? "").trim() !== "" &&
          String(value).trim() !== "—",
      )
      .slice(0, 4)
      .map(([name, value]) => ({ name: String(name), value: String(value) }));
    const failure =
      job.status === "failed"
        ? String(
            job.fatal_error || job.error_message || job.error?.message || job.stage_detail || "",
          )
        : job.status === "blocked"
          ? String(job.stage_detail || "")
          : "";
    const kind = operationResultKind(job);
    return {
      id: String(job.id),
      type: String(job.type || "llm"),
      status: String(job.status || ""),
      label: jobLabel(job),
      icon: operationIcon(job),
      subtitle: operationSubtitle(job),
      facts,
      owner: String(job.owner || ""),
      createdAt: job.created_at || null,
      startedAt: job.started_at || null,
      finishedAt: job.finished_at || null,
      total: Number(job.total || 0),
      completed: Number(job.completed || 0),
      progressLabel: jobProgressText(job, "of"),
      cancelRequested: Boolean(job.cancel_requested),
      error: failure,
      result: kind ? { kind } : null,
    };
  }
  return {
    jobLabel,
    jobProviderSummary,
    jobElapsedSeconds,
    humanDuration,
    fact,
    decisionLabel,
    operationIcon,
    operationResultKind,
    operationSubtitle,
    jobProgressText,
    operationDetailPairs,
    operationViewModel,
  };
}
