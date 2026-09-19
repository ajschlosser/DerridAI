const API_BASE = "/api/v0.58.5";
const POLL_INTERVAL_MS = 1500;
const HISTORY_KEY = "derridai.0.58.5.history";
const ACTIVE_JOB_KEY = "derridai.0.58.5.active-job";
const LOCALE_KEY = "derridai.locale";
const SUPPORTED_LOCALES = ["en", "fr"];

const $ = (id) => document.getElementById(id);
const dom = {
  locale: $("locale-select"), form: $("research-form"), prompt: $("prompt-input"),
  responseLanguage: $("response-language"), limit: $("evidence-limit"),
  canonicalWorkIds: $("canonical-work-ids"), submit: $("submit-button"),
  loading: $("loading-indicator"), status: $("status-message"), error: $("error-message"),
  errorText: $("error-text"), selectionCount: $("selection-count"),
  clearSelection: $("clear-selection-button"), runSelected: $("run-selected-button"),
  resultRegion: $("result-region"), resultHeading: $("result-heading"),
  answer: $("answer-content"), copyAnswer: $("copy-answer-button"),
  citations: $("citations-list"), citationsEmpty: $("citations-empty"),
  validation: $("validation-list"), validationEmpty: $("validation-empty"),
  diagnostics: $("diagnostics-list"), evidenceList: $("evidence-list"),
  historyList: $("history-list"), historyEmpty: $("history-empty"),
  clearHistory: $("clear-history-button"),
};

let messages = {};
let locale = "en";
let currentResult = null;
let currentPrompt = "";
let selectedEvidence = new Map();
let pollTimer = null;

function loadLocal(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
function saveLocal(key, value) { localStorage.setItem(key, JSON.stringify(value)); }
function interpolate(template, vars = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? `{${key}}`));
}
function t(key, vars = {}) { return interpolate(messages[key] ?? key, vars); }

async function setLocale(nextLocale) {
  const requested = SUPPORTED_LOCALES.includes(nextLocale) ? nextLocale : "en";
  try {
    const response = await fetch(`/i18n/${requested}.json`, { cache: "no-cache" });
    if (!response.ok) throw new Error(String(response.status));
    messages = await response.json();
    locale = requested;
  } catch {
    if (requested !== "en") return setLocale("en");
    messages = {};
    locale = "en";
  }
  document.documentElement.lang = locale;
  document.documentElement.dir = messages.meta?.dir || "ltr";
  dom.locale.value = locale;
  localStorage.setItem(LOCALE_KEY, locale);
  for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
  for (const node of document.querySelectorAll("[data-i18n-placeholder]")) node.placeholder = t(node.dataset.i18nPlaceholder);
  renderSelectionSummary();
  renderHistory();
  if (currentResult) renderResult(currentResult, currentPrompt, false);
}

function setBusy(busy) {
  dom.form.setAttribute("aria-busy", String(busy));
  dom.submit.disabled = busy;
  dom.loading.hidden = !busy;
}
function clearError() { dom.error.hidden = true; dom.errorText.textContent = ""; }
function showError(message) {
  dom.errorText.textContent = message || t("error.generic");
  dom.error.hidden = false;
  dom.error.tabIndex = -1;
  dom.error.focus();
}
function setStatus(status, phase) {
  const parts = [];
  if (status) parts.push(t(`status.${status}`));
  if (phase) parts.push(t(`status.phase.${phase}`));
  dom.status.textContent = parts.join(" — ");
}

function retrievalMode() {
  return document.querySelector('input[name="retrieval-mode"]:checked')?.value || "auto";
}
function sourceLanguages() {
  return [...document.querySelectorAll('input[name="document-language"]:checked')].map((x) => x.value);
}
function workIds() {
  return dom.canonicalWorkIds.value.split(/[,;\n]+/).map((x) => x.trim()).filter((x, i, a) => x && a.indexOf(x) === i);
}
function compactEvidence(record) {
  const keys = [
    "record_id","text","work","canonical_work_id","document_author","speaker","quoted_speaker",
    "position_holder","stance","proposition_status","target","discourse_role","language",
    "page_start","page_end","year","edition","translator","publisher"
  ];
  return Object.fromEntries(keys.filter((k) => record[k] !== undefined && record[k] !== null && record[k] !== "").map((k) => [k, record[k]]));
}
function requestPayload(forceSelected = false) {
  const mode = forceSelected ? "selected" : retrievalMode();
  const languages = sourceLanguages();
  if (!languages.length) throw new Error(t("form.document_languages"));
  if (mode === "selected" && !selectedEvidence.size) throw new Error(t("error.selected_evidence_required"));
  return {
    prompt: dom.prompt.value.trim(),
    locale,
    options: {
      retrieval_mode: mode,
      response_language: dom.responseLanguage.value,
      document_languages: languages,
      canonical_work_ids: workIds(),
      limit: Number.parseInt(dom.limit.value, 10) || 12,
      include_diagnostics: true
    },
    selected_evidence: mode === "selected" ? [...selectedEvidence.values()].map(compactEvidence) : []
  };
}

