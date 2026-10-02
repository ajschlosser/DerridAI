/* Copyright 2026 Aaron John Schlosser, PhD. */

import { openMessageDialog } from "../composables/messageDialog";

// The clipboard helper (the message dialog itself is `MessageDialogHost.vue`). The
// runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper = "toast";
type Deps = { state: Loose } & Record<Helper, Fn>;
export function createModalDialogs(deps: Deps) {
  const { toast } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  async function copyJsonToClipboard(value: Any, labelText = "record") {
    const text = JSON.stringify(value, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      toast(`Copied ${labelText} JSON`);
    } catch (error: Any) {
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      try {
        document.execCommand("copy");
        toast(`Copied ${labelText} JSON`);
      } catch {
        openMessageDialog({ title: "Could not copy", message: error.message, tone: "danger" });
      } finally {
        area.remove();
      }
    }
  }
  return { copyJsonToClipboard };
}
