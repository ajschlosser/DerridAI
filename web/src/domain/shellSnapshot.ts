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

import { esc } from "./html";
import { getNavItems } from "./navItems";
import { describeRecordsFile } from "./recordsFiles";
import { evidenceSelection } from "./sharedSearchSupport";
import { activeFile, selectedRecord } from "./sharedRecordScopes";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { hasCorpusDb, recordStores } from "./storeAvailability";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;
const { selectedEvidenceEntries } = evidenceSelection;

export function systemCardHtml() {
  const health = state.health;
  const row = (name: string, dot: string, label: string) =>
    `<div class="system-row"><span>${name}</span><span class="system-value"><i class="status-dot${dot ? ` ${dot}` : ""}"></i>${esc(label)}</span></div>`;
  if (!health) {
    const unknown = tr("runtime.unknown");
    return [
      row("API", "warn", tr("runtime.checking")),
      row("Chroma", "", unknown),
      row("Ollama", "", unknown),
    ].join("\n      ");
  }
  const apiOk = health?.ok === true;
  const chromaOk = health?.chroma?.available === true;
  const ollamaOk = (state.llmStatus || health?.ollama)?.available === true;
  const service = (ok: boolean) => ({
    dot: ok ? "ok" : apiOk ? "warn" : "bad",
    label: tr(ok ? "runtime.ready" : apiOk ? "runtime.unavailable" : "runtime.unknown"),
  });
  const chroma = service(chromaOk);
  const ollama = service(ollamaOk);
  return [
    row("API", apiOk ? "ok" : "bad", tr(apiOk ? "runtime.online" : "runtime.offline")),
    row("Chroma", chroma.dot, chroma.label),
    row("Ollama", ollama.dot, ollama.label),
  ].join("\n    ");
}

function currentContext() {
  const f = activeFile(),
    r = selectedRecord();
  if (state.view === "record" && r)
    return {
      kicker: r.record_id || tr("runtime.record"),
      title: r.work || tr("runtime.record"),
      meta: f?.name || "",
    };
  const map: Record<string, string[]> = {
    home: [
      "Overview",
      "Dashboard",
      "Workspace, vector stores, review activity, and corpus statistics",
    ],
    list: [
      "Corpora",
      f?.name || "Records",
      f
        ? `${f.records.length.toLocaleString()} ${tr("dynamic.records")}`
        : tr("runtime.open_jsonl"),
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
        ? `${state.pdf.name} · ${tr("record.pdf_page").replace("{page}", String(state.pdf.page))}`
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
/**
 * Route/file context needed by breadcrumbs and feature views that still consume
 * shell compatibility state. It is independent from sidebar navigation and
 * status counters, so callers can refresh only the slice they actually changed.
 */
export function getShellContextSnapshot() {
  return {
    view: state.view,
    files: state.files.map((file: Any) => describeRecordsFile(file, state.activeFileId)),
    context: currentContext(),
  };
}

/**
 * Small status projection used by application chrome. None of these values
 * scans record contents; work is bounded by loaded file/store/evidence counts.
 */
export function getShellStatusSnapshot() {
  // Shell chrome only needs the aggregate count. Counting file lengths avoids
  // rebuilding the corpus-wide flattened row cache after every record edit.
  const totalLoaded = state.files.reduce(
    (sum: number, file: Any) => sum + (Array.isArray(file.records) ? file.records.length : 0),
    0,
  );
  const corpusStores = recordStores();
  const dbRecords = corpusStores.reduce(
    (sum: number, store: Any) => sum + (Number(store.count) || 0),
    0,
  );
  return {
    totalLoaded,
    corpusStoreCount: corpusStores.length,
    dbRecords,
    hasCorpusDb: hasCorpusDb(),
    activeStore: state.activeStore,
    selectedEvidenceCount: selectedEvidenceEntries().length,
  };
}

/**
 * Compatibility snapshot for callers that still need the complete shell model.
 * Native shell code should prefer the independently refreshable projections.
 */
export function getShellSnapshot() {
  return {
    ...getShellContextSnapshot(),
    ...getShellStatusSnapshot(),
    nav: getNavItems(),
  };
}
