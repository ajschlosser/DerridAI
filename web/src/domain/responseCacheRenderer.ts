/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

// The response cache page, drawn as an HTML string into the runtime surface. Moved verbatim from the legacy runtime; the
// runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "api"
  | "formatTimestamp"
  | "navigateTo"
  | "openMessageModal"
  | "persistPrefs"
  | "refreshStores"
  | "responseCacheStore"
  | "showViewLoading"
  | "toast";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createResponseCacheRenderer(deps: Deps) {
  const {
    state,
    api,
    formatTimestamp,
    navigateTo,
    openMessageModal,
    persistPrefs,
    refreshStores,
    responseCacheStore,
    showViewLoading,
    toast,
  } = deps;
  async function renderResponseCache(main: Any) {
    showViewLoading(main, "Loading response cache", "Reading cached RAG responses…");
    try {
      await refreshStores();
    } catch (error: Any) {
      console.warn("Could not refresh store metadata", error);
    }
    let payload;
    try {
      payload = await api("/api/response-cache/records?limit=100&offset=0");
    } catch (error: Any) {
      main.innerHTML = `<div class="info error"><b>Could not read response cache.</b><span>${esc(error.message || String(error))}</span></div>`;
      return;
    }
    const cache = responseCacheStore();
    const count = Number(payload.total ?? payload.count ?? 0);
    const records = Array.isArray(payload.records) ? payload.records : [];
    const exists = Boolean(payload.exists || cache);
    main.innerHTML = `<div class="response-cache-page">
    <section class="card response-cache-overview">
      <div class="cardhead"><div><b>RAG response cache</b><div class="note">System cache only. This collection is intentionally excluded from corpus Vector Stores, corpus DB counts, language mirroring, and RAG source selection.</div></div><div class="tools"><button class="btn" id="cacheFaq">${icon("books")}Open Response Library</button>${exists ? '<button class="btn danger" id="clearResponseCache">Clear cache</button>' : ""}</div></div>
      <div class="dashboard-kpis response-cache-kpis"><div class="dash-kpi"><span>Cached responses</span><strong>${count.toLocaleString()}</strong></div><div class="dash-kpi"><span>Collection</span><strong>${exists ? "_response_cache" : "Not created"}</strong></div><div class="dash-kpi"><span>Embedding</span><strong>${esc(cache?.embedding_model || "system-managed")}</strong></div></div>
      <div class="info">Each cache record stores the original RAG query, instructions, run parameters, answer, evidence, retrieval diagnostics, timings, and all saved LLM grading runs.</div>
    </section>
    <section class="card"><div class="cardhead"><div><b>Recent cached responses</b><div class="note">Latest 100 response-cache entries. Use Response Library for full answer/evidence browsing and re-runs.</div></div></div>
      <div class="tablewrap"><table><thead><tr><th>Created</th><th>Question</th><th>Generation</th><th>Evidence</th><th>Grades</th><th></th></tr></thead><tbody>${records.map((record: Any, index: Any) => `<tr><td>${esc(formatTimestamp(record.created_at))}</td><td>${esc(record.question || "")}</td><td>${esc(record.provider || "")} · ${esc(record.model || "")}</td><td>${Number(record.evidence_count || 0)}</td><td>${Array.isArray(record.grades) ? record.grades.length : 0}</td><td><button class="btn tiny" data-cache-faq="${index}">Open in Response Library</button></td></tr>`).join("") || '<tr><td colspan="6" class="note">No cached responses yet.</td></tr>'}</tbody></table></div>
    </section>
  </div>`;
    main.querySelector("#cacheFaq")?.addEventListener("click", () => navigateTo("faq"));
    main.querySelectorAll("[data-cache-faq]").forEach(
      (button: Any) =>
        (button.onclick = () => {
          state.faqSearch = records[+button.dataset.cacheFaq]?.question || "";
          state.faqPage = 1;
          persistPrefs();
          navigateTo("faq");
        }),
    );
    main.querySelector("#clearResponseCache")?.addEventListener("click", async () => {
      const approved = await openMessageModal({
        title: "Clear RAG response cache?",
        message: `Delete all ${count.toLocaleString()} cached RAG responses and saved grades? Corpus vector databases are not affected.`,
        tone: "danger",
        confirmLabel: "Clear response cache",
        cancelLabel: "Cancel",
      });
      if (!approved) return;
      try {
        await api("/api/stores/_response_cache", { method: "DELETE" });
        await refreshStores();
        renderResponseCache(main);
        toast("Response cache cleared");
      } catch (error: Any) {
        toast(`Could not clear response cache: ${error.message}`);
      }
    });
  }
  return { renderResponseCache };
}
