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

// Document-level click delegation the legacy runtime registered at module scope: opening a job result from any
// result button, and the copy / cite / evidence buttons that legacy-built markup still emits. Registers on import.
/* eslint-disable @typescript-eslint/no-explicit-any */
import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";
import { copyCitation, copyJsonToClipboard } from "./clipboardCopy";
import { openJobResults } from "./operationsPanelHooks";
import { reviewItemFromKey } from "./reviewItems";
import { renderView } from "./sharedNavigation";
import { evidenceSelection } from "./sharedSearchSupport";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";

const RESULT_SELECTOR =
  "[data-toast-open-result],[data-job-result],[data-rag-job-result],[data-recent-rag-result]";

document.addEventListener(
  "click",
  (event) => {
    const resultButton = (event.target as Element | null)?.closest?.<HTMLButtonElement>(
      RESULT_SELECTOR,
    );
    if (!resultButton) return;
    const jobId =
      resultButton.dataset.toastOpenResult ||
      resultButton.dataset.jobResult ||
      resultButton.dataset.ragJobResult ||
      resultButton.dataset.recentRagResult;
    if (!jobId) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    resultButton.disabled = true;
    const original = resultButton.innerHTML;
    resultButton.textContent = tr("runtime.result_opening");
    void Promise.resolve(openJobResults(jobId))
      .catch((error: any) =>
        openMessageDialog({
          title: tr("runtime.result_open_failed"),
          message: error?.message || String(error),
          tone: "danger",
        }),
      )
      .finally(() => {
        if (resultButton.isConnected) {
          resultButton.disabled = false;
          resultButton.innerHTML = original;
        }
      });
  },
  { capture: true },
);

document.addEventListener("click", (event) => {
  const target = event.target as Element | null;
  const s = state as any;
  const loadedButton = target?.closest?.<HTMLElement>("[data-copy-row-key]");
  if (loadedButton) {
    event.stopPropagation();
    const item = reviewItemFromKey(s, loadedButton.dataset.copyRowKey);
    if (item)
      copyJsonToClipboard(
        item.file.records[item.index],
        item.record.record_id || tr("dynamic.record_one"),
      );
    else toast(tr("runtime.toast.source_record_gone"), { tone: "danger" });
    return;
  }
  const citeButton = target?.closest?.<HTMLElement>("[data-cite-row-key]");
  if (citeButton) {
    event.stopPropagation();
    const item = reviewItemFromKey(s, citeButton.dataset.citeRowKey);
    if (item) copyCitation(item.record, citeButton.dataset.citeKind || "inline");
    return;
  }
  const dbCite = target?.closest?.<HTMLElement>("[data-admin-db-cite],[data-r-cite]");
  if (dbCite) {
    event.preventDefault();
    event.stopPropagation();
    const id = String(dbCite.dataset.adminDbId || dbCite.dataset.rId || "");
    const result = (s.storeSearchResults || []).find(
      (item: any) =>
        String(item.id || item.record?._chroma_id || item.record?.record_id || "") === id,
    );
    const record =
      result?.record ||
      (s.storeRecords || []).find(
        (item: any) => String(item._chroma_id || item.record_id || "") === id,
      );
    if (record)
      copyCitation(record, dbCite.dataset.adminDbCite || dbCite.dataset.rCite || "inline");
    else toast(tr("runtime.toast.citation_source_gone"), { tone: "warning" });
    return;
  }
  const evidenceButton = target?.closest?.<HTMLElement>("[data-toggle-workspace-evidence]");
  if (evidenceButton) {
    event.stopPropagation();
    const item = reviewItemFromKey(s, evidenceButton.dataset.toggleWorkspaceEvidence);
    if (item) {
      evidenceSelection.toggleWorkspaceEvidence(item.file, item.index);
      renderView();
    }
    return;
  }
  const storeButton = target?.closest?.<HTMLElement>("[data-copy-store-record]");
  if (storeButton) {
    event.stopPropagation();
    const record = s.storeRecords.find(
      (item: any) =>
        String(item._chroma_id || "") === String(storeButton.dataset.copyStoreRecord || ""),
    );
    if (record) {
      const copy = { ...record };
      delete copy._chroma_id;
      copyJsonToClipboard(copy, copy.record_id || tr("runtime.toast.chroma_record"));
    }
  }
});
