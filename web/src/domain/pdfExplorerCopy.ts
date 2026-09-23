/* Copyright 2026 Aaron John Schlosser, PhD. */

export type Tr = (key: string, fallback?: string) => string;
export type Trf = (key: string, fallback: string, values?: Record<string, unknown>) => string;

/** User-visible PDF Explorer copy. PdfExplorerSurface owns the UI; this module owns the strings. */
export function createPdfExplorerCopy(tr: Tr, trf: Trf) {
  return {
    openPdf: tr("pdf.open", "Open PDF"),
    openAnother: tr("pdf.open_another", "Open another"),
    opening: tr("pdf.opening", "Opening PDF…"),
    document: tr("pdf.document", "PDF document"),
    explorer: tr("pdf.explorer", "PDF Explorer"),
    openSource: tr("pdf.open_source", "Open a source PDF"),
    openHelp: tr(
      "pdf.open_help",
      "Render pages, extract text, connect pages to records, and run LLM-assisted source workflows.",
    ),
    emptyHelp: tr(
      "pdf.empty_help",
      "Open a PDF to render pages, read its embedded title metadata, extract text, and move directly between linked PDF pages and corpus records.",
    ),
    choosePdf: tr("pdf.choose", "Choose PDF"),
    pagesCount: (count: number) => trf("pdf.pages_count", "{count} pages", { count }),
    linkedWorks: tr("pdf.linked_works", "linked works"),
    linkedRecords: tr("pdf.linked_records", "linked records"),
    onThisPage: tr("pdf.on_this_page", "on this page"),
    page: tr("record.page", "Page"),
    go: tr("ui.go", "Go"),
    rotateLeft: tr("pdf.rotate_left", "Rotate left 90°"),
    rotateRight: tr("pdf.rotate_right", "Rotate right 90°"),
    upright: tr("pdf.upright", "upright"),
    rotation: (deg: number) => trf("pdf.rotation_deg", "{deg}° rotation", { deg }),
    rotationAmount: (deg: number) => trf("pdf.rotation_amount", "{deg}°", { deg }),
    fitWidth: tr("pdf.fit_width", "Fit width"),
    extractPage: tr("pdf.extract_page", "Extract page text"),
    extractingPage: (page: number) => trf("pdf.extracting_page", "Extracting page {page}…", { page }),
    moreTextTools: tr("pdf.more_text_tools", "More text tools"),
    extractAll: tr("pdf.extract_all", "Extract all text"),
    extracting: tr("pdf.extracting", "Extracting…"),
    llmTools: tr("pdf.llm_tools", "LLM tools"),
    llmToolsHelp: tr(
      "pdf.llm_tools_help",
      "Each action lets you choose provider, model, parameters, and run mode.",
    ),
    cleanPage: tr("pdf.clean_page", "Clean current page text"),
    draftRecord: tr("pdf.draft_record", "Create draft record"),
    matchLink: tr("pdf.match_link", "Match & link page to record"),
    manageProviders: tr("pdf.manage_providers", "Manage LLM providers"),
    buildRecordSet: tr("pdf.build_record_set", "Build record set"),
    source: tr("pdf.source", "Source"),
    works: tr("dashboard.works", "Works"),
    noneLinked: tr("pdf.none_linked", "None linked"),
    currentPageRecords: tr("pdf.current_page_records", "Current-page records"),
    backTo: (id: string) => trf("pdf.back_to", "Back to {id}", { id }),
    recordFallback: tr("pdf.record_fallback", "Record"),
    renderer: tr("pdf.renderer_pdfjs", "PDF.js renderer"),
    fallbackRenderer: tr("pdf.renderer_fallback", "Browser fallback"),
    linkedOnPage: (count: number) =>
      trf("pdf.linked_on_page", "{count} linked record(s) on this page", { count }),
    pageText: tr("pdf.page_text", "Page text"),
    extractThenClean: tr(
      "pdf.extract_then_clean",
      "Extract the current page, then optionally clean it with an LLM.",
    ),
    sourceLabel: (source: string) => trf("pdf.extraction_source", "Source: {source}", { source }),
    searchPage: tr("pdf.search_page", "Search page text"),
    emptyExtract: tr(
      "pdf.empty_extract",
      "Use “Extract current page” or “Extract all text.” If both PDF.js and PyMuPDF find no text, the page likely requires OCR.",
    ),
    recordsOnPage: (page: number) => trf("pdf.records_on_page", "Records on page {page}", { page }),
    linkedCount: (count: number) => trf("pdf.linked_count", "{count} linked record(s)", { count }),
    searchRecord: tr("pdf.search_record", "Search record ID, work, or source file"),
    noMatching: tr("pdf.no_matching_records", "No matching records"),
    linkPage: (page: number) => trf("pdf.link_page", "Link page {page}", { page }),
    copy: tr("ui.copy", "Copy"),
    inline: tr("ui.inline", "Inline"),
    full: tr("ui.full", "Full"),
    evidence: tr("ui.evidence", "Evidence"),
    openRecord: tr("record.open", "Open record"),
    unlink: tr("pdf.unlink", "Unlink"),
    unlinkTitle: tr("pdf.unlink_title", "Unlink record from PDF"),
    noLinkedYet: tr("pdf.no_linked_yet", "No records linked to this page yet."),
    recordsAnywhere: tr("pdf.records_anywhere", "Records linked anywhere in this PDF"),
    relatedNote: (count: number) =>
      trf(
        "pdf.related_note",
        "{count} record(s) · jump directly between source pages and records",
        { count },
      ),
    filterLinked: tr("pdf.filter_linked", "Filter linked records"),
    copyEntire: tr("pdf.copy_entire", "Copy entire record"),
    openPdfPage: (page: number) => trf("pdf.open_page", "Open PDF page {page}", { page }),
    noFilterMatch: tr("pdf.no_filter_match", "No linked records match this filter."),
    showingFirst: (shown: number, total: number) =>
      trf(
        "pdf.showing_first",
        "Showing first {shown} of {total} matches. Narrow the filter to see a specific record.",
        { shown, total },
      ),
    recordN: (n: number) => trf("dashboard.record_n", "Record {n}", { n }),
    chooseAutocomplete: tr("pdf.choose_autocomplete", "Choose a record from the autocomplete list"),
    couldNotOpen: tr("pdf.could_not_open", "Could not open PDF"),
    pdfJsUnavailable: tr(
      "pdf.extract.pdfjs_unavailable",
      "PDF.js is unavailable for this document.",
    ),
    jsInitFailed: (error: string) =>
      trf(
        "pdf.js_init_failed",
        "PDF.js could not initialize ({error}). Rendering and extraction will use fallbacks where possible.",
        { error },
      ),
    rendering: (page: number) => trf("pdf.rendering", "Rendering page {page}…", { page }),
    renderFailed: (page: number, error: string) =>
      trf("pdf.render_failed", "Could not render page {page}: {error}", { page, error }),
    fileGone: tr(
      "pdf.extract.file_gone",
      "The PDF file is no longer available in this browser session.",
    ),
    apiUnreachable: (error: string) =>
      trf("pdf.extract.api_unreachable", "PDF extraction API is unreachable: {error}", { error }),
    extractHttpFailed: (status: string | number) =>
      trf("pdf.extract.http_failed", "PDF extraction failed with HTTP {status}", { status }),
    sourcePdfJsPage: (page: number) =>
      trf("pdf.extract.source_pdfjs_page", "PDF.js (browser), page {page}", { page }),
    sourcePyMuPage: (page: number) =>
      trf("pdf.extract.source_pymu_page", "PyMuPDF (API fallback), page {page}", { page }),
    sourcePdfJsAll: tr("pdf.extract.source_pdfjs_all", "PDF.js (browser), all pages"),
    sourcePyMuAll: tr("pdf.extract.source_pymu_all", "PyMuPDF (API fallback), all pages"),
    noTextLayer: tr("pdf.extract.no_text_layer", "No extractable text layer"),
    pdfJsFailed: (error: string) => trf("pdf.extract.pdfjs_failed", "PDF.js failed: {error}", { error }),
    needsOcrPage: (page: number) =>
      trf(
        "pdf.extract.needs_ocr_page",
        "Neither PDF.js nor PyMuPDF found extractable text on page {page}. It likely requires OCR.",
        { page },
      ),
    needsOcrAll: tr(
      "pdf.extract.needs_ocr_all",
      "Neither PDF.js nor PyMuPDF found extractable text. Image-only pages require OCR.",
    ),
    pageMarker: (page: number) => trf("pdf.extract.page_marker", "--- Page {page} ---", { page }),
  };
}
