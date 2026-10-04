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

import { allRows } from "./corpusCache";
import { getNavItems } from "./navItems";
import { describeRecordsFile } from "./recordsFiles";
import { canUse } from "./sharedSession";
import { pendingUpsertRows } from "./sharedDbPresence";
import { evidenceSelection } from "./sharedSearchSupport";
import { activeFile, needsReviewItems, selectedRecord } from "./sharedRecordScopes";
import { responseCacheStore } from "./sharedStores";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { dbUnavailableReason, hasCorpusDb, recordStores } from "./storeAvailability";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;
const { selectedEvidenceEntries } = evidenceSelection;

export function systemCardHtml() {
  const health = state.health;
  if (!health) {
    return `<div class="system-row"><span>API</span><span class="system-value"><i class="status-dot warn"></i>Checking</span></div>
      <div class="system-row"><span>Chroma</span><span class="system-value"><i class="status-dot"></i>Unknown</span></div>
      <div class="system-row"><span>Ollama</span><span class="system-value"><i class="status-dot"></i>Unknown</span></div>`;
  }
  const apiOk = health?.ok === true;
  const chromaOk = health?.chroma?.available === true;
  const ollamaOk = (state.llmStatus || health?.ollama)?.available === true;
  return `<div class="system-row"><span>API</span><span class="system-value"><i class="status-dot ${apiOk ? "ok" : "bad"}"></i>${apiOk ? "Online" : "Offline"}</span></div>
    <div class="system-row"><span>Chroma</span><span class="system-value"><i class="status-dot ${chromaOk ? "ok" : apiOk ? "warn" : "bad"}"></i>${chromaOk ? "Ready" : apiOk ? "Unavailable" : "Unknown"}</span></div>
    <div class="system-row"><span>Ollama</span><span class="system-value"><i class="status-dot ${ollamaOk ? "ok" : apiOk ? "warn" : "bad"}"></i>${ollamaOk ? "Ready" : apiOk ? "Unavailable" : "Unknown"}</span></div>`;
}

function currentContext() {
  const f = activeFile(),
    r = selectedRecord();
  if (state.view === "record" && r)
    return { kicker: r.record_id || "Record", title: r.work || "Record", meta: f?.name || "" };
  const map: Record<string, string[]> = {
    home: [
      "Overview",
      "Dashboard",
      "Workspace, vector stores, review activity, and corpus statistics",
    ],
    list: [
      "Corpora",
      f?.name || "Records",
      f ? `${f.records.length.toLocaleString()} ${tr("dynamic.records")}` : "Open a JSONL file",
    ],
    works: ["Corpora", "Works", "Cross-file work overview"],
    global: ["Corpora", "Global Search", "Search and filter every loaded record"],
    annotations: [
      "Corpora",
      "Annotations",
      "Review annotations by work or in recent-activity order",
    ],
    semanticmap: ["Corpora", "Semantic map", "Concepts, topics, and persons that occur together"],
    pdf: [
      "Corpus Management",
      state.pdf.title || "Corpus Builder",
      state.pdf.name
        ? `${state.pdf.name} · page ${state.pdf.page}`
        : "Build, monitor, and review auditable corpus records",
    ],
    compare: ["Corpora", "Record Comparison", "Inspect field and text differences"],
    vector: ["Corpus Management", "Corpus Data", "Persistent local ChromaDB collections"],
    rag: [
      "Research",
      "Research",
      "Run the evidence-grounded DerridAI retrieval and synthesis pipeline",
    ],
    faq: [
      "Research",
      "Response Library",
      "Browse saved RAG questions, answers, evidence, reruns, and grades",
    ],
    responsecache: [
      "System",
      "System Data",
      "Inspect application storage, trace derived metadata, and manage saved research responses.",
    ],
    providers: [
      "AI & Automation",
      "LLM Providers",
      "Create, configure, test, warm, and reuse LLM provider profiles across every LLM workflow",
    ],
    config: [
      "System",
      "Settings",
      "Application behavior, retrieval defaults, storage, backup, and reset controls",
    ],
  };
  const dynamicTitle =
    (state.view === "list" && f?.name) || (state.view === "pdf" && state.pdf.title);
  const dynamicMeta = (state.view === "list" && f) || (state.view === "pdf" && state.pdf.name);
  const key = map[state.view] ? state.view : "list";
  const [kickerText, titleText, metaText] = map[key];
  // Static labels are translated; data-driven titles (file names, PDF titles) are not.
  return {
    kicker: tr(`context.${key}.kicker`, kickerText),
    title: dynamicTitle ? titleText : tr(`context.${key}.title`, titleText),
    meta: dynamicMeta ? metaText : tr(`context.${key}.meta`, metaText),
  };
}
export function getShellSnapshot() {
  const ctx = currentContext();
  const totalLoaded = allRows().length;
  const flagged = needsReviewItems().length;
  const pending = state.activeStore ? pendingUpsertRows().length : 0;
  const corpusStores = recordStores();
  const dbRecords = corpusStores.reduce(
    (sum: number, store: Any) => sum + (Number(store.count) || 0),
    0,
  );
  const cacheCount = Number(responseCacheStore()?.count || 0);
  const activeJobs = state.jobs.filter((job: Any) =>
    ["queued", "running", "cancelling"].includes(job.status),
  ).length;
  return {
    view: state.view,
    files: state.files.map((file: Any) => describeRecordsFile(file, state.activeFileId)),
    context: ctx,
    totalLoaded,
    flagged,
    pending,
    activeJobs,
    corpusStoreCount: corpusStores.length,
    dbRecords,
    cacheCount,
    hasCorpusDb: hasCorpusDb(),
    dbUnavailableReason: dbUnavailableReason(),
    activeStore: state.activeStore,
    canEdit: canUse("editLocalRecords") && state.view === "record" && Boolean(selectedRecord()),
    selectedEvidenceCount: selectedEvidenceEntries().length,
    systemHtml: systemCardHtml(),
    nav: getNavItems(),
  };
}
