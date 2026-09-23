/* Copyright 2026 Aaron John Schlosser, PhD. */

// Application lifecycle: importing and closing corpus files, warming up an LLM provider, and the health check run at
// start-up and after Chroma becomes available. Moved verbatim from the legacy runtime; the runtime's state object and
// helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "api"
  | "applyCompressedTableUrlState"
  | "clearFileDerivedState"
  | "decompressUrlState"
  | "defaultProviderProfile"
  | "ensureProviderProfiles"
  | "idbDelete"
  | "invalidateCorpusCache"
  | "isResearcher"
  | "openMessageModal"
  | "parseJsonl"
  | "persistFileNow"
  | "persistPrefs"
  | "providerDisplayName"
  | "providerProfile"
  | "providerRequestConfig"
  | "refreshProviderStatuses"
  | "refreshStoreWorks"
  | "refreshStores"
  | "renderView"
  | "shell"
  | "stableJsonlFileIdentity"
  | "syncUrl"
  | "toast"
  | "tr"
  | "trf"
  | "updateSystemCard";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createAppLifecycle(deps: Deps) {
  const {
    state,
    api,
    applyCompressedTableUrlState,
    clearFileDerivedState,
    decompressUrlState,
    defaultProviderProfile,
    ensureProviderProfiles,
    idbDelete,
    invalidateCorpusCache,
    isResearcher,
    openMessageModal,
    parseJsonl,
    persistFileNow,
    persistPrefs,
    providerDisplayName,
    providerProfile,
    providerRequestConfig,
    refreshProviderStatuses,
    refreshStoreWorks,
    refreshStores,
    renderView,
    shell,
    stableJsonlFileIdentity,
    syncUrl,
    toast,
    tr,
    trf,
    updateSystemCard,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  async function warmupProviderProfile(profileId = null) {
    const profile = providerProfile(profileId || state.appConfig.default_provider_profile);
    if (!profile) return;
    const current = state.providerWarmups?.[profile.id] || {};
    if (current.status === "running") return;
    const cfg = providerRequestConfig(profile, { textReview: false });
    const started = performance.now();
    const startedAt = new Date().toISOString();
    const running = {
      status: "running",
      message: `Warming ${cfg.model}…`,
      profile_id: profile.id,
      provider: profile.type,
      model: cfg.model,
      base_url: cfg.base_url,
      started_at: startedAt,
      completed_at: null,
      elapsed_seconds: null,
      error: null,
    };
    state.providerWarmups[profile.id] = running;
    if (profile.id === state.appConfig.default_provider_profile) state.warmup = running;
    if (state.view === "home") window.dispatchEvent(new CustomEvent("derridai:dashboard-refresh"));
    try {
      const result = await api("/api/llm/warmup", {
        method: "POST",
        body: JSON.stringify({
          provider: profile.type,
          model: cfg.model,
          base_url: cfg.base_url,
          api_key: cfg.api_key,
          // Load with the context real calls use, so the model is not loaded twice.
          num_ctx: Number(cfg.ollama?.num_ctx) > 0 ? Number(cfg.ollama.num_ctx) : undefined,
        }),
      });
      const ready = {
        status: "ready",
        message: `${providerDisplayName(profile)} · ${result.model || cfg.model} warmed`,
        profile_id: profile.id,
        provider: profile.type,
        model: result.model || cfg.model,
        base_url: result.base_url || cfg.base_url,
        started_at: startedAt,
        completed_at: new Date().toISOString(),
        elapsed_seconds: (performance.now() - started) / 1000,
        error: null,
      };
      state.providerWarmups[profile.id] = ready;
      if (profile.id === state.appConfig.default_provider_profile) state.warmup = ready;
    } catch (error: Any) {
      const failed = {
        status: "failed",
        message: error.message,
        profile_id: profile.id,
        provider: profile.type,
        model: cfg.model,
        base_url: cfg.base_url,
        started_at: startedAt,
        completed_at: new Date().toISOString(),
        elapsed_seconds: (performance.now() - started) / 1000,
        error: error.message,
      };
      state.providerWarmups[profile.id] = failed;
      if (profile.id === state.appConfig.default_provider_profile) state.warmup = failed;
    }
    if (state.view === "home") window.dispatchEvent(new CustomEvent("derridai:dashboard-refresh"));
  }
  async function warmupConfiguredLlm() {
    return warmupProviderProfile(state.appConfig.default_provider_profile);
  }
  async function importFiles(fileList: Any) {
    if (isResearcher()) return toast(tr("runtime.toast.researcher_cannot_load"));
    const shareParams = new URLSearchParams(location.search);
    const requestedFileId = shareParams.get("file");
    const requestedUrlState = shareParams.get("ts");
    let first = null,
      total = 0,
      errors = 0;
    for (const file of [...fileList]) {
      const text = await file.text();
      const parsed = parseJsonl(text);
      if (!parsed.records.length) {
        errors += parsed.errors.length || 1;
        continue;
      }
      const identity = await stableJsonlFileIdentity(text);
      const existing = state.files.find((item: Any) => item.id === identity.id);
      if (existing) {
        first ||= existing.id;
        total += existing.records.length;
        errors += existing.errors?.length || 0;
        continue;
      }
      const item = {
        ...identity,
        name: file.name,
        records: parsed.records,
        errors: parsed.errors,
        dirty: new Set(),
        imported_at: new Date().toISOString(),
      };
      state.files.push(item);
      persistFileNow(item);
      first ||= item.id;
      total += item.records.length;
      errors += item.errors.length;
    }
    if (requestedFileId && state.files.some((item: Any) => item.id === requestedFileId)) {
      state.activeFileId = requestedFileId;
      if (requestedUrlState)
        applyCompressedTableUrlState(decompressUrlState(requestedUrlState), state.view);
    } else if (first) state.activeFileId = first;
    persistPrefs();
    shell();
    renderView();
    syncUrl({ replace: true });
    toast(
      errors
        ? trf("dynamic.loaded_records_issues", { count: total, issues: errors })
        : trf("dynamic.loaded_records", { count: total }),
    );
  }
  async function closeFile(id: Any) {
    const f = state.files.find((x: Any) => x.id === id);
    if (!f) return;
    if (
      f.dirty.size &&
      !(await openMessageModal({
        title: tr("files.close_modified_title"),
        message: trf("files.close_modified_message", { name: f.name }),
        tone: "danger",
        confirmLabel: tr("ui.close_file"),
        cancelLabel: tr("files.keep_open"),
      }))
    )
      return;
    const i = state.files.indexOf(f);
    state.files.splice(i, 1);
    delete state.searches[id];
    delete state.listFilters[id];
    delete state.pages[id];
    delete state.sorts[id];
    clearFileDerivedState(id);
    invalidateCorpusCache();
    idbDelete("files", id).catch((error: Any) =>
      console.error("Could not remove saved file", error),
    );
    if (state.activeFileId === id)
      state.activeFileId = state.files[Math.min(i, state.files.length - 1)]?.id || null;
    persistPrefs();
    shell();
    renderView();
  }
  async function checkHealth() {
    try {
      state.health = await api("/api/health");
      ensureProviderProfiles();
      await refreshProviderStatuses();
    } catch (error: Any) {
      state.health = { ok: false, error: error.message };
      state.providerStatuses = {};
      state.llmStatus = {
        provider: defaultProviderProfile()?.type || "ollama",
        available: false,
        models: [],
        error: error.message,
      };
    }
    updateSystemCard();
    if (state.health?.chroma?.available) {
      try {
        await refreshStores();
        if (isResearcher() && state.activeStore) await refreshStoreWorks(true);
        persistPrefs();
        const active = document.activeElement;
        const userIsEditing =
          active &&
          active !== document.body &&
          ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName);
        if (!userIsEditing) {
          shell();
          renderView();
        }
      } catch (error: Any) {
        console.warn("Initial Chroma collection refresh failed", error);
      }
    }
  }
  return { warmupProviderProfile, warmupConfiguredLlm, importFiles, closeFile, checkHealth };
}
