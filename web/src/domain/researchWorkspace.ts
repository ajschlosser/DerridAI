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

// The Research workspace and the Response Library: the workspace snapshot, configuration, evidence, running and grading
// research, and the cached-answer page. Moved verbatim from the legacy runtime; the runtime's state object and helpers are
// passed in as dependencies.
import { createResponseFaq } from "./responseFaq";
import { providerRequestConfig } from "./providerRequest";
import { createGetResearchJob } from "./researchJobLookup";
import { cloneAuditValue } from "./recordValues";
import {
  normalizedResearchConfig,
  researchEvidenceForUi,
  researchJobForUi,
  researchProfileForUi,
  sanitizeResearchGeneration,
} from "./researchPayloads";
import { bindCopy } from "../i18n/bindCopy";
import { englishDefault } from "../i18n/englishDefault";
import { toast } from "../composables/notifications";

type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "api"
  | "canAccessPage"
  | "cancelBackgroundJob"
  | "clearSelectedEvidence"
  | "gradeRagResponse"
  | "hasCapability"
  | "hasCorpusDb"
  | "isResearcher"
  | "navigateTo"
  | "persistPrefs"
  | "providerDisplayName"
  | "providerProfile"
  | "providerProfiles"
  | "pruneClientJobState"
  | "recordStores"
  | "refreshJobs"
  | "refreshStores"
  | "selectedEvidenceEntries"
  | "selectedEvidencePayload"
  | "setEvidence"
  | "shellRefreshHook"
  | "startJobPolling"
  | "syncJobProgressToasts"
  | "tr"
  | "trf"
  | "uid";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createResearchWorkspace(deps: Deps) {
  const {
    state,
    api,
    canAccessPage,
    cancelBackgroundJob,
    clearSelectedEvidence,
    gradeRagResponse,
    hasCapability,
    hasCorpusDb,
    isResearcher,
    navigateTo,
    persistPrefs,
    providerDisplayName,
    providerProfile,
    providerProfiles,
    pruneClientJobState,
    recordStores,
    refreshJobs,
    refreshStores,
    selectedEvidenceEntries,
    selectedEvidencePayload,
    setEvidence,
    shellRefreshHook,
    startJobPolling,
    syncJobProgressToasts,
    trf,
    uid,
  } = deps;
  const { tr } = bindCopy(deps.tr, (key, fallback, values = {}) =>
    Object.entries(values).reduce(
      (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
      fallback || englishDefault(key) || key,
    ),
  );
  function researchConfigForUi() {
    return cloneAuditValue(state.ragConfig || {});
  }
  async function getResearchWorkspaceSnapshot({
    refresh = false,
    includeJobs = true,
    includePipelines = true,
    strictCollections = false,
  } = {}) {
    if (refresh) {
      try {
        await refreshStores();
      } catch (error) {
        if (strictCollections) throw error;
        console.warn("Could not refresh Research collections", error);
      }
      if (includeJobs && (hasCapability("rag.jobs.own") || !isResearcher()))
        await refreshJobs({ rerender: false });
    }
    const corpus = recordStores();
    const usable = corpus.filter((store: Any) => Number(store.count || 0) > 0);
    const evidence = selectedEvidenceEntries()
      .map(researchEvidenceForUi)
      .filter((item: Any) => item !== null);
    if (!evidence.length) state.ragConfig.skip_retrieval = false;
    if (evidence.length && !hasCorpusDb()) state.ragConfig.skip_retrieval = true;
    if (
      !state.ragConfig.source_collection ||
      !corpus.some((store: Any) => store.name === state.ragConfig.source_collection)
    ) {
      state.ragConfig.source_collection =
        (
          usable.find((store: Any) => store.collection_role === "primary") ||
          usable[0] ||
          corpus[0] ||
          {}
        ).name || "";
    }
    const profiles = providerProfiles();
    if (
      profiles.length &&
      !profiles.some((profile: Any) => profile.id === state.ragConfig.provider_profile_id)
    ) {
      state.ragConfig.provider_profile_id =
        (
          profiles.find(
            (profile: Any) => profile.id === state.appConfig.default_provider_profile,
          ) || profiles[0]
        )?.id || "";
    }
    if (
      profiles.length &&
      !profiles.some(
        (profile: Any) => profile.id === state.ragConfig.auto_grade_provider_profile_id,
      )
    ) {
      state.ragConfig.auto_grade_provider_profile_id =
        (
          profiles.find((profile: Any) => profile.id !== state.ragConfig.provider_profile_id) ||
          profiles[0]
        )?.id || "";
    }

    let pipelineVisibility: Loose = {
      assignment: null,
      override_allowed: false,
      pipelines: [],
      strategies: [],
    };
    try {
      if (includePipelines)
        pipelineVisibility = await api("/api/system/pipelines/research-options");
      const configuredId = String(state.ragConfig.pipeline_id || "").trim();
      const configuredVersion = Number(state.ragConfig.pipeline_version || 0);
      if (
        includePipelines &&
        configuredId &&
        !((pipelineVisibility.pipelines || []) as Loose[]).some(
          (pipeline: Loose) =>
            String(pipeline.pipeline_id || "") === configuredId &&
            Number(pipeline.version || 0) === configuredVersion,
        )
      ) {
        // Remove an override that is no longer visible or authorized. Keeping
        // it in browser preferences would make a later Research run fail for a
        // pipeline the user can no longer select.
        state.ragConfig.pipeline_id = "";
        state.ragConfig.pipeline_version = null;
      }
    } catch (error) {
      // Research remains available with server-side assignment resolution even
      // if the visibility endpoint is temporarily unavailable.
      console.warn("Could not load Research pipeline visibility", error);
    }

    persistPrefs();
    return {
      config: researchConfigForUi(),
      stores: corpus.map((store: Any) => ({
        name: store.name,
        count: Number(store.count || 0),
        collection_role: store.collection_role || "general",
        embedding_model: store.embedding_model || store.metadata?.embedding_model || "",
        filter_fields: Array.isArray(store.filter_fields) ? store.filter_fields.map(String) : [],
        schema_id: String(store.schema_id || store.metadata?.schema_id || ""),
        source_works: Array.isArray(store.source_works)
          ? store.source_works.map(String).filter(Boolean)
          : [],
      })),
      profiles: profiles.map(researchProfileForUi).filter(Boolean),
      selected_evidence: evidence,
      jobs:
        !isResearcher() || hasCapability("rag.jobs.own")
          ? (state.jobs || [])
              .filter((job: Any) => job.type === "rag")
              .map(researchJobForUi)
              .filter(Boolean)
          : [],
      history: cloneAuditValue(state.ragConfig.history || []),
      pipeline_assignment:
        pipelineVisibility.assignment && typeof pipelineVisibility.assignment === "object"
          ? cloneAuditValue(pipelineVisibility.assignment)
          : null,
      pipeline_options: Array.isArray(pipelineVisibility.pipelines)
        ? cloneAuditValue(pipelineVisibility.pipelines)
        : [],
      pipeline_strategies: Array.isArray(pipelineVisibility.strategies)
        ? cloneAuditValue(pipelineVisibility.strategies)
        : [],
      pipeline_override_allowed: Boolean(pipelineVisibility.override_allowed),
      can_run: hasCapability("rag.run"),
      can_select_evidence: hasCapability("evidence.select"),
      can_manage_jobs: !isResearcher() || hasCapability("rag.jobs.own"),
      is_researcher: isResearcher(),
    };
  }
  function updateResearchConfig(patch = {}) {
    const allowed = new Set([
      "pipeline_id",
      "pipeline_version",
      "source_collection",
      "work_filter",
      "locales",
      "search_types",
      "k",
      "fetch_k",
      "automatic_sizing",
      "lambda_mult",
      "rrf_k",
      "rerank_top_n",
      "reranker",
      "cross_encoder_model",
      "query_decomposition",
      "query_decomposition_num_predict",
      "response_language",
      "evidence_record_char_limit",
      "evidence_total_char_limit",
      "bind_citations",
      "include_works_cited",
      "prompt_metadata",
      "auto_grade",
      "auto_grade_provider_profile_id",
      "provider_profile_id",
      "skip_retrieval",
      "use_prior_response_memory",
      "use_prior_claim_memory",
      "memory_profile_id",
      "prompt",
      "instructions",
    ]);
    for (const [key, value] of Object.entries(patch || {}))
      if (allowed.has(key)) state.ragConfig[key] = cloneAuditValue(value);
    if (!selectedEvidenceEntries().length) state.ragConfig.skip_retrieval = false;
    persistPrefs();
    shellRefreshHook?.();
    return researchConfigForUi();
  }
  function removeResearchEvidence(key: Any) {
    if (!hasCapability("evidence.select")) throw new Error(tr("permissions.evidence_denied"));
    setEvidence(String(key || ""), null, false);
    if (!selectedEvidenceEntries().length) state.ragConfig.skip_retrieval = false;
    persistPrefs();
    return selectedEvidenceEntries()
      .map(researchEvidenceForUi)
      .filter((item: Any) => item !== null);
  }
  function clearResearchEvidence() {
    if (!hasCapability("evidence.select")) throw new Error(tr("permissions.evidence_denied"));
    clearSelectedEvidence();
    state.ragConfig.skip_retrieval = false;
    persistPrefs();
    return [];
  }
  async function discoverResearchModels(profileId: Any) {
    const profile = providerProfile(profileId);
    if (!profile) return [];
    if (isResearcher()) return profile.model ? [String(profile.model)] : [];
    try {
      const status = await api("/api/llm/status", {
        method: "POST",
        body: JSON.stringify({
          provider: profile.type || "ollama",
          base_url: profile.base_url || null,
          api_key: profile.type === "openai" ? profile.api_key || "" : null,
        }),
      });
      state.providerStatuses[profile.id] = status;
      return (status.models || []).map((item: Any) => String(item.name || "")).filter(Boolean);
    } catch (error) {
      console.warn("Research model discovery failed", error);
      return profile.model ? [String(profile.model)] : [];
    }
  }
  async function refreshResearchJobs() {
    if (isResearcher() && !hasCapability("rag.jobs.own")) return [];
    await refreshJobs({ rerender: false });
    return (state.jobs || [])
      .filter((job: Any) => job.type === "rag")
      .map(researchJobForUi)
      .filter(Boolean);
  }
  const getResearchJob = createGetResearchJob({ api, state });
  async function cancelResearchJob(jobId: Any) {
    if (isResearcher() && !hasCapability("rag.jobs.own"))
      throw new Error("Your role cannot manage Research jobs.");
    const job = await cancelBackgroundJob(jobId, { refresh: false });
    return researchJobForUi(job);
  }
  async function deleteResearchJob(jobId: Any) {
    if (isResearcher() && !hasCapability("rag.jobs.own"))
      throw new Error("Your role cannot manage Research jobs.");
    await api(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" });
    pruneClientJobState(jobId);
    persistPrefs();
    shellRefreshHook?.();
    return true;
  }
  function generationFromProfile(profile: Any) {
    const cfg = providerRequestConfig(profile, { textReview: true });
    return cloneAuditValue(cfg?.ollama || {});
  }
  async function startResearchRun(input: Loose = {}) {
    if (!hasCapability("rag.run")) throw new Error(tr("permissions.rag_denied"));
    // Research page controls are per-run overrides. Settings owns the
    // persistent defaults, so starting a run must not rewrite ragConfig.
    const cfg: Loose = normalizedResearchConfig({
      ...researchConfigForUi(),
      ...(input.config || {}),
    });
    const prompt = String(input.prompt ?? cfg.prompt ?? "").trim();
    const instructions = String(input.instructions ?? cfg.instructions ?? "").trim();
    if (!prompt) throw new Error("Enter a research question.");
    const selected = selectedEvidenceEntries();
    const skipRetrieval = Boolean(input.skip_retrieval ?? cfg.skip_retrieval);
    if (skipRetrieval && !selected.length)
      throw new Error("Select at least one evidence record before using evidence-only mode.");
    if (!skipRetrieval && !cfg.source_collection) throw new Error("Select a corpus database.");
    if (!skipRetrieval && !(cfg.locales || []).length)
      throw new Error("Select at least one document language.");
    if (!skipRetrieval && !(cfg.search_types || []).length)
      throw new Error("Select at least one retrieval route.");
    if (!skipRetrieval) {
      const store = recordStores().find((item: Any) => item.name === cfg.source_collection);
      if (!store)
        throw new Error(
          "The selected corpus database is no longer available. Choose an existing database before running Research.",
        );
      if (Number(store.count || 0) <= 0)
        throw new Error(
          "The selected corpus database is empty. Add records before running Research.",
        );
    }
    if (selected.length > 500)
      throw new Error("Research supports at most 500 selected evidence records in one run.");
    const selectedPayload = selectedEvidencePayload();
    if (skipRetrieval && selectedPayload.length !== selected.length)
      throw new Error(
        "One or more selected evidence records are no longer available. Remove the stale selection and try again.",
      );

    const profileId = String(
      input.provider_profile_id ||
        cfg.provider_profile_id ||
        state.appConfig.default_provider_profile ||
        "",
    );
    const profile = providerProfile(profileId);
    if (!profile) throw new Error("No LLM profile is available for Research.");
    const provider = ["ollama", "openai"].includes(String(profile.type || ""))
      ? String(profile.type)
      : "";
    if (!provider)
      throw new Error(
        "The selected LLM profile uses an unsupported provider. Update the profile before running Research.",
      );
    const defaultModel =
      provider === "openai" && profile.model_mode === "auto" ? "auto" : String(profile.model || "");
    const model = String(input.model || defaultModel).trim();
    if (!model) throw new Error("Select a generation model.");

    const baseGeneration = generationFromProfile(profile) as Loose;
    const generation = sanitizeResearchGeneration({
      ...baseGeneration,
      ...(input.generation || {}),
    });

    const gradeProfile = cfg.auto_grade
      ? providerProfile(cfg.auto_grade_provider_profile_id || profile.id)
      : null;
    if (cfg.auto_grade && !gradeProfile)
      throw new Error(
        "The selected auto-grade LLM profile is no longer available. Choose another grader or turn off auto-grading.",
      );
    if (gradeProfile && !["ollama", "openai"].includes(String(gradeProfile.type || "")))
      throw new Error("The selected auto-grade profile uses an unsupported provider.");
    const gradeConfig = gradeProfile
      ? providerRequestConfig(gradeProfile, { textReview: true })
      : null;
    // Draft text remains convenient browser state; execution choices stay
    // local to this run and are captured on the request below.
    state.ragConfig.prompt = prompt;
    state.ragConfig.instructions = instructions;
    rememberRagPrompt(prompt, instructions, {
      source_collection: cfg.source_collection,
      provider,
      model,
    });
    persistPrefs();

    const job = await api("/api/jobs/rag", {
      method: "POST",
      body: JSON.stringify({
        prompt,
        instructions: instructions || null,
        pipeline_id: cfg.pipeline_id || null,
        pipeline_version: cfg.pipeline_version || null,
        source_collection: cfg.source_collection || "",
        work_filter: cfg.work_filter,
        selected_evidence: selectedPayload,
        skip_retrieval: skipRetrieval,
        use_prior_response_memory: Boolean(cfg.use_prior_response_memory),
        use_prior_claim_memory: Boolean(cfg.use_prior_claim_memory),
        memory_profile_id: cfg.memory_profile_id || null,
        locales: cfg.locales,
        search_types: cfg.search_types,
        k: cfg.k,
        fetch_k: cfg.fetch_k,
        automatic_sizing: Boolean(cfg.automatic_sizing),
        lambda_mult: cfg.lambda_mult,
        rrf_k: cfg.rrf_k,
        rerank_top_n: cfg.rerank_top_n,
        reranker: cfg.reranker,
        cross_encoder_model: cfg.cross_encoder_model,
        query_decomposition: cfg.query_decomposition,
        query_decomposition_num_predict: cfg.query_decomposition_num_predict,
        response_language: cfg.response_language,
        evidence_record_char_limit: cfg.evidence_record_char_limit,
        evidence_total_char_limit: cfg.evidence_total_char_limit,
        provider,
        model,
        base_url: isResearcher() ? null : profile.base_url || null,
        api_key: isResearcher() ? null : provider === "openai" ? profile.api_key || "" : null,
        provider_profile_id: profile.id,
        max_concurrent_requests: Math.max(
          1,
          Math.min(
            64,
            Number(profile.max_concurrent_requests ?? (provider === "ollama" ? 1 : 32)) || 1,
          ),
        ),
        generation,
        ollama_concurrency_limit:
          provider === "ollama"
            ? Math.max(
                1,
                Math.min(
                  32,
                  Number(
                    profile.max_concurrent_requests ?? state.appConfig.ollama_rag_concurrency ?? 1,
                  ) || 1,
                ),
              )
            : null,
        bind_citations: Boolean(cfg.bind_citations),
        include_works_cited: Boolean(cfg.include_works_cited),
        prompt_metadata: cfg.prompt_metadata,
        auto_grade: Boolean(cfg.auto_grade),
        auto_grade_provider: gradeConfig?.provider || null,
        auto_grade_model: gradeConfig?.model || null,
        auto_grade_base_url: isResearcher() ? null : gradeConfig?.base_url || null,
        auto_grade_api_key: isResearcher() ? null : gradeConfig?.api_key || null,
        auto_grade_provider_profile_id: gradeConfig?.provider_profile_id || null,
        auto_grade_generation: gradeConfig?.ollama
          ? sanitizeResearchGeneration(gradeConfig.ollama)
          : null,
      }),
    });
    state.jobs = [job, ...state.jobs.filter((existing: Any) => existing.id !== job.id)];
    rememberRagRun(job);
    persistPrefs();
    syncJobProgressToasts();
    startJobPolling();
    shellRefreshHook?.();
    toast(
      trf("runtime.toast.research_started", {
        provider: providerDisplayName(profile),
        model,
      }),
      { tone: "success" },
    );
    return researchJobForUi(job);
  }
  async function gradeResearchJob(jobId: Any) {
    const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
    const result = job?.result;
    if (!result?.answer) throw new Error("This Research run has no completed answer to grade.");
    return gradeRagResponse({
      question: result.prompt || job.prompt || "",
      answer: result.answer || "",
      evidence: Array.isArray(result.evidence) ? result.evidence : [],
      responseRecordId: result.response_cache?.record_id || null,
      generationProvider: result.provider || job.provider || null,
      generationModel: result.model || job.model || null,
    });
  }
  function prepareResearchRerun(job: Any) {
    const request = job?.request || job?.result?.rag_request || {};
    if (!request || typeof request !== "object") return researchConfigForUi();
    const keys = [
      "pipeline_id",
      "pipeline_version",
      "source_collection",
      "work_filter",
      "locales",
      "search_types",
      "k",
      "fetch_k",
      "automatic_sizing",
      "lambda_mult",
      "rrf_k",
      "rerank_top_n",
      "reranker",
      "cross_encoder_model",
      "query_decomposition",
      "query_decomposition_num_predict",
      "response_language",
      "evidence_record_char_limit",
      "evidence_total_char_limit",
      "bind_citations",
      "include_works_cited",
      "prompt_metadata",
      "auto_grade",
      "auto_grade_provider_profile_id",
      "provider_profile_id",
      "skip_retrieval",
      "use_prior_response_memory",
      "use_prior_claim_memory",
      "memory_profile_id",
    ];
    const patch = Object.fromEntries(
      keys.filter((key) => request[key] !== undefined).map((key) => [key, request[key]]),
    );
    patch.prompt = request.prompt || job?.prompt || "";
    patch.instructions = request.instructions || "";
    return normalizedResearchConfig({
      ...researchConfigForUi(),
      ...patch,
    });
  }
  const { getResponseFaqPage, gradeResponseFaqRecord, rerunResponseFaqRecord } = createResponseFaq({
    api,
    canAccessPage,
    tr,
    gradeRagResponse,
    prepareRagRerun: (request) => prepareRagRerun(request),
  });
  function rememberRagPrompt(prompt: Any, instructions: Any, extra: Loose = {}) {
    const question = String(prompt || "").trim();
    const guidance = String(instructions || "").trim();
    if (!question && !guidance) return;
    const history = Array.isArray(state.ragConfig.history) ? state.ragConfig.history : [];
    const existing = history.findIndex(
      (item: Any) =>
        String(item.prompt || "").trim() === question &&
        String(item.instructions || "").trim() === guidance,
    );
    if (existing >= 0) history.splice(existing, 1);
    history.unshift({
      id: uid(),
      prompt: question,
      instructions: guidance,
      timestamp: new Date().toISOString(),
      source_collection: extra.source_collection || state.ragConfig.source_collection || "",
      provider: extra.provider || state.appConfig.chat_provider || "ollama",
      model: extra.model || "",
    });
    state.ragConfig.history = history.slice(0, 100);
  }
  function rememberRagRun(job: Any) {
    if (!job?.id) return;
    const history = Array.isArray(state.ragConfig.run_history) ? state.ragConfig.run_history : [];
    const existing = history.findIndex((item: Any) => item.job_id === job.id);
    if (existing >= 0) history.splice(existing, 1);
    history.unshift({
      job_id: job.id,
      timestamp: job.created_at || new Date().toISOString(),
      provider: job.provider === "openai" ? "openai" : "ollama",
      model: job.model || "",
      source_collection: job.source_collection || state.ragConfig.source_collection || "",
      prompt: job.prompt || state.ragConfig.prompt || "",
    });
    state.ragConfig.run_history = history.slice(0, 250);
  }
  function prepareRagRerun(request: Loose = {}) {
    const cfg = state.ragConfig;
    const source = request.source_collection;
    if (source) cfg.source_collection = source;
    if (Array.isArray(request.work_filter))
      cfg.work_filter = cloneAuditValue(request.work_filter);
    if (Array.isArray(request.locales) && request.locales.length)
      cfg.locales = [...request.locales];
    if (Array.isArray(request.search_types) && request.search_types.length)
      cfg.search_types = [...request.search_types];
    for (const key of [
      "pipeline_id",
      "pipeline_version",
      "k",
      "fetch_k",
      "automatic_sizing",
      "lambda_mult",
      "rrf_k",
      "rerank_top_n",
      "reranker",
      "cross_encoder_model",
      "query_decomposition",
      "query_decomposition_num_predict",
      "response_language",
      "evidence_record_char_limit",
      "evidence_total_char_limit",
      "bind_citations",
      "include_works_cited",
      "prompt_metadata",
      "auto_grade",
    ]) {
      if (request[key] !== undefined) cfg[key] = cloneAuditValue(request[key]);
    }
    cfg.prompt = String(request.prompt || cfg.prompt || "");
    cfg.instructions = String(request.instructions || cfg.instructions || "");

    const providerType = request.provider;
    const baseUrl = request.base_url;
    const model = request.model;
    let profile = providerProfiles().find(
      (item: Any) =>
        (!providerType || item.type === providerType) &&
        (!baseUrl || item.base_url === baseUrl) &&
        (!model || item.model === model || (model === "auto" && item.model_mode === "auto")),
    );
    if (!profile && providerType) {
      profile = {
        id: `rerun-${providerType}-${uid()}`,
        name: `Rerun · ${providerType === "ollama" ? "Ollama" : "OpenAI-compatible"}`,
        type: providerType,
        base_url:
          baseUrl ||
          (providerType === "ollama"
            ? "http://host.docker.internal:11434"
            : "http://host.docker.internal:3001/v1"),
        model: model || (providerType === "ollama" ? "gemma4:e2b" : "auto"),
        model_mode: providerType === "openai" && model === "auto" ? "auto" : "manual",
        model_kind: "any",
        api_key: "",
        max_concurrent_requests: Math.max(
          1,
          Math.min(
            64,
            Number(request.max_concurrent_requests ?? (providerType === "ollama" ? 1 : 32)) || 1,
          ),
        ),
        num_predict: request.generation?.num_predict ?? 4096,
        num_ctx: request.generation?.num_ctx ?? 16384,
        think: String(request.generation?.think ?? "false"),
        temperature: request.generation?.temperature ?? 0,
        top_k: request.generation?.top_k ?? 0,
        top_p: request.generation?.top_p ?? 1,
        min_p: request.generation?.min_p ?? "",
        repeat_penalty: request.generation?.repeat_penalty ?? 1.1,
        seed: request.generation?.seed ?? "",
        keep_alive: request.generation?.keep_alive || "10m",
        extra_options: JSON.stringify(request.generation?.extra_options || {}),
      };
      state.appConfig.provider_profiles.push(profile);
    }
    if (profile) {
      cfg.provider_profile_id = profile.id;
      if (request.generation) {
        const generation = request.generation;
        for (const key of [
          "num_ctx",
          "num_predict",
          "temperature",
          "top_k",
          "top_p",
          "min_p",
          "repeat_penalty",
          "seed",
          "mirostat",
          "mirostat_eta",
          "mirostat_tau",
          "keep_alive",
        ]) {
          if (generation[key] !== undefined && generation[key] !== null)
            profile[key] = generation[key];
        }
        if (generation.think !== undefined && generation.think !== null)
          profile.think = String(generation.think);
        if (generation.extra_options)
          profile.extra_options = JSON.stringify(generation.extra_options);
      }
    }
    if (
      request.auto_grade_provider_profile_id &&
      providerProfiles().some((item: Any) => item.id === request.auto_grade_provider_profile_id)
    ) {
      cfg.auto_grade_provider_profile_id = request.auto_grade_provider_profile_id;
    } else if (request.auto_grade_provider) {
      const gradeProfile = providerProfiles().find(
        (item: Any) =>
          item.type === request.auto_grade_provider &&
          (!request.auto_grade_model ||
            item.model === request.auto_grade_model ||
            (request.auto_grade_model === "auto" && item.model_mode === "auto")),
      );
      if (gradeProfile) cfg.auto_grade_provider_profile_id = gradeProfile.id;
    }
    persistPrefs();
    navigateTo("rag");
  }
  return {
    researchConfigForUi,
    getResearchWorkspaceSnapshot,
    updateResearchConfig,
    removeResearchEvidence,
    clearResearchEvidence,
    discoverResearchModels,
    refreshResearchJobs,
    getResearchJob,
    cancelResearchJob,
    deleteResearchJob,
    generationFromProfile,
    startResearchRun,
    gradeResearchJob,
    prepareResearchRerun,
    getResponseFaqPage,
    gradeResponseFaqRecord,
    rerunResponseFaqRecord,
    rememberRagPrompt,
    rememberRagRun,
    prepareRagRerun,
  };
}
