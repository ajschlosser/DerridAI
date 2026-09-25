/* Copyright 2026 Aaron John Schlosser, PhD. */

import { createPdfExplorerCopy } from "./pdfExplorerCopy";

// Live PDF canvas rendering and text extraction. Explorer chrome lives in PdfExplorerSurface.vue.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any
type Deps = { state: Loose; tr: Fn; trf: Fn };

export function createPdfExplorerRenderer(deps: Deps) {
  const { state, tr, trf } = deps;
  const copy = createPdfExplorerCopy(tr, trf);
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  async function renderPdfCanvas(pageNumber: Any) {
    const canvas = document.querySelector("#pdfCanvas");
    if (!canvas || !state.pdf.doc) return;
    const status = document.querySelector("#pdfRenderStatus");
    try {
      if (status) status.textContent = copy.rendering(pageNumber);
      const page = await state.pdf.doc.getPage(pageNumber);
      const rotation = Number(state.pdf.rotation || 0) % 360;
      const base = page.getViewport({ scale: 1, rotation });
      const container = canvas.parentElement;
      const maxWidth = Math.max(420, (container?.clientWidth || 900) - 32);
      // PDF tools now live below the viewer, so the document can use its natural
      // fit-width scale without reserving horizontal room for a side column.
      const scale = Math.min(2.1, Math.max(0.5, maxWidth / base.width));
      const viewport = page.getViewport({ scale, rotation });
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(viewport.width * dpr);
      canvas.height = Math.floor(viewport.height * dpr);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      const context = canvas.getContext("2d");
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      await page.render({ canvasContext: context, viewport }).promise;
      if (status) status.textContent = "";
    } catch (error: Any) {
      console.error("PDF render failed", error);
      if (status) status.textContent = copy.renderFailed(pageNumber, error.message);
    }
  }
  async function extractPdfPageBrowser(p: Any) {
    if (!state.pdf.doc) throw new Error(copy.pdfJsUnavailable);
    const page = await state.pdf.doc.getPage(p);
    const content = await page.getTextContent({ includeMarkedContent: true });
    let text = "";
    for (const item of content.items) {
      if (!item || typeof item.str !== "string") continue;
      text += item.str;
      text += item.hasEOL ? "\n" : " ";
    }
    return text
      .replace(/[ \t]+\n/g, "\n")
      .replace(/ {2,}/g, " ")
      .trim();
  }
  async function extractPdfApi(page = null) {
    if (!state.pdf.file) throw new Error(copy.fileGone);
    const form = new FormData();
    form.append("file", state.pdf.file, state.pdf.name || "document.pdf");
    const url = page ? `/api/pdf/extract?page=${page}` : "/api/pdf/extract";
    let response;
    try {
      response = await fetch(url, { method: "POST", body: form });
    } catch (error: Any) {
      throw new Error(copy.apiUnreachable(error.message));
    }
    const payload = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    if (!response.ok)
      throw new Error(
        typeof payload.detail === "string"
          ? payload.detail
          : copy.extractHttpFailed(response.status),
      );
    return payload;
  }
  async function extractPdfPageSmart(p: Any) {
    let browserError = "";
    if (state.pdf.doc) {
      try {
        const text = await extractPdfPageBrowser(p);
        if (text.trim()) return { text, source: copy.sourcePdfJsPage(p), warning: "" };
      } catch (error: Any) {
        browserError = error.message;
      }
    }
    const payload = await extractPdfApi(p);
    const text = payload.pages?.[0]?.text || "";
    if (text.trim())
      return {
        text,
        source: copy.sourcePyMuPage(p),
        warning: browserError ? copy.pdfJsFailed(browserError) : "",
      };
    return {
      text: "",
      source: copy.noTextLayer,
      warning: copy.needsOcrPage(p),
    };
  }
  async function extractPdfAllSmart() {
    let browserError = "";
    if (state.pdf.doc) {
      try {
        const parts = [];
        let nonempty = 0;
        for (let p = 1; p <= state.pdf.doc.numPages; p++) {
          const text = await extractPdfPageBrowser(p);
          if (text.trim()) nonempty++;
          parts.push(`${copy.pageMarker(p)}\n${text}`);
        }
        if (nonempty) return { text: parts.join("\n\n"), source: copy.sourcePdfJsAll, warning: "" };
      } catch (error: Any) {
        browserError = error.message;
      }
    }
    const payload = await extractPdfApi();
    const parts = (payload.pages || []).map(
      (item: Any) => `${copy.pageMarker(item.page)}\n${item.text || ""}`,
    );
    if (payload.has_text)
      return {
        text: parts.join("\n\n"),
        source: copy.sourcePyMuAll,
        warning: browserError ? copy.pdfJsFailed(browserError) : "",
      };
    return {
      text: parts.join("\n\n"),
      source: copy.noTextLayer,
      warning: copy.needsOcrAll,
    };
  }
  return {
    renderPdfCanvas,
    extractPdfPageBrowser,
    extractPdfApi,
    extractPdfPageSmart,
    extractPdfAllSmart,
  };
}