async function submitResearch(forceSelected = false) {
  clearError();
  if (!dom.prompt.value.trim()) { dom.prompt.focus(); return; }
  let payload;
  try { payload = requestPayload(forceSelected); } catch (error) { showError(error.message); return; }
  setBusy(true);
  setStatus("pending", "queued");
  try {
    const response = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || String(response.status));
    const job = { jobId: body.job_id, prompt: payload.prompt, submittedAt: new Date().toISOString() };
    saveLocal(ACTIVE_JOB_KEY, job);
    await pollJob(job);
  } catch (error) {
    setBusy(false);
    showError(error.message || t("error.network"));
  }
}

async function pollJob(job) {
  if (pollTimer) clearTimeout(pollTimer);
  try {
    const response = await fetch(`${API_BASE}/query/${encodeURIComponent(job.jobId)}`);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || String(response.status));
    setStatus(body.status, body.phase);
    if (body.status === "completed") {
      localStorage.removeItem(ACTIVE_JOB_KEY);
      setBusy(false);
      currentResult = body.result?.content;
      currentPrompt = job.prompt;
      if (!currentResult) throw new Error(t("error.generic"));
      saveHistory(job.prompt, currentResult);
      renderResult(currentResult, job.prompt, true);
      return;
    }
    if (body.status === "failed") {
      localStorage.removeItem(ACTIVE_JOB_KEY);
      setBusy(false);
      showError(body.error || t("error.generic"));
      return;
    }
    pollTimer = setTimeout(() => pollJob(job), POLL_INTERVAL_MS);
  } catch (error) {
    localStorage.removeItem(ACTIVE_JOB_KEY);
    setBusy(false);
    showError(error.message || t("error.network"));
  }
}

