/* Copyright 2026 Aaron John Schlosser, PhD. */

// Linking PDF pages to workspace records: which pages a record cites, which records a page cites, and loading a PDF's
// metadata. Moved verbatim from the legacy runtime; the runtime's state object and helpers are passed in as
// dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "allRows"
  | "applyRecordChanges"
  | "normalizePdfLinkChanges"
  | "openMessageModal"
  | "pdfLinks"
  | "renderView"
  | "shell"
  | "toast"
  | "tr"
  | "trf";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createPdfLinking(deps: Deps) {
  const {
    state,
    allRows,
    applyRecordChanges,
    normalizePdfLinkChanges,
    openMessageModal,
    pdfLinks,
    renderView,
    shell,
    toast,
    tr,
    trf,
  } = deps;
  function pdfDisplayTitle() {
    return state.pdf.title || state.pdf.name || "PDF";
  }
  function loadedPdfPagesForRecord(record: Any) {
    if (!state.pdf.name) return [];
    return pdfLinks(record)
      .filter((link: Any) => link.pdf_file === state.pdf.name)
      .map((link: Any) => Number(link.pdf_page))
      .filter((page: Any) => Number.isFinite(page) && page > 0)
      .sort((a: Any, b: Any) => a - b);
  }
  function allLinkedRowsForLoadedPdf() {
    if (!state.pdf.name) return [];
    const rows = [];
    for (const { file, record, index } of allRows()) {
      const pages = loadedPdfPagesForRecord(record);
      if (pages.length) rows.push({ file, record, index, pages });
    }
    return rows.sort(
      (a, b) =>
        (a.pages[0] || 0) - (b.pages[0] || 0) ||
        String(a.record.work || "").localeCompare(String(b.record.work || "")) ||
        String(a.record.record_id || "").localeCompare(String(b.record.record_id || "")),
    );
  }
  async function loadPdfMetadata(doc: Any, fileName: Any) {
    const fallback = String(fileName || "").replace(/\.pdf$/i, "");
    if (!doc) return { title: fallback, author: "" };
    try {
      const metadata = await doc.getMetadata();
      const info = metadata?.info || {};
      const xmp = metadata?.metadata;
      const title = String(
        info.Title || xmp?.get?.("dc:title") || xmp?.get?.("pdf:title") || fallback || "",
      ).trim();
      const author = String(
        info.Author || xmp?.get?.("dc:creator") || xmp?.get?.("pdf:author") || "",
      ).trim();
      return { title: title || fallback, author };
    } catch (error) {
      console.warn("Could not read PDF metadata", error);
      return { title: fallback, author: "" };
    }
  }
  function openPdfExplorerWorkspace() {
    window.dispatchEvent(
      new CustomEvent("derridai:navigate-native", {
        detail: { path: "/pdf?mode=explorer", runtimeView: "pdf" },
      }),
    );
  }
  function openLoadedPdfPage(page: Any) {
    if (!state.pdf.doc && !state.pdf.file) return toast(tr("pdf.link.open_first_explorer"));
    const max = state.pdf.doc?.numPages || Number(page) || 1;
    state.pdf.page = Math.max(1, Math.min(max, Number(page) || 1));
    state.pdf.text = "";
    state.pdf.extractError = "";
    state.pdf.extractionSource = "";
    openPdfExplorerWorkspace();
  }
  function linkedPdfRows(page = state.pdf.page) {
    return allRows().filter(({ record }: Any) =>
      pdfLinks(record).some((link: Any) => {
        if (Number(link.pdf_page) !== Number(page)) return false;
        return !state.pdf.name || link.pdf_file === state.pdf.name;
      }),
    );
  }
  async function linkPdfPage(file: Any, index: Any, page: Any) {
    if (!state.pdf.name) return toast(tr("pdf.link.open_first"));
    const record = file.records[index];
    let links = pdfLinks(record);
    const target = { pdf_file: state.pdf.name, pdf_page: Number(page) };
    if (
      links.some(
        (link: Any) =>
          link.pdf_file === target.pdf_file && Number(link.pdf_page) === target.pdf_page,
      )
    )
      return toast(trf("pdf.link.already", { page }));
    if (links.length && links.some((link: Any) => link.pdf_file !== target.pdf_file)) {
      if (
        !(await openMessageModal({
          title: tr("pdf.link.replace_title"),
          message: trf("pdf.link.replace_message", {
            current: links[0].pdf_file,
            next: target.pdf_file,
          }),
          tone: "danger",
          confirmLabel: tr("pdf.link.replace_confirm"),
          cancelLabel: tr("common.cancel"),
        }))
      )
        return;
      links = [];
    }
    const next = [...links, target].sort((a, b) => a.pdf_page - b.pdf_page);
    const count = applyRecordChanges(file, index, normalizePdfLinkChanges(record, next), {
      source: "pdf_link",
    });
    shell();
    renderView();
    toast(count ? trf("pdf.link.linked", { page }) : tr("pdf.link.unchanged"));
  }
  function unlinkPdfLink(file: Any, index: Any, link: Any, { stayInPdf = false } = {}) {
    const record = file?.records?.[index];
    if (!record) return;
    const links = pdfLinks(record);
    const next = links.filter(
      (item: Any) =>
        !(item.pdf_file === link.pdf_file && Number(item.pdf_page) === Number(link.pdf_page)),
    );
    if (next.length === links.length) return toast(tr("pdf.link.not_found"));
    const count = applyRecordChanges(file, index, normalizePdfLinkChanges(record, next), {
      source: "pdf_unlink",
    });
    if (stayInPdf) window.dispatchEvent(new CustomEvent("derridai:pdf-explorer-refresh"));
    else {
      shell();
      renderView();
    }
    toast(
      count
        ? trf("pdf.link.unlinked", {
            file: link.pdf_file,
            page: link.pdf_page,
          })
        : tr("pdf.link.unchanged"),
    );
  }
  function unlinkAllPdfLinks(file: Any, index: Any) {
    const record = file?.records?.[index];
    if (!record || !pdfLinks(record).length) return toast(tr("pdf.link.none"));
    const count = applyRecordChanges(file, index, normalizePdfLinkChanges(record, []), {
      source: "pdf_unlink",
    });
    shell();
    renderView();
    toast(count ? tr("pdf.link.all_removed") : tr("pdf.link.none_changed"));
  }
  return {
    pdfDisplayTitle,
    loadedPdfPagesForRecord,
    allLinkedRowsForLoadedPdf,
    loadPdfMetadata,
    openPdfExplorerWorkspace,
    openLoadedPdfPage,
    linkedPdfRows,
    linkPdfPage,
    unlinkPdfLink,
    unlinkAllPdfLinks,
  };
}
