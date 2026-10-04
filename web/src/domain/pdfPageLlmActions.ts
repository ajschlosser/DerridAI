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

import { toast } from "../composables/notifications";
import { openMessageDialog } from "../composables/messageDialog";
import { allRows } from "./corpusCache";
import { reviewKey } from "./evidenceSelection";
import { pdfLinks } from "./recordPayloads";
import { reviewItemFromKey } from "./reviewItems";
import { sharedPdfLinking } from "./sharedPdfLinking";
import { pages } from "./sharedRecordHelpers";
import { tr, trf } from "./sharedTranslate";
import { state } from "./sharedUrlState";
import { extractPdfPageSmart } from "./sharedPdfExplorerRenderer";

/* eslint-disable @typescript-eslint/no-explicit-any */
type Any = any;
type Fn = (...args: any[]) => any;
/* eslint-enable @typescript-eslint/no-explicit-any */

// The job dialogs are still built by the runtime (they take runtime-owned helpers), so the PDF page LLM actions reach
// the task launcher and draft-record dialog through late-bound hooks the runtime registers once they exist.
const llmTaskHooks: { openLlmTaskLauncher: Fn; openPdfDraftRecord: Fn } = {
  openLlmTaskLauncher: () => undefined,
  openPdfDraftRecord: () => undefined,
};
export function registerPdfLlmTaskHooks(next: { openLlmTaskLauncher: Fn; openPdfDraftRecord: Fn }) {
  Object.assign(llmTaskHooks, next);
}
const linkPdfPage = sharedPdfLinking.linkPdfPage;

