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

import { dbUnavailableReason } from "./storeAvailability";
import { tr } from "./sharedTranslate";

// Tooltips that explain why a control is disabled, and the modal opener that applies them. Moved out of the legacy
// runtime; they need only the shared translation and store-availability helpers.
export function decorateDisabledControls(root: Document | Element = document) {
  root
    .querySelectorAll?.<
      HTMLElement & { title: string }
    >("button:disabled,input:disabled,select:disabled")
    .forEach((control) => {
      if (control.closest?.(".disabled-control-tooltip")) return;
      const explicit = control.dataset.disabledReason;
      const existingTitle = String(control.title || "").trim();
      const id = (control.id || "").toLowerCase();
      const text = String(control.textContent || "")
        .trim()
        .toLowerCase();
      const pageAction = String(control.dataset.page || "")
        .split(":")
        .at(-1);
      let reason =
        explicit ||
        existingTitle ||
        tr(
          "runtime.disabled.unavailable",
          "This action is unavailable until its required selection or data is available.",
        );
      if (!explicit && !existingTitle && (pageAction === "first" || pageAction === "prev"))
        reason = tr("runtime.disabled.first_page", "You are already on the first page.");
      else if (!explicit && !existingTitle && (pageAction === "next" || pageAction === "last"))
        reason = tr("runtime.disabled.last_page", "You are already on the last page.");
      else if (!explicit && !existingTitle && control.dataset.up !== undefined)
        reason = tr("runtime.disabled.column_first", "This column is already first.");
      else if (!explicit && !existingTitle && control.dataset.down !== undefined)
        reason = tr("runtime.disabled.column_last", "This column is already last.");
      else if (id === "breadcrumbback")
        reason = tr(
          "runtime.disabled.no_earlier_location",
          "There is no earlier navigation location.",
        );
      else if (id === "breadcrumbforward")
        reason = tr(
          "runtime.disabled.no_forward_location",
          "There is no forward navigation location.",
        );
      else if (id === "loadraghistory")
        reason = tr(
          "runtime.disabled.choose_rag_question",
          "Choose a previous RAG question first.",
        );
      else if (id === "applyjobselected" || id === "applyselectedchanges")
        reason = tr(
          "runtime.disabled.select_proposed_change",
          "Select at least one proposed change first.",
        );
      else if (id === "nukeeverything") reason = tr("config.nuke.type_to_enable_help");
      else if (id === "linkpdf")
        reason = tr(
          "runtime.disabled.pdf_page_linked",
          "The current PDF page is already linked to this record.",
        );
      else if (id === "runsearch")
        reason = tr(
          "runtime.disabled.semantic_search_precomputed",
          "Semantic search is unavailable for precomputed-only collections.",
        );
      else if (["ragmodel", "toolmodel", "touchmodel"].includes(id))
        reason = tr(
          "runtime.disabled.model_automatic",
          "The provider is configured to choose the model automatically.",
        );
      else if (id === "columnadd")
        reason = tr("runtime.disabled.all_fields_shown", "Every available field is already shown.");
      else if (id === "importactive")
        reason = tr("runtime.disabled.load_select_jsonl_tab", "Load and select a JSONL tab first.");
      else if (id === "importall")
        reason = tr("runtime.disabled.load_jsonl_tab", "Load at least one JSONL tab first.");
      else if (["extractpage", "extractall", "pdfllmclean", "pdfllmdraft"].includes(id))
        reason = tr(
          "runtime.disabled.load_pdf_text_page",
          "Load a PDF page with extractable text first.",
        );
      else if (["pdfllmlink", "linkcurrentpdf"].includes(id))
        reason = tr(
          "runtime.disabled.load_records_before_link",
          "Load JSONL records before linking a PDF page.",
        );
      else if (
        [
          "collectionembeddingprovider",
          "collectionembeddingmodel",
          "saveembeddingsettings",
        ].includes(id)
      )
        reason = tr(
          "runtime.disabled.embedding_locked",
          "Embedding settings are locked after a collection contains records; create a new empty collection to change them.",
        );
      else if (id === "runtouchup")
        reason = tr(
          "runtime.disabled.configure_llm",
          "Configure a reachable LLM provider and model before running this operation.",
        );
      else if (text.includes("cancelling"))
        reason = tr(
          "runtime.disabled.cancelling",
          "Cancellation has already been requested for this operation.",
        );
      else if (/upsert|sync|rag/.test(id)) reason = dbUnavailableReason() || reason;
      else if (/prev|older/.test(id))
        reason = tr("runtime.disabled.no_previous", "There is no previous item or older version.");
      else if (/next|newer/.test(id))
        reason = tr("runtime.disabled.no_next", "There is no next item or newer version.");
      else if (/merge/.test(id))
        reason = tr(
          "runtime.disabled.merge_two_tabs",
          "Load at least two JSONL tabs to merge them.",
        );
      else if (/subset|bulk|export/.test(id))
        reason = tr("runtime.disabled.load_records", "Load JSONL records first.");
      else if (/edit/.test(id))
        reason = tr("runtime.disabled.select_record", "Select a record first.");
      if (explicit) reason = explicit;
      control.title = reason;
      if (control.tagName === "BUTTON" && !control.closest(".disabled-control-tooltip")) {
        const wrapper = document.createElement("span");
        wrapper.className = "disabled-control-tooltip";
        wrapper.dataset.tooltip = reason;
        control.parentNode?.insertBefore(wrapper, control);
        wrapper.appendChild(control);
      }
    });
}

export function showAppModal(dialog: HTMLDialogElement) {
  decorateDisabledControls(dialog);
  dialog.showModal();
}