function appendInline(container, text) {
  for (const fragment of String(text).split(/(\[E\d+\]|\*\*[^*]+\*\*|\*[^*]+\*)/g)) {
    if (!fragment) continue;
    if (/^\[E\d+\]$/.test(fragment)) {
      const tag = fragment.slice(1, -1);
      const link = document.createElement("a");
      link.href = `#evidence-${tag}`;
      link.className = "evidence-link";
      link.textContent = fragment;
      link.setAttribute("aria-label", `${t("evidence.heading")} ${tag}`);
      container.append(link);
    } else if (fragment.startsWith("**") && fragment.endsWith("**")) {
      const strong = document.createElement("strong"); strong.textContent = fragment.slice(2, -2); container.append(strong);
    } else if (fragment.startsWith("*") && fragment.endsWith("*")) {
      const em = document.createElement("em"); em.textContent = fragment.slice(1, -1); container.append(em);
    } else container.append(document.createTextNode(fragment));
  }
}
function renderAnswer(text) {
  dom.answer.replaceChildren();
  for (const block of String(text || "").trim().split(/\n{2,}/)) {
    const trimmed = block.trim(); if (!trimmed) continue;
    const heading = trimmed.match(/^#{1,4}\s+(.+)$/);
    const lines = trimmed.split("\n");
    const unordered = lines.every((line) => /^[-*]\s+/.test(line.trim()));
    const ordered = lines.every((line) => /^\d+\.\s+/.test(line.trim()));
    if (heading) {
      const h = document.createElement("h4"); appendInline(h, heading[1]); dom.answer.append(h);
    } else if (unordered || ordered) {
      const list = document.createElement(ordered ? "ol" : "ul");
      for (const line of lines) {
        const li = document.createElement("li"); appendInline(li, line.replace(/^([-*]|\d+\.)\s+/, "")); list.append(li);
      }
      dom.answer.append(list);
    } else {
      const p = document.createElement("p"); appendInline(p, trimmed.replace(/\n/g, " ")); dom.answer.append(p);
    }
  }
}
function metadataRow(list, label, value, score = false) {
  if (value === undefined || value === null || value === "" || (Array.isArray(value) && !value.length)) return;
  const dt = document.createElement("dt"); dt.textContent = label;
  const dd = document.createElement("dd");
  const rendered = Array.isArray(value) ? value.join(", ") : String(value);
  if (score) {
    const span = document.createElement("span"); span.textContent = rendered; span.title = t("evidence.score_help"); span.tabIndex = 0; dd.append(span);
  } else dd.textContent = rendered;
  list.append(dt, dd);
}
function renderCitations(citations = []) {
  dom.citations.replaceChildren(); dom.citationsEmpty.hidden = citations.length > 0;
  for (const citation of citations) {
    const li = document.createElement("li"); li.textContent = citation.full;
    const evidence = currentResult?.evidence?.find((x) => x.record_id === citation.record_id);
    if (evidence) {
      const link = document.createElement("a"); link.href = `#evidence-${evidence.evidence_tag}`; link.className = "evidence-link"; link.textContent = ` [${evidence.evidence_tag}]`; li.append(link);
    }
    dom.citations.append(li);
  }
}
function renderValidation(issues = []) {
  dom.validation.replaceChildren(); dom.validationEmpty.hidden = issues.length > 0;
  for (const issue of issues) {
    const li = document.createElement("li"); li.className = "validation-item"; li.dataset.severity = issue.severity || "info";
    li.textContent = `${String(issue.severity || "info").toUpperCase()}: ${issue.message || issue.code}`; dom.validation.append(li);
  }
}
function renderDiagnostics(info = {}) {
  dom.diagnostics.replaceChildren();
  metadataRow(dom.diagnostics, t("diagnostics.mode"), info.mode);
  metadataRow(dom.diagnostics, t("diagnostics.candidates"), info.candidate_count ?? 0);
  metadataRow(dom.diagnostics, t("diagnostics.deduplicated"), info.deduplicated_count ?? 0);
  metadataRow(dom.diagnostics, t("diagnostics.returned"), info.returned_count ?? 0);
  metadataRow(dom.diagnostics, t("diagnostics.languages"), info.languages || []);
  metadataRow(dom.diagnostics, t("diagnostics.works"), info.canonical_work_ids || []);
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(String(text || "")); dom.status.textContent = t("result.copy_success"); }
  catch { showError(t("error.generic")); }
}
function renderEvidence(records = []) {
  dom.evidenceList.replaceChildren();
  for (const record of records) {
    const article = document.createElement("article"); article.className = "evidence-card"; article.id = `evidence-${record.evidence_tag}`;
    const header = document.createElement("div"); header.className = "evidence-card__header";
    const h3 = document.createElement("h3");
    const pages = record.page_start ? `${record.page_start}${record.page_end && record.page_end !== record.page_start ? "–" + record.page_end : ""}` : "";
    h3.textContent = [record.evidence_tag, record.work, pages].filter(Boolean).join(" · ");
    const label = document.createElement("label"); label.className = "evidence-card__select";
    const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.checked = selectedEvidence.has(record.record_id);
    checkbox.setAttribute("aria-label", t("evidence.select", { tag: record.evidence_tag }));
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) selectedEvidence.set(record.record_id, record); else selectedEvidence.delete(record.record_id);
      renderSelectionSummary();
    });
    const span = document.createElement("span"); span.textContent = t("evidence.selected"); label.append(checkbox, span); header.append(h3, label);

    const body = document.createElement("div"); body.className = "evidence-card__body";
    const dl = document.createElement("dl"); dl.className = "metadata-list";
    metadataRow(dl, t("evidence.work"), record.work); metadataRow(dl, t("evidence.pages"), pages);
    metadataRow(dl, t("evidence.author"), record.document_author); metadataRow(dl, t("evidence.speaker"), record.speaker);
    metadataRow(dl, t("evidence.quoted_speaker"), record.quoted_speaker); metadataRow(dl, t("evidence.position_holder"), record.position_holder);
    metadataRow(dl, t("evidence.stance"), record.stance); metadataRow(dl, t("evidence.role"), record.discourse_role);
    metadataRow(dl, t("evidence.language"), record.language); metadataRow(dl, t("evidence.record_id"), record.record_id);
    metadataRow(dl, t("evidence.retrieval_method"), record.retrieval_method);
    metadataRow(dl, t("evidence.retrieval_score"), record.retrieval_score?.toFixed?.(4) ?? record.retrieval_score, true);
    metadataRow(dl, t("evidence.rerank_score"), record.rerank_score?.toFixed?.(4) ?? record.rerank_score, true);

    const text = document.createElement("p"); text.className = "evidence-text"; text.textContent = record.text || "";
    const actions = document.createElement("div"); actions.className = "evidence-actions";
    const inline = document.createElement("button"); inline.type = "button"; inline.className = "button quiet"; inline.textContent = t("evidence.copy_inline"); inline.addEventListener("click", () => copyText(record.inline_citation));
    const full = document.createElement("button"); full.type = "button"; full.className = "button quiet"; full.textContent = t("evidence.copy_full"); full.addEventListener("click", () => copyText(record.full_citation));
    actions.append(inline, full); body.append(dl, text, actions);
    for (const warning of record.provenance_warnings || []) {
      const p = document.createElement("p"); p.className = "provenance-warning"; p.textContent = `${t("evidence.provenance_warning")}: ${String(warning).replaceAll("_", " ")}`; body.append(p);
    }
    article.append(header, body); dom.evidenceList.append(article);
  }
}
function renderSelectionSummary() {
  const count = selectedEvidence.size;
  dom.selectionCount.textContent = count ? t("selection.count", { count }) : t("selection.none");
  dom.clearSelection.disabled = count === 0; dom.runSelected.disabled = count === 0;
}
function renderResult(content, prompt, focus = false) {
  currentResult = content; currentPrompt = prompt; dom.resultRegion.hidden = false; dom.resultHeading.textContent = prompt;
  renderAnswer(content.response); renderCitations(content.citations || []); renderValidation(content.validation_issues || []);
  renderDiagnostics(content.retrieval || {}); renderEvidence(content.evidence || []);
  if (focus) { dom.resultHeading.tabIndex = -1; dom.resultHeading.focus(); }
}
function saveHistory(prompt, content) {
  const history = loadLocal(HISTORY_KEY, []);
  const light = {
    prompt, response: content.response, citations: content.citations || [],
    validation_issues: content.validation_issues || [], retrieval: content.retrieval || {},
    completedAt: new Date().toISOString()
  };
  saveLocal(HISTORY_KEY, [light, ...history.filter((x) => x.prompt !== prompt)].slice(0, 12)); renderHistory();
}
function renderHistory() {
  const history = loadLocal(HISTORY_KEY, []); dom.historyList.replaceChildren(); dom.historyEmpty.hidden = history.length > 0;
  for (const item of history) {
    const li = document.createElement("li"), button = document.createElement("button"); button.type = "button"; button.textContent = item.prompt;
    const meta = document.createElement("span"); meta.className = "history-meta"; meta.textContent = item.completedAt ? new Date(item.completedAt).toLocaleString(locale) : ""; button.append(meta);
    button.addEventListener("click", () => { dom.prompt.value = item.prompt; renderResult({ ...item, evidence: [] }, item.prompt, true); }); li.append(button); dom.historyList.append(li);
  }
}

