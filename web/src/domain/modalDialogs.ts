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

// The clipboard helper (the message dialog itself is `MessageDialogHost.vue`). The
// runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper = "trf";
type Deps = { state: Loose } & Record<Helper, Fn>;
export function createModalDialogs(deps: Deps) {
  const { trf } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  async function copyJsonToClipboard(value: Any, labelText = "record") {
    const text = JSON.stringify(value, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      toast(trf("runtime.toast.json_copied", { label: labelText }), { tone: "success" });
    } catch (error: Any) {
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
        openMessageDialog({ title: "Could not copy", message: error.message, tone: "danger" });
      } finally {
        area.remove();
      }
    }
  }
  return { copyJsonToClipboard };
}
