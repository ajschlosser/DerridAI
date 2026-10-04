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
import { stripLigaturesAndArtifacts } from "./textCleanup";
import { applyRecordChanges } from "./sharedRecordEditing";
import { renderView } from "./sharedNavigation";
import { tr, trf } from "./sharedTranslate";
import { shell } from "./sharedWorkspaceStorage";

/* eslint-disable @typescript-eslint/no-explicit-any */
// Strips ligatures and extraction artefacts from one record's text as a tracked OCR-cleanup change.
export function cleanRecord(f: any, i: number) {
  const c = stripLigaturesAndArtifacts(f.records[i].text);
  if (!c.changed) return toast(tr("runtime.toast.no_ligatures"), { tone: "warning" });
  const changed = applyRecordChanges(f, i, { text: c.text }, { source: "ocr_cleanup" });
  shell();
  renderView();
  toast(
    trf(
      changed === 1
        ? "runtime.toast.tracked_changes_applied_one"
        : "runtime.toast.tracked_changes_applied_many",
      { count: changed },
    ),
    { tone: "success" },
  );
}