dom.form.addEventListener("submit", (event) => { event.preventDefault(); submitResearch(false); });
dom.runSelected.addEventListener("click", () => submitResearch(true));
dom.clearSelection.addEventListener("click", () => {
  selectedEvidence.clear(); renderSelectionSummary();
  for (const checkbox of dom.evidenceList.querySelectorAll('input[type="checkbox"]')) checkbox.checked = false;
});
dom.copyAnswer.addEventListener("click", () => copyText(currentResult?.response || ""));
dom.clearHistory.addEventListener("click", () => { saveLocal(HISTORY_KEY, []); renderHistory(); });
dom.locale.addEventListener("change", async () => { await setLocale(dom.locale.value); dom.responseLanguage.value = locale; });
for (const input of document.querySelectorAll('input[name="retrieval-mode"]')) {
  input.addEventListener("change", () => {
    dom.selectionCount.textContent = retrievalMode() === "selected" && !selectedEvidence.size ? t("error.selected_evidence_required") : (selectedEvidence.size ? t("selection.count", { count: selectedEvidence.size }) : t("selection.none"));
  });
}

(async function initialize() {
  const browser = (navigator.language || "en").slice(0, 2).toLowerCase();
  const saved = localStorage.getItem(LOCALE_KEY);
  await setLocale(SUPPORTED_LOCALES.includes(saved) ? saved : (SUPPORTED_LOCALES.includes(browser) ? browser : "en"));
  dom.responseLanguage.value = locale; renderSelectionSummary(); renderHistory();
  const active = loadLocal(ACTIVE_JOB_KEY, null);
  if (active?.jobId && active?.prompt) { dom.prompt.value = active.prompt; setBusy(true); pollJob(active); }
})();