async function currentPdfPageText() {
  const result = await extractPdfPageSmart(state.pdf.page);
  state.pdf.text = result.text;
  state.pdf.extractionSource = result.source;
  state.pdf.extractError = result.warning || "";
  return result.text || "";
}
export async function applyPdfLinkMatch(match: Any) {
  if (!match?.key)
    return openMessageDialog({
      title: "No supported record match",
      message: match?.reason || "The model did not identify a sufficiently supported record.",
    });
  const item = reviewItemFromKey(state, match.key);
  if (!item)
    return openMessageDialog({
      title: "Matched record unavailable",
      message: "The matched record is no longer loaded.",
      tone: "danger",
    });
  const confidence = Number(match.confidence);
  const approved = await openMessageDialog({
    title: "Link PDF page to record?",
    message: `PDF page ${state.pdf.page} → ${item.record.record_id || "matched record"}\n\n${Number.isFinite(confidence) ? `${Math.round(confidence * 100)}% confidence` : "Confidence not reported"}${match.reason ? `\n${match.reason}` : ""}`,
    confirmLabel: "Link page",
    cancelLabel: "Cancel",
  });
  if (!approved) return;
  linkPdfPage(item.file, item.index, state.pdf.page);
  toast(
    trf("runtime.toast.linked_page", {
      page: state.pdf.page,
      record: item.record.record_id || tr("dynamic.record_one"),
    }),
    { tone: "success" },
  );
}
function rankPdfLinkCandidates(rawText: Any) {
  const titleTokens = new Set(
    String(state.pdf.title || state.pdf.name || "")
      .toLocaleLowerCase()
      .split(/\W+/)
      .filter((token) => token.length > 3),
  );
  const page = Number(state.pdf.page);
  const pageTokens = new Set(
    String(rawText || "")
      .toLocaleLowerCase()
      .split(/\W+/)
      .filter((token) => token.length > 5)
      .slice(0, 140),
  );
  return allRows()
    .map(({ file, record, index }: Any) => {
      let score = 0;
      const work = String(record.work || record.document_title || "").toLocaleLowerCase();
      score +=
        work.split(/\W+/).filter((token) => token.length > 3 && titleTokens.has(token)).length * 6;
      const start = Number(record.page_start),
        end = Number(record.page_end ?? record.page_start);
      if (
        Number.isFinite(start) &&
        Number.isFinite(end) &&
        page >= Math.min(start, end) &&
        page <= Math.max(start, end)
      )
        score += 10;
      if (pdfLinks(record).some((link) => link.pdf_file === state.pdf.name)) score += 12;
      score += Math.min(
        12,
        String(record.text || "")
          .toLocaleLowerCase()
          .split(/\W+/)
          .filter((token) => token.length > 5 && pageTokens.has(token))
          .slice(0, 140).length,
      );
      return {
        score,
        candidate: {
          key: reviewKey(file, index),
          record_id: record.record_id || "",
          work: record.work || "",
          pages: pages(record),
          citation: record.inline_citation || record.full_citation || "",
          text: String(record.text || "").slice(0, 600),
        },
      };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 32)
    .map((item) => item.candidate);
}
export async function cleanPdfPageWithLlm() {
  try {
    const raw_text = await currentPdfPageText();
    if (!raw_text.trim()) return toast(tr("runtime.toast.no_page_text"), { tone: "warning" });
    llmTaskHooks.openLlmTaskLauncher({
      task: "pdf_clean_text",
      title: "Clean PDF page text",
      description: `${state.pdf.title || state.pdf.name} · page ${state.pdf.page}`,
      payload: {
        mode: "clean_text",
        raw_text,
        pdf_file: state.pdf.name || null,
        pdf_title: state.pdf.title || null,
        pdf_author: state.pdf.author || null,
        pdf_page: state.pdf.page,
        candidates: [],
      },
      onForegroundResult: async (result: Any) => {
        state.pdf.text = result.text || "";
        state.pdf.extractionSource = `LLM cleanup · ${result.model || "model"} · page ${state.pdf.page}`;
        state.pdf.extractError = "";
        window.dispatchEvent(new CustomEvent("derridai:pdf-explorer-refresh"));
      },
    });
  } catch (error: Any) {
    toast(trf("runtime.toast.llm_cleanup_prepare_failed", { detail: error.message }), {
      tone: "danger",
    });
  }
}
export async function draftPdfPageWithLlm() {
  try {
    const raw_text = await currentPdfPageText();
    if (!raw_text.trim()) return toast(tr("runtime.toast.no_page_text"), { tone: "warning" });
    llmTaskHooks.openLlmTaskLauncher({
      task: "pdf_draft_record",
      title: "Create draft record from PDF page",
      description: `${state.pdf.title || state.pdf.name} · page ${state.pdf.page}`,
      payload: {
        mode: "draft_record",
        raw_text,
        pdf_file: state.pdf.name || null,
        pdf_title: state.pdf.title || null,
        pdf_author: state.pdf.author || null,
        pdf_page: state.pdf.page,
        candidates: [],
      },
      onForegroundResult: async (result: Any) =>
        llmTaskHooks.openPdfDraftRecord(result.record || {}),
    });
  } catch (error: Any) {
    toast(trf("runtime.toast.draft_prepare_failed", { detail: error.message }), { tone: "danger" });
  }
}
export async function linkPdfPageWithLlm() {
  if (!state.files.length)
    return toast(tr("runtime.toast.load_before_pdf_match"), { tone: "warning" });
  try {
    const raw_text = await currentPdfPageText(),
      candidates = rankPdfLinkCandidates(raw_text);
    if (!candidates.length)
      return toast(tr("runtime.toast.no_candidate_records"), { tone: "warning" });
    llmTaskHooks.openLlmTaskLauncher({
      task: "pdf_link_record",
      title: "Link PDF page to record",
      description: `${state.pdf.title || state.pdf.name} · page ${state.pdf.page} · ${candidates.length} pre-ranked candidates`,
      payload: {
        mode: "link_record",
        raw_text,
        pdf_file: state.pdf.name || null,
        pdf_title: state.pdf.title || null,
        pdf_author: state.pdf.author || null,
        pdf_page: state.pdf.page,
        candidates,
      },
      onForegroundResult: async (result: Any) => applyPdfLinkMatch(result.match || {}),
    });
  } catch (error: Any) {
    toast(trf("runtime.toast.record_matching_prepare_failed", { detail: error.message }), {
      tone: "danger",
    });
  }
}
