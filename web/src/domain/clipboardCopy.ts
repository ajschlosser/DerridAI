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

import { openMessageDialog } from "../composables/messageDialog";
import { toast } from "../composables/notifications";
import { fullCitation, inlineCitation } from "./citations";
import { trf } from "./sharedTranslate";

// Clipboard helpers shared by Vue callers and the runtime. The legacy code and tests pass records freely.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

export async function copyJsonToClipboard(value: unknown, labelText = "record") {
  const text = JSON.stringify(value, null, 2);
  try {
    await navigator.clipboard.writeText(text);
    toast(trf("runtime.toast.json_copied", { label: labelText }), { tone: "success" });
  } catch (error) {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try {
      document.execCommand("copy");
      toast(trf("runtime.toast.json_copied", { label: labelText }), { tone: "success" });
    } catch {
      openMessageDialog({
        title: "Could not copy",
        message: (error as Error).message,
        tone: "danger",
      });
    } finally {
      area.remove();
    }
  }
}

export async function copyCitation(record: Loose, kind = "inline") {
  const text = kind === "full" ? fullCitation(record) : inlineCitation(record);
  try {
    await navigator.clipboard.writeText(text);
    // Say exactly what reached the clipboard, so the reader can check it before pasting.
    toast(
      trf(
        kind === "full"
          ? "record.full_citation_copied_value"
          : "record.inline_citation_copied_value",
        kind === "full"
          ? "Copied full citation to the clipboard: {citation}"
          : "Copied inline citation to the clipboard: {citation}",
        { citation: text },
      ),
      { tone: "success", duration: 7000 },
    );
  } catch (error) {
    toast(
      trf("record.copy_failed_reason", {
        error: (error as Error)?.message || String(error),
      }),
      { tone: "danger" },
    );
  }
}
