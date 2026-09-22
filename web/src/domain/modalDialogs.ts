/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

// The confirmation and message dialog and the clipboard helper, drawn as HTML strings. Moved verbatim from the legacy
// runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper = "showAppModal" | "toast";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createModalDialogs(deps: Deps) {
  const { showAppModal, toast } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  function openMessageModal({
    title = "Notice",
    message = "",
    detail = "",
    tone = "info",
    confirmLabel = "OK",
    cancelLabel = null,
  } = {}) {
    return new Promise((resolve) => {
      const dialog = document.createElement("dialog");
      dialog.className = `message-dialog ${tone}`;
      dialog.innerHTML = `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2>${detail ? `<div class="dialog-subtitle">${esc(detail)}</div>` : ""}</div><button class="btn icon-only" data-cancel>${icon("close")}</button></div><div class="db"><div class="message-modal-body">${esc(message).replace(/\n/g, "<br>")}</div></div><div class="da">${cancelLabel ? `<button class="btn" data-cancel>${esc(cancelLabel)}</button>` : ""}<button class="btn ${tone === "danger" ? "danger" : "primary"}" data-confirm>${esc(confirmLabel)}</button></div>`;
      document.body.appendChild(dialog);
      const finish = (value: Any) => {
        dialog.close();
        dialog.remove();
        resolve(value);
      };
      dialog
        .querySelectorAll("[data-cancel]")
        .forEach((button: Any) => (button.onclick = () => finish(false)));
      dialog.querySelector("[data-confirm]").onclick = () => finish(true);
      dialog.addEventListener(
        "cancel",
        (event: Any) => {
          event.preventDefault();
          finish(false);
        },
        { once: true },
      );
      showAppModal(dialog);
    });
  }
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
        openMessageModal({ title: "Could not copy", message: error.message, tone: "danger" });
      } finally {
        area.remove();
      }
    }
  }
  return { openMessageModal, copyJsonToClipboard };
}
