/* Copyright 2026 Aaron John Schlosser, PhD. */

import { fullCitation } from "./citations";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";
import { esc, icon } from "./html";
import { highlight } from "./recordFormatting";

// The PDF Explorer, drawn as an HTML string into the runtime surface, with the page rendering and text extraction it
// uses. Moved verbatim from the legacy runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "activeFile"
  | "allLinkedRowsForLoadedPdf"
  | "cleanPdfPageWithLlm"
  | "defaultProviderProfile"
  | "draftPdfPageWithLlm"
  | "evidenceIsSelected"
  | "linkPdfPage"
  | "linkPdfPageWithLlm"
  | "linkedPdfRows"
  | "loadPdfMetadata"
  | "loadedPdfPagesForRecord"
  | "lookupRecord"
  | "navigateTo"
  | "openMessageModal"
  | "pages"
  | "pdfDisplayTitle"
  | "persistCurrentPdfAsset"
  | "providerDisplayName"
  | "recordOptionForKey"
  | "recordOptionLabel"
  | "renderView"
  | "reviewKey"
  | "searchRecordOptions"
  | "selectedIndex"
  | "selectedRecord"
  | "shell"
  | "syncUrl"
  | "toast"
  | "tr"
  | "unlinkPdfLink"
  | "workspaceEvidenceSelectionKey";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createPdfExplorerRenderer(deps: Deps) {
  const {
    state,
    activeFile,
    allLinkedRowsForLoadedPdf,
    cleanPdfPageWithLlm,
    defaultProviderProfile,
    draftPdfPageWithLlm,
    evidenceIsSelected,
    linkPdfPage,
    linkPdfPageWithLlm,
    linkedPdfRows,
    loadPdfMetadata,
    loadedPdfPagesForRecord,
    lookupRecord,
    navigateTo,
    openMessageModal,
    pages,
    pdfDisplayTitle,
    persistCurrentPdfAsset,
    providerDisplayName,
    recordOptionForKey,
    recordOptionLabel,
    renderView,
    reviewKey,
    searchRecordOptions,
    selectedIndex,
    selectedRecord,
    shell,
    syncUrl,
    toast,
    tr,
    unlinkPdfLink,
    workspaceEvidenceSelectionKey,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  function renderPdf(main: Any) {
    if (state.view === "pdf") syncUrl({ replace: true });
    const loaded = Boolean(state.pdf.file);
    const canRender = Boolean(state.pdf.doc);
    const extractReady = Boolean(state.pdf.doc || state.pdf.file);
    const linked = loaded ? linkedPdfRows(state.pdf.page) : [];
    const allRelated = loaded ? allLinkedRowsForLoadedPdf() : [];
    const relatedQuery = String(state.pdf.relatedSearch || "")
      .trim()
      .toLocaleLowerCase();
    const related = allRelated.filter(
      ({ file, record, pages }: Any) =>
        !relatedQuery ||
        [
          file.name,
          record.record_id,
          record.work,
          record.document_author,
          record.inline_citation,
          record.full_citation,
          pages.join(" "),
        ].some((value) =>
          String(value || "")
            .toLocaleLowerCase()
            .includes(relatedQuery),
        ),
    );
    const selectedFile = activeFile();
    const selected = selectedRecord();
    const hasRecordOptions = state.files.some((file: Any) => file.records.length > 0);
    const currentRecordKey =
      selectedFile && selected ? `${selectedFile.id}::${selectedIndex(selectedFile)}` : "";
    const currentOption =
      selectedFile && selected
        ? {
            value: currentRecordKey,
            label: recordOptionLabel(selectedFile, selected, selectedIndex(selectedFile)),
          }
        : null;
    const selectedPdfPages = selected ? loadedPdfPagesForRecord(selected) : [];
    const selectedRelated = Boolean(selectedFile && selected && selectedPdfPages.length);
    const pdfTitle = pdfDisplayTitle();
    const relatedWorks = [
      ...new Set(allRelated.map((item: Any) => String(item.record.work || "")).filter(Boolean)),
    ].sort((a: Any, b: Any) => a.localeCompare(b));

    const pdfProvider = defaultProviderProfile();
    main.innerHTML = `<section class="card pdf-document-header">
    <input id="pdfInput" type="file" accept="application/pdf" hidden>
    <div class="pdf-document-primary">
      <button class="btn primary" id="openPdf">${icon("pdf")}${loaded ? "Open another" : "Open PDF"}</button>
      <div class="pdf-document-title">${loaded ? `<span>PDF document</span><h2>${esc(pdfTitle)}</h2><p>${esc(state.pdf.name)}${state.pdf.author ? ` · ${esc(state.pdf.author)}` : ""}${state.pdf.doc ? ` · ${state.pdf.doc.numPages} pages` : ""}</p>` : `<span>PDF Explorer</span><h2>Open a source PDF</h2><p>Render pages, extract text, connect pages to records, and run LLM-assisted source workflows.</p>`}</div>
      ${loaded ? `<div class="pdf-document-status"><span><b>${relatedWorks.length}</b> linked works</span><span><b>${allRelated.length}</b> linked records</span><span><b>${linked.length}</b> on this page</span></div>` : ""}
    </div>
    ${
      loaded
        ? `<div class="pdf-command-row">
      <div class="pdf-page-nav"><button class="btn small icon-only" id="pdfPrev" ${state.pdf.page <= 1 ? "disabled" : ""}>←</button><label><span>Page</span><input class="control pdf-page-input" id="pdfPageInput" type="number" min="1" max="${state.pdf.doc?.numPages || 999999}" value="${state.pdf.page}"></label><span class="pdf-page-total">/ ${state.pdf.doc?.numPages || "?"}</span><button class="btn small" id="pdfGo">Go</button><button class="btn small icon-only" id="pdfNext" ${state.pdf.doc && state.pdf.page >= state.pdf.doc.numPages ? "disabled" : ""}>→</button></div>
      <div class="pdf-command-divider"></div>
      <div class="pdf-view-actions"><button class="btn small icon-only" id="pdfRotateLeft" title="Rotate left 90°">↶</button><button class="btn small icon-only" id="pdfRotateRight" title="Rotate right 90°">↷</button><span class="note">${state.pdf.rotation ? `${state.pdf.rotation}°` : "upright"}</span></div>
      <div class="pdf-command-divider"></div>
      <button class="btn small" id="extractPage" ${extractReady ? "" : "disabled"}>Extract page text</button>
      <details class="pdf-toolbar-menu"><summary class="btn small">More text tools</summary><div class="pdf-toolbar-menu-popover"><button class="btn small" id="extractAll" ${extractReady ? "" : "disabled"}>Extract all text</button></div></details>
      <details class="pdf-toolbar-menu llm-menu"><summary class="btn small soft">${icon("spark")}LLM tools</summary><div class="pdf-toolbar-menu-popover"><div class="pdf-menu-context"><b>${esc(providerDisplayName(pdfProvider))}</b><span>Each action lets you choose provider, model, parameters, and run mode.</span></div><button class="btn small" id="pdfLlmClean" ${extractReady ? "" : "disabled"}>Clean current page text</button><button class="btn small" id="pdfLlmDraft" ${extractReady ? "" : "disabled"}>Create draft record</button><button class="btn small" id="pdfLlmLink" ${state.files.length ? "" : "disabled"}>Match & link page to record</button><button class="btn small" id="pdfProviders">${icon("gear")}Manage LLM providers</button></div></details><button class="btn small primary" id="pdfCorpusBuilder">${icon("spark")}Build record set</button>
    </div>
    <div class="pdf-context-row"><div class="pdf-context-pill"><span>Source</span><b>p. ${state.pdf.page}</b></div><div class="pdf-context-pill"><span>Works</span><b>${esc(relatedWorks.slice(0, 2).join(" · ") || "None linked")}${relatedWorks.length > 2 ? ` +${relatedWorks.length - 2}` : ""}</b></div><div class="pdf-context-pill"><span>Current-page records</span><b>${linked.length}</b></div>${selectedRelated ? `<button class="btn soft" id="returnToSelectedRecord">${icon("record")}Back to ${esc(selected.record_id || "record")}</button>` : ""}</div>`
        : ""
    }
  </section>
  ${
    loaded
      ? `<section class="pdfgrid pdfgrid-v2">
    <article class="card pdf-viewer-card">
      <div class="cardhead pdf-viewer-head"><div><b>Page ${state.pdf.page}</b><div class="note">${canRender ? "PDF.js renderer" : "Browser fallback"} · ${linked.length} linked record${linked.length === 1 ? "" : "s"} on this page</div></div><span class="pdf-view-badge">${state.pdf.rotation ? `${state.pdf.rotation}° rotation` : "Fit width"}</span></div>
      ${canRender ? `<div class="pdf-canvas-wrap"><canvas id="pdfCanvas"></canvas><div class="pdf-render-status" id="pdfRenderStatus"></div></div>` : `<iframe class="pdf-frame" id="pdfFrame" title="${esc(pdfTitle)}" src="${esc(state.pdf.url)}#page=${state.pdf.page}"></iframe>`}
    </article>

    <aside class="pdf-side-stack">
      <article class="card pdf-text-card">
        <div class="cardhead"><div><b>Page text</b><div class="note">${state.pdf.extractionSource ? `Source: ${esc(state.pdf.extractionSource)}` : "Extract the current page, then optionally clean it with an LLM."}</div></div><div class="search"><input id="pdfSearch" value="${esc(state.pdf.search || "")}" placeholder="Search page text"></div></div>
        ${state.pdf.extractError ? `<div class="info warn" style="margin:14px">${esc(state.pdf.extractError)}</div>` : ""}
        <div class="pdftext">${highlight(state.pdf.text || "", state.pdf.search || "") || '<span class="note">Use “Extract current page” or “Extract all text.” If both PDF.js and PyMuPDF find no text, the page likely requires OCR.</span>'}</div>
      </article>

      <article class="card panel pdf-current-links">
        <div class="toolbar compact-toolbar"><div><b>Records on page ${state.pdf.page}</b><div class="note">${linked.length} linked record${linked.length === 1 ? "" : "s"}</div></div></div>
        <div class="pdf-link-controls">
          <div class="autocomplete"><input class="control" id="pdfRecordSearch" autocomplete="off" placeholder="Search record ID, work, or source file" value="${esc(currentOption?.label || "")}"><input type="hidden" id="pdfRecordKey" value="${esc(currentOption?.value || "")}"><div class="autocomplete-list hidden" id="pdfRecordSuggestions"></div></div>
          <button class="btn" id="linkCurrentPdf" ${hasRecordOptions ? "" : "disabled"}>${icon("plus")}Link page ${state.pdf.page}</button>
        </div>
        <div class="pdf-linked-list">${
          linked
            .map(
              ({ file, record, index }: Any) => `<div class="linked-record-row">
          <button class="linked-record" data-linked-file="${file.id}" data-linked-index="${index}"><b>${esc(record.record_id || `Record ${index + 1}`)}</b><span>${esc(record.work || file.name)} · ${esc(record.inline_citation || pages(record))}</span></button>
          <div class="tools"><button class="btn small" data-copy-row-key="${esc(reviewKey(file, index))}">${icon("copy")}Copy</button><button class="btn small" data-cite-row-key="${esc(reviewKey(file, index))}" data-cite-kind="inline" title="${esc(tr("ui.copy_inline", "Copy inline citation"))}">Inline</button><button class="btn small" data-cite-row-key="${esc(reviewKey(file, index))}" data-cite-kind="full" title="${esc(tr("ui.copy_full", "Copy full citation"))}">Full</button><button class="btn small ${evidenceIsSelected(workspaceEvidenceSelectionKey(file, index)) ? "soft" : ""}" data-toggle-workspace-evidence="${esc(reviewKey(file, index))}" title="${esc(evidenceIsSelected(workspaceEvidenceSelectionKey(file, index)) ? tr("ui.remove_evidence", "Remove from evidence") : tr("ui.add_evidence", "Add to evidence"))}">${evidenceIsSelected(workspaceEvidenceSelectionKey(file, index)) ? icon("check") : icon("plus")}Evidence</button><button class="btn small" data-linked-open-file="${file.id}" data-linked-open-index="${index}">${icon("record")}Open record</button><button class="btn small danger unlink-pdf-link" data-unlink-file="${file.id}" data-unlink-index="${index}" title="Unlink record from PDF">${icon("close")}Unlink</button></div>
        </div>`,
            )
            .join("") || '<div class="note">No records linked to this page yet.</div>'
        }</div>
      </article>

      <article class="card panel pdf-related-records">
        <div class="toolbar compact-toolbar"><div><b>Records linked anywhere in this PDF</b><div class="note">${allRelated.length} record${allRelated.length === 1 ? "" : "s"} · jump directly between source pages and records</div></div></div>
        <div class="search pdf-related-search"><input id="pdfRelatedSearch" value="${esc(state.pdf.relatedSearch || "")}" placeholder="Filter linked records"></div>
        <div class="pdf-related-list">${
          related
            .slice(0, 80)
            .map(
              ({ file, record, index, pages: recordPages }: Any) => `<div class="pdf-related-row">
          <button class="pdf-related-record" data-related-record-file="${file.id}" data-related-record-index="${index}"><b>${esc(record.record_id || `Record ${index + 1}`)}</b><span>${esc(record.work || file.name)}</span><small>${esc(fullCitation(record) || file.name)}</small></button>
          <div class="pdf-related-pages"><button class="copy-record-mini" data-copy-row-key="${esc(reviewKey(file, index))}" title="Copy entire record">${icon("copy")}</button><button class="copy-record-mini" data-cite-row-key="${esc(reviewKey(file, index))}" data-cite-kind="inline" title="${esc(tr("ui.copy_inline", "Copy inline citation"))}">I</button><button class="copy-record-mini" data-cite-row-key="${esc(reviewKey(file, index))}" data-cite-kind="full" title="${esc(tr("ui.copy_full", "Copy full citation"))}">F</button><button class="copy-record-mini ${evidenceIsSelected(workspaceEvidenceSelectionKey(file, index)) ? "selected" : ""}" data-toggle-workspace-evidence="${esc(reviewKey(file, index))}" title="${esc(evidenceIsSelected(workspaceEvidenceSelectionKey(file, index)) ? tr("ui.remove_evidence", "Remove from evidence") : tr("ui.add_evidence", "Add to evidence"))}">${evidenceIsSelected(workspaceEvidenceSelectionKey(file, index)) ? "✓" : "+"}</button>${recordPages.map((page: Any) => `<button class="pdf-page-chip ${Number(page) === Number(state.pdf.page) ? "active" : ""}" data-related-page="${page}" title="Open PDF page ${page}">p. ${page}</button>`).join("")}</div>
        </div>`,
            )
            .join("") || '<div class="note">No linked records match this filter.</div>'
        }</div>
        ${related.length > 80 ? `<div class="note" style="padding-top:8px">Showing first 80 of ${related.length} matches. Narrow the filter to see a specific record.</div>` : ""}
      </article>
    </aside>
  </section>`
      : `<section class="empty"><div class="drop"><div class="drop-icon">${icon("pdf")}</div><h1>PDF Explorer</h1><p>Open a PDF to render pages, read its embedded title metadata, extract text, and move directly between linked PDF pages and corpus records.</p><button class="btn primary" id="openPdf2">${icon("pdf")}Choose PDF</button></div></section>`
  }`;

    document.querySelector("#openPdf").onclick = () => document.querySelector("#pdfInput").click();
    document
      .querySelector("#openPdf2")
      ?.addEventListener("click", () => document.querySelector("#pdfInput").click());
    document.querySelector("#pdfInput").onchange = async (e: Any) => {
      const file = e.target.files[0];
      if (!file) return;
      const openButtons = [
        document.querySelector("#openPdf"),
        document.querySelector("#openPdf2"),
      ].filter(Boolean);
      const buttonState = openButtons.map((button) => ({ button, html: button.innerHTML }));
      for (const { button } of buttonState) {
        button.disabled = true;
        button.innerHTML = `<span class="spinner small-spinner"></span>Opening PDF…`;
      }
      try {
        if (state.pdf.url) URL.revokeObjectURL(state.pdf.url);
        const buffer = await file.arrayBuffer();
        state.pdf.file = file;
        state.pdf.url = URL.createObjectURL(new Blob([buffer], { type: "application/pdf" }));
        state.pdf.name = file.name;
        state.pdf.title = file.name.replace(/\.pdf$/i, "");
        state.pdf.author = "";
        state.pdf.page = 1;
        state.pdf.rotation = 0;
        state.pdf.text = "";
        state.pdf.search = "";
        state.pdf.relatedSearch = "";
        state.pdf.extractError = "";
        state.pdf.extractionSource = "";
        try {
          state.pdf.doc = await pdfjsLib.getDocument({ data: new Uint8Array(buffer.slice(0)) })
            .promise;
          const metadata = await loadPdfMetadata(state.pdf.doc, file.name);
          state.pdf.title = metadata.title || state.pdf.title;
          state.pdf.author = metadata.author || "";
        } catch (error: Any) {
          console.error("PDF.js initialization failed", error);
          state.pdf.doc = null;
          state.pdf.extractError = `PDF.js could not initialize (${error.message}). Rendering and extraction will use fallbacks where possible.`;
        }
        await persistCurrentPdfAsset();
        shell();
        renderView();
      } catch (error: Any) {
        console.error("Could not open PDF", error);
        await openMessageModal({
          title: "Could not open PDF",
          message: error.message || String(error),
          tone: "danger",
        });
        for (const { button, html } of buttonState) {
          if (button.isConnected) {
            button.disabled = false;
            button.innerHTML = html;
          }
        }
      }
    };

    if (!loaded) return;

    if (canRender) renderPdfCanvas(state.pdf.page);

    const setPage = (page: Any) => {
      const max = state.pdf.doc?.numPages || Math.max(1, page);
      state.pdf.page = Math.max(1, Math.min(max, Number(page) || 1));
      state.pdf.text = "";
      state.pdf.extractError = "";
      state.pdf.extractionSource = "";
      persistCurrentPdfAsset();
      syncUrl({ replace: true });
      renderPdf(main);
    };

    document.querySelector("#pdfRotateLeft")?.addEventListener("click", () => {
      state.pdf.rotation = (Number(state.pdf.rotation || 0) + 270) % 360;
      persistCurrentPdfAsset();
      renderPdf(main);
    });
    document.querySelector("#pdfRotateRight")?.addEventListener("click", () => {
      state.pdf.rotation = (Number(state.pdf.rotation || 0) + 90) % 360;
      persistCurrentPdfAsset();
      renderPdf(main);
    });
    document.querySelector("#pdfLlmClean")?.addEventListener("click", cleanPdfPageWithLlm);
    document.querySelector("#pdfLlmDraft")?.addEventListener("click", draftPdfPageWithLlm);
    document.querySelector("#pdfLlmLink")?.addEventListener("click", linkPdfPageWithLlm);
    document
      .querySelector("#pdfProviders")
      ?.addEventListener("click", () => navigateTo("providers"));
    document
      .querySelector("#pdfCorpusBuilder")
      ?.addEventListener("click", () =>
        window.dispatchEvent(new CustomEvent("derridai:pdf-builder")),
      );
    document
      .querySelector("#pdfPrev")
      ?.addEventListener("click", () => setPage(state.pdf.page - 1));
    document
      .querySelector("#pdfNext")
      ?.addEventListener("click", () => setPage(state.pdf.page + 1));
    document
      .querySelector("#pdfGo")
      ?.addEventListener("click", () => setPage(document.querySelector("#pdfPageInput").value));
    document.querySelector("#pdfPageInput")?.addEventListener("keydown", (e: Any) => {
      if (e.key === "Enter") {
        e.preventDefault();
        setPage(e.target.value);
      }
    });
    document
      .querySelector("#returnToSelectedRecord")
      ?.addEventListener("click", () =>
        navigateTo("record", { fileId: selectedFile.id, index: selectedIndex(selectedFile) }),
      );

    document.querySelector("#extractPage")?.addEventListener("click", async () => {
      const pageToExtract = Number(
        document.querySelector("#pdfPageInput")?.value || state.pdf.page,
      );
      state.pdf.page = Math.max(
        1,
        Math.min(state.pdf.doc?.numPages || pageToExtract, pageToExtract),
      );
      const button = document.querySelector("#extractPage");
      button.disabled = true;
      button.textContent = `Extracting page ${state.pdf.page}…`;
      try {
        const result = await extractPdfPageSmart(state.pdf.page);
        state.pdf.text = result.text;
        state.pdf.extractionSource = result.source;
        state.pdf.extractError = result.warning || "";
      } catch (error: Any) {
        state.pdf.extractError = error.message;
      }
      renderPdf(main);
    });
    document.querySelector("#extractAll")?.addEventListener("click", async () => {
      const button = document.querySelector("#extractAll");
      button.disabled = true;
      button.textContent = "Extracting…";
      try {
        const result = await extractPdfAllSmart();
        state.pdf.text = result.text;
        state.pdf.extractionSource = result.source;
        state.pdf.extractError = result.warning || "";
      } catch (error: Any) {
        state.pdf.extractError = error.message;
      }
      renderPdf(main);
    });

    const s = document.querySelector("#pdfSearch");
    if (s)
      s.oninput = (e: Any) => {
        const pos = e.target.selectionStart;
        state.pdf.search = e.target.value;
        renderPdf(main);
        requestAnimationFrame(() => {
          const x = document.querySelector("#pdfSearch");
          if (x) {
            x.focus();
            x.setSelectionRange(pos, pos);
          }
        });
      };

    const relatedSearch = document.querySelector("#pdfRelatedSearch");
    if (relatedSearch)
      relatedSearch.oninput = (e: Any) => {
        const pos = e.target.selectionStart;
        state.pdf.relatedSearch = e.target.value;
        renderPdf(main);
        requestAnimationFrame(() => {
          const next = document.querySelector("#pdfRelatedSearch");
          if (next) {
            next.focus();
            next.setSelectionRange(pos, pos);
          }
        });
      };

    const search = document.querySelector("#pdfRecordSearch");
    const hidden = document.querySelector("#pdfRecordKey");
    const suggestions = document.querySelector("#pdfRecordSuggestions");
    const renderSuggestions = () => {
      const q = search.value.trim();
      const matches = searchRecordOptions(q, 12);
      suggestions.innerHTML =
        matches
          .map(
            (option: Any) =>
              `<button type="button" class="autocomplete-option" data-record-key="${esc(option.value)}"><b>${esc(option.label.split(" · ")[1] || option.label)}</b><span>${esc(option.label)}</span></button>`,
          )
          .join("") || '<div class="autocomplete-empty">No matching records</div>';
      suggestions.classList.remove("hidden");
      suggestions.querySelectorAll("[data-record-key]").forEach(
        (button: Any) =>
          (button.onclick = () => {
            const option = recordOptionForKey(button.dataset.recordKey);
            if (option) {
              hidden.value = option.value;
              search.value = option.label;
            }
            suggestions.classList.add("hidden");
          }),
      );
    };
    search?.addEventListener("focus", renderSuggestions);
    search?.addEventListener("input", () => {
      hidden.value = "";
      renderSuggestions();
    });
    search?.addEventListener("keydown", (e: Any) => {
      if (e.key === "Escape") suggestions.classList.add("hidden");
    });
    document.addEventListener(
      "click",
      (e: Any) => {
        if (!e.target.closest(".autocomplete")) suggestions?.classList.add("hidden");
      },
      { once: true },
    );

    document.querySelector("#linkCurrentPdf")?.addEventListener("click", () => {
      let key = hidden.value;
      if (!key) {
        const exact = searchRecordOptions(search.value, 24).find(
          (option: Any) => option.label === search.value,
        );
        key = exact?.value || "";
      }
      const item = lookupRecord(key);
      if (item) linkPdfPage(item.file, item.index, state.pdf.page);
      else toast("Choose a record from the autocomplete list");
    });

    document.querySelectorAll("[data-linked-file],[data-linked-open-file]").forEach(
      (button: Any) =>
        (button.onclick = () => {
          const fileId = button.dataset.linkedFile || button.dataset.linkedOpenFile;
          const index = +(button.dataset.linkedIndex ?? button.dataset.linkedOpenIndex);
          navigateTo("record", { fileId, index });
        }),
    );
    document.querySelectorAll("[data-unlink-file]").forEach(
      (button: Any) =>
        (button.onclick = () => {
          const file = state.files.find((item: Any) => item.id === button.dataset.unlinkFile);
          if (file)
            unlinkPdfLink(
              file,
              +button.dataset.unlinkIndex,
              { pdf_file: state.pdf.name, pdf_page: state.pdf.page },
              { stayInPdf: true },
            );
        }),
    );
    document.querySelectorAll("[data-related-record-file]").forEach(
      (button: Any) =>
        (button.onclick = () => {
          navigateTo("record", {
            fileId: button.dataset.relatedRecordFile,
            index: +button.dataset.relatedRecordIndex,
          });
        }),
    );
    document
      .querySelectorAll("[data-related-page]")
      .forEach((button: Any) => (button.onclick = () => setPage(+button.dataset.relatedPage)));
  }
  async function renderPdfCanvas(pageNumber: Any) {
    const canvas = document.querySelector("#pdfCanvas");
    if (!canvas || !state.pdf.doc) return;
    const status = document.querySelector("#pdfRenderStatus");
    try {
      if (status) status.textContent = `Rendering page ${pageNumber}…`;
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
      if (status) status.textContent = `Could not render page ${pageNumber}: ${error.message}`;
    }
  }
  async function extractPdfPageBrowser(p: Any) {
    if (!state.pdf.doc) throw new Error("PDF.js is unavailable for this document.");
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
    if (!state.pdf.file)
      throw new Error("The PDF file is no longer available in this browser session.");
    const form = new FormData();
    form.append("file", state.pdf.file, state.pdf.name || "document.pdf");
    const url = page ? `/api/pdf/extract?page=${page}` : "/api/pdf/extract";
    let response;
    try {
      response = await fetch(url, { method: "POST", body: form });
    } catch (error: Any) {
      throw new Error(`PDF extraction API is unreachable: ${error.message}`);
    }
    const payload = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    if (!response.ok)
      throw new Error(
        typeof payload.detail === "string"
          ? payload.detail
          : `PDF extraction failed with HTTP ${response.status}`,
      );
    return payload;
  }
  async function extractPdfPageSmart(p: Any) {
    let browserError = "";
    if (state.pdf.doc) {
      try {
        const text = await extractPdfPageBrowser(p);
        if (text.trim()) return { text, source: `PDF.js (browser), page ${p}`, warning: "" };
      } catch (error: Any) {
        browserError = error.message;
      }
    }
    const payload = await extractPdfApi(p);
    const text = payload.pages?.[0]?.text || "";
    if (text.trim())
      return {
        text,
        source: `PyMuPDF (API fallback), page ${p}`,
        warning: browserError ? `PDF.js failed: ${browserError}` : "",
      };
    return {
      text: "",
      source: "No extractable text layer",
      warning: `Neither PDF.js nor PyMuPDF found extractable text on page ${p}. It likely requires OCR.`,
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
          parts.push(`--- Page ${p} ---\n${text}`);
        }
        if (nonempty)
          return { text: parts.join("\n\n"), source: "PDF.js (browser), all pages", warning: "" };
      } catch (error: Any) {
        browserError = error.message;
      }
    }
    const payload = await extractPdfApi();
    const parts = (payload.pages || []).map(
      (item: Any) => `--- Page ${item.page} ---\n${item.text || ""}`,
    );
    if (payload.has_text)
      return {
        text: parts.join("\n\n"),
        source: "PyMuPDF (API fallback), all pages",
        warning: browserError ? `PDF.js failed: ${browserError}` : "",
      };
    return {
      text: parts.join("\n\n"),
      source: "No extractable text layer",
      warning: "Neither PDF.js nor PyMuPDF found extractable text. Image-only pages require OCR.",
    };
  }
  return {
    renderPdf,
    renderPdfCanvas,
    extractPdfPageBrowser,
    extractPdfApi,
    extractPdfPageSmart,
    extractPdfAllSmart,
  };
}
