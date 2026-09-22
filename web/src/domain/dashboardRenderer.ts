/* Copyright 2026 Aaron John Schlosser, PhD. */

import { mlaPageSpan } from "./citations";
import { esc, icon } from "./html";
import { commonWorkValue, workCoverUrl } from "./workMetadata";

// The home dashboard, drawn as an HTML string into the runtime surface. Moved verbatim from the legacy runtime; the
// runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "allRows"
  | "api"
  | "applyUiTheme"
  | "canAccessPage"
  | "compactNumber"
  | "dashboardMetricBody"
  | "dbSearchWhere"
  | "decorateDisabledControls"
  | "defaultProviderProfile"
  | "formatTimestamp"
  | "hasCapability"
  | "isResearcher"
  | "label"
  | "memoCorpus"
  | "mountOperationsPanelHost"
  | "navigateTo"
  | "openAnnotationsWorkspaceRecord"
  | "openDatabaseCreationFromResearch"
  | "persistPrefs"
  | "pieShareSeries"
  | "providerDisplayName"
  | "recentAnnotations"
  | "recentAuditChanges"
  | "recordStores"
  | "refreshServerAnnotations"
  | "refreshStoreWorks"
  | "refreshStores"
  | "relativeTime"
  | "renderCorpusBuildsHomeCard"
  | "renderOperationsPanel"
  | "researcherDbRecords"
  | "responseCacheStore"
  | "searchByMetadata"
  | "syncUrl"
  | "toast"
  | "tr"
  | "trf"
  | "uid"
  | "wireCorpusBuildsHomeCard"
  | "workIndex"
  | "workInsightMetrics";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createDashboardRenderer(deps: Deps) {
  const {
    state,
    allRows,
    api,
    applyUiTheme,
    canAccessPage,
    compactNumber,
    dashboardMetricBody,
    dbSearchWhere,
    decorateDisabledControls,
    defaultProviderProfile,
    formatTimestamp,
    hasCapability,
    isResearcher,
    label,
    memoCorpus,
    mountOperationsPanelHost,
    navigateTo,
    openAnnotationsWorkspaceRecord,
    openDatabaseCreationFromResearch,
    persistPrefs,
    pieShareSeries,
    providerDisplayName,
    recentAnnotations,
    recentAuditChanges,
    recordStores,
    refreshServerAnnotations,
    refreshStoreWorks,
    refreshStores,
    relativeTime,
    renderCorpusBuildsHomeCard,
    renderOperationsPanel,
    researcherDbRecords,
    responseCacheStore,
    searchByMetadata,
    syncUrl,
    toast,
    tr,
    trf,
    uid,
    wireCorpusBuildsHomeCard,
    workIndex,
    workInsightMetrics,
  } = deps;
  function dashboardTotals() {
    if (isResearcher()) {
      const stores = recordStores();
      const active = stores.find((store: Any) => store.name === state.activeStore) || stores[0];
      return {
        records: Number(active?.count || 0),
        works: state.storeWorkStats.length,
        flagged: 0,
        files: 0,
        changes: 0,
        dbs: stores.length,
        dbRecords: stores.reduce((sum: Any, store: Any) => sum + (Number(store.count) || 0), 0),
        cacheResponses: 0,
      };
    }
    const corpus = memoCorpus("dashboard-totals", () => {
      let flagged = 0,
        changes = 0;
      const works = new Set();
      for (const { record } of allRows()) {
        const work = String(record.work || "").trim();
        if (work) works.add(work);
        if (record.needs_review) flagged++;
        changes += Array.isArray(record.updates) ? record.updates.length : 0;
      }
      return {
        records: allRows().length,
        works: works.size,
        flagged,
        files: state.files.length,
        changes,
      };
    });
    const stores = recordStores();
    return {
      ...corpus,
      dbs: stores.length,
      dbRecords: stores.reduce((sum: Any, store: Any) => sum + (Number(store.count) || 0), 0),
      cacheResponses: Number(responseCacheStore()?.count || 0),
    };
  }
  function dashboardWorkspaceRecordTarget(pointer: Any) {
    if (!pointer || pointer.kind !== "workspace") return null;
    const file = state.files.find((item: Any) => item.id === pointer.fileId);
    const index = Number(pointer.index);
    if (!file || !Number.isInteger(index) || index < 0 || index >= file.records.length) return null;
    return { record: file.records[index], target: { kind: "workspace", fileId: file.id, index } };
  }
  async function dashboardRecordPreview() {
    const pointer = state.lastViewedRecord;
    if (pointer?.kind === "workspace") {
      const found = dashboardWorkspaceRecordTarget(pointer);
      if (found) return { ...found, lastViewed: true };
    }
    if (pointer?.kind === "database" && pointer.store && pointer.id) {
      let record = (state.activeStore === pointer.store ? researcherDbRecords() : []).find(
        (item: Any) => String(item._chroma_id || item.record_id || "") === String(pointer.id),
      );
      if (!record) {
        try {
          record = await api(
            `/api/stores/${encodeURIComponent(pointer.store)}/records/${encodeURIComponent(pointer.id)}`,
          );
        } catch {
          record = null;
        }
      }
      if (record)
        return {
          record,
          target: { kind: "database", store: pointer.store, id: String(pointer.id) },
          lastViewed: true,
        };
    }
    if (isResearcher()) {
      const current =
        recordStores().find((store: Any) => store.name === state.activeStore) || recordStores()[0];
      if (!current?.name || !Number(current.count || 0))
        return { record: null, target: null, lastViewed: false };
      try {
        const offset = Math.floor(Math.random() * Math.max(1, Number(current.count || 0)));
        const data = await api(
          `/api/stores/${encodeURIComponent(current.name)}/records?limit=1&offset=${offset}`,
        );
        const record = (data.records || [])[0] || null;
        if (record) {
          const id = String(record._chroma_id || record.record_id || "");
          return {
            record,
            target: { kind: "database", store: current.name, id },
            lastViewed: false,
          };
        }
      } catch (error: Any) {
        console.warn("Could not choose a random dashboard record", error);
      }
      return { record: null, target: null, lastViewed: false };
    }
    const choices = allRows();
    if (!choices.length) return { record: null, target: null, lastViewed: false };
    const item = choices[Math.floor(Math.random() * choices.length)];
    return {
      record: item.record,
      target: { kind: "workspace", fileId: item.file.id, index: item.index },
      lastViewed: false,
    };
  }
  /** Opens the record a shared (server) annotation is attached to, in the store it belongs to. */
  function openSharedAnnotationRecord(store: Any, recordId: Any) {
    openAnnotationsWorkspaceRecord({ server: true, source: store, record_id: recordId });
  }
  async function renderDashboard(main: Any) {
    if (isResearcher()) {
      try {
        await refreshStores();
        if (!state.activeStore) state.activeStore = recordStores()[0]?.name || "";
        if (state.activeStore) await refreshStoreWorks(true);
      } catch (error: Any) {
        console.warn("Could not refresh researcher dashboard data", error);
      }
    }
    try {
      await refreshServerAnnotations(
        isResearcher() && state.serverAnnotationsStore !== String(state.activeStore || ""),
      );
    } catch (error: Any) {
      console.warn("Could not refresh annotations for dashboard", error);
    }
    const _rows = allRows(),
      totals = dashboardTotals(),
      workMap = isResearcher() ? null : workIndex();
    const workItems = isResearcher()
      ? (state.storeWorkStats || []).map((item: Any) => ({
          work: item.work,
          count: Number(item.count || 0),
          totalWords: Number(item.total_words || 0),
          averageRecordLength: Number(item.average_record_length || 0),
          year: item.publication_year || item.year || "",
          cover: item.cover_url || "",
          author: item.document_author || "",
          publisher: item.publisher || "",
        }))
      : [...workMap.values()]
          .map((item) => {
            const year = commonWorkValue(item.rows, "publication_year"),
              totalWords = item.rows.reduce(
                (sum: Any, row: Any) =>
                  sum +
                  String(row.record?.text || "")
                    .trim()
                    .split(/\s+/)
                    .filter(Boolean).length,
                0,
              );
            return {
              work: item.work,
              count: item.count,
              totalWords,
              averageRecordLength: item.count ? Math.round(totalWords / item.count) : 0,
              year: year.value || [...item.years].sort()[0] || "",
              cover: workCoverUrl(item.rows),
              author: [...item.authors].join(", "),
              publisher: commonWorkValue(item.rows, "publisher").value || "",
            };
          })
          .sort((a, b) => a.work.localeCompare(b.work));
    const words = workItems.reduce((sum: Any, item: Any) => sum + Number(item.totalWords || 0), 0);
    const singleLoadedWork =
      !isResearcher() && workItems.length === 1 && workMap?.has(workItems[0].work)
        ? workMap.get(workItems[0].work)
        : null;
    const metricSets = singleLoadedWork
      ? workInsightMetrics(singleLoadedWork.rows, singleLoadedWork.work)
      : [
          {
            id: "average",
            type: "bars",
            title: tr("dashboard.top_avg_record_length", "Top 5 Works by Average Record Length"),
            values: [...workItems]
              .sort((a, b) => b.averageRecordLength - a.averageRecordLength)
              .slice(0, 5)
              .map((item) => ({ key: item.work, value: item.averageRecordLength })),
            format: (value: Any) => Number(value).toLocaleString(),
          },
          {
            id: "words",
            type: "bars",
            title: tr("dashboard.top_total_words", "Top 5 Works by Total Words"),
            values: [...workItems]
              .sort((a, b) => b.totalWords - a.totalWords)
              .slice(0, 5)
              .map((item) => ({ key: item.work, value: item.totalWords })),
            format: (value: Any) => compactNumber(value),
          },
          {
            id: "records",
            type: "bars",
            title: tr("dashboard.top_works_records", "Top 5 Works by Number of Records"),
            values: [...workItems]
              .sort((a, b) => b.count - a.count)
              .slice(0, 5)
              .map((item) => ({ key: item.work, value: item.count })),
            format: (value: Any) => Number(value).toLocaleString(),
          },
          {
            id: "record-share",
            type: "pie",
            title: tr("dashboard.work_record_share", "Works as percentage of total records"),
            values: pieShareSeries(workItems, "count"),
            valueLabel: tr("dynamic.records", "records"),
          },
          {
            id: "word-share",
            type: "pie",
            title: tr("dashboard.work_word_share", "Works as percentage of total words"),
            values: pieShareSeries(workItems, "totalWords"),
            valueLabel: tr("dashboard.words", "words"),
          },
        ];
    state.dashboardMetricIndex = Math.max(
      0,
      Math.min(metricSets.length - 1, Number(state.dashboardMetricIndex) || 0),
    );
    const activeMetric = metricSets[state.dashboardMetricIndex];
    const recent = isResearcher()
      ? hasCapability("activity.read")
        ? [
            ...(hasCapability("annotations.read")
              ? (state.serverAnnotations || []).map((annotation: Any) => ({
                  kind: "annotation",
                  timestamp: annotation.created_at || "",
                  annotation,
                }))
              : []),
            ...(hasCapability("rag.jobs.own")
              ? (state.jobs || [])
                  .filter((job: Any) => job.type === "rag")
                  .map((job: Any) => ({
                    kind: "rag",
                    timestamp: job.updated_at || job.finished_at || job.created_at || "",
                    job,
                  }))
              : []),
          ]
            .sort(
              (a, b) => new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime(),
            )
            .slice(0, 4)
        : []
      : recentAuditChanges(4).map(({ file, record, index, update }: Any) => ({
          kind: "record",
          timestamp: update.timestamp || "",
          file,
          record,
          index,
          update,
        }));
    const works = workItems.sort((a: Any, b: Any) => a.work.localeCompare(b.work));
    const currentProvider = defaultProviderProfile();
    const currentLanguage = state.translations?.info?.name || state.translations?.locale || "";
    const currentLanguageFlag = state.translations?.info?.flag || "🌐";
    const latestAnnotation =
      !isResearcher() || hasCapability("annotations.read") ? recentAnnotations(1)[0] || null : null;
    const preview = await dashboardRecordPreview(),
      previewRecord = preview.record,
      previewTarget = preview.target;
    main.innerHTML = `<div class="dashboard-page">
    <section class="dashboard-page-top"><article class="card dashboard-hero"><img src="/brand/derridai-mark.png" alt="" class="dashboard-hero-mark"><div class="dashboard-hero-copy"><h1>${esc(tr("dashboard.welcome", "Welcome to DerridAI"))}</h1><p class="dashboard-hero-tagline">${esc(tr("dashboard.tagline", "Search. Compare. Annotate. Always already."))}</p><blockquote>${esc(tr("dashboard.quote", "“Il n’y a pas de hors-texte.”"))}</blockquote><small>— Jacques Derrida</small><div class="dashboard-hero-actions"><button class="btn dark" id="dashStartSearch">${icon("search")}${esc(tr("dashboard.start_searching", "Start searching"))}</button><button class="btn" id="dashBrowseWorks">${icon("books")}${esc(tr("dashboard.browse_works", "Browse works"))}</button></div></div></article>
    <article class="card dashboard-search-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("search")}</span><b>${esc(tr("dashboard.global_search", "Global Search"))}</b></div><div class="dashboard-search-tabs"><button class="${state.globalSearchMode === "traditional" ? "active" : ""}" data-dash-search-mode="traditional">${esc(tr("research.traditional_search", isResearcher() ? "Record search" : "Traditional search"))}</button><button class="${state.globalSearchMode !== "traditional" ? "active" : ""}" data-dash-search-mode="database">${esc(tr("research.semantic_db_search", "Semantic DB Search"))}</button></div><div class="dashboard-search-line"><div class="dashboard-search-input">${icon("search")}<input id="dashSearchQuery" value="${esc(state.globalSearch || "")}" placeholder="${esc(tr("dashboard.search_corpus_placeholder", "Search the corpus…"))}"></div><select id="dashSearchWork" class="control" aria-label="${esc(tr("field.work", "Work"))}"><option value="">${esc(tr("dashboard.all_works", "All works"))}</option>${works.map((item: Any) => `<option value="${esc(item.work)}">${esc(item.work)}</option>`).join("")}</select><button class="btn dark" id="dashRunSearch">${icon("search")}${esc(tr("ui.search", "Search"))}</button></div><div class="dashboard-search-footer"><button class="dashboard-advanced-link" id="dashAdvancedSearch">${esc(tr("dashboard.advanced_filters", "Advanced filters"))} →</button><p class="dashboard-search-help">${esc(tr("dashboard.search_help", "Search across works, metadata, annotations, and—when available—the semantic database."))}</p></div></article></section>
    <section class="dashboard-page-middle"><article class="card dashboard-overview-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("books")}</span><b>${esc(tr("dashboard.corpus_overview", "Corpus Overview"))}</b></div><div class="dashboard-overview-grid"><button data-dashboard-nav="works"><span class="dashboard-overview-icon">${icon("books")}</span><strong>${works.length.toLocaleString()}</strong><small>${esc(tr("dashboard.works", "Works"))}</small></button><button data-dashboard-nav="${isResearcher() ? "vector" : "list"}"><span class="dashboard-overview-icon">${icon("record")}</span><strong>${totals.records.toLocaleString()}</strong><small>${esc(tr("dashboard.records", "Records"))}</small></button><button ${isResearcher() ? 'disabled data-disabled-reason="Word totals are not exposed to researcher accounts."' : ""}><span class="dashboard-overview-icon">${icon("list")}</span><strong>${isResearcher() ? "—" : compactNumber(words)}</strong><small>${esc(tr("dashboard.total_words", "Total words"))}</small></button><button data-dashboard-nav="vector"><span class="dashboard-overview-icon">${icon("database")}</span><strong>${totals.dbs.toLocaleString()}</strong><small>${esc(tr("dashboard.databases", "Databases"))}</small></button></div></article>
    <article class="card dashboard-average-card dashboard-metric-carousel" aria-roledescription="carousel"><div class="dashboard-metric-head"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("chart")}</span><b>${esc(activeMetric.title)}</b></div><div class="dashboard-metric-controls"><button class="dashboard-metric-arrow" id="dashMetricPrev" type="button" aria-label="${esc(tr("dashboard.previous_chart", "Previous chart"))}">←</button><span>${state.dashboardMetricIndex + 1} / ${metricSets.length}</span><button class="dashboard-metric-arrow" id="dashMetricNext" type="button" aria-label="${esc(tr("dashboard.next_chart", "Next chart"))}">→</button></div></div><div class="dashboard-metric-body">${dashboardMetricBody(activeMetric)}</div><div class="dashboard-metric-dots" role="tablist" aria-label="${esc(tr("dashboard.work_charts", "Work charts"))}">${metricSets.map((metric: Any, index: Any) => `<button type="button" role="tab" data-dashboard-metric="${index}" class="${index === state.dashboardMetricIndex ? "active" : ""}" aria-label="${esc(metric.title)}" aria-selected="${index === state.dashboardMetricIndex}" tabindex="${index === state.dashboardMetricIndex ? 0 : -1}"></button>`).join("")}</div></article>
    <article class="card dashboard-activity-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("history")}</span><b>${esc(tr("dashboard.recent_activity", "Recent Activity"))}</b></div><div class="dashboard-activity-list">${recent.map((item: Any) => (item.kind === "annotation" ? `<button class="dashboard-activity-row" data-recent-server-annotation-record="${esc(item.annotation.record_id || "")}" data-recent-server-annotation-store="${esc(item.annotation.store || "")}"><span class="dashboard-activity-clock">${icon("record")}</span><time>${esc(relativeTime(item.timestamp))}</time><span>${esc(tr("annotations.record_note", "Annotation"))} · ${esc(item.annotation.work || item.annotation.record_id || tr("nav.record", "Record"))}</span></button>` : item.kind === "rag" ? `<button class="dashboard-activity-row" ${item.job.status === "completed" ? `data-recent-rag-result="${esc(item.job.id)}"` : ""}><span class="dashboard-activity-clock">${icon("spark")}</span><time>${esc(relativeTime(item.timestamp))}</time><span>${esc(tr("nav.rag", "Research"))} · ${esc(String(item.job.prompt || item.job.label || "RAG").slice(0, 90))}</span></button>` : `<button class="dashboard-activity-row" data-recent-file="${item.file.id}" data-recent-index="${item.index}"><span class="dashboard-activity-clock">${icon("history")}</span><time>${esc(relativeTime(item.update.timestamp))}</time><span>${esc(label(item.update.field_name || tr("dashboard.updated_record", "Updated record")))} · ${esc(item.record.work || item.record.record_id || item.file.name)}</span></button>`)).join("") || `<div class="dashboard-activity-empty">${esc(tr("dashboard.no_recent_activity", "No recent activity in areas available to this account."))}</div>`}</div></article></section>
    <section class="card dashboard-works-card"><div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("books")}</span><b>${esc(tr("dashboard.works", "Works"))}</b></div><button class="dashboard-text-link" id="dashViewAllWorks">${esc(tr("dashboard.view_all_works", "View all works"))} →</button></div><div class="dashboard-work-carousel-shell"><button class="carousel-arrow" id="dashWorksPrev" type="button" title="${esc(tr("ui.previous", "Previous"))}" aria-label="${esc(tr("ui.previous", "Previous"))}">‹</button><div class="dashboard-work-strip" id="dashWorksCarousel">${works.map((item: Any, index: Any) => `<button class="dashboard-work-card" data-dashboard-work="${esc(item.work)}">${item.cover ? `<img class="dashboard-book-cover image" src="${esc(item.cover)}" alt="${esc(trf("works.cover_alt", "Cover of {work}", { work: item.work }))}" loading="lazy">` : `<span class="dashboard-book-cover placeholder">${String(index + 1).padStart(2, "0")}</span>`}<span><b>${esc(item.work)}</b><small>${esc(item.year || tr("dashboard.year_not_recorded", "Year not recorded"))}</small><small>${item.count.toLocaleString()} ${esc(tr("dynamic.records", "records"))}</small></span></button>`).join("") || `<div class="note">${esc(tr("research.no_works", "No works loaded yet."))}</div>`}</div><button class="carousel-arrow" id="dashWorksNext" type="button" title="${esc(tr("ui.next", "Next"))}" aria-label="${esc(tr("ui.next", "Next"))}">›</button></div></section>
    <section class="dashboard-page-lower">${
      isResearcher()
        ? hasCapability("appearance.manage")
          ? `<article class="card dashboard-quick-card dashboard-appearance-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("gear")}</span><b>${esc(tr("dashboard.appearance", "Appearance"))}</b></div><p>${esc(tr("dashboard.appearance_help", "Choose the interface accent that is easiest for you to read."))}</p><fieldset class="dashboard-theme-options"><legend>${esc(tr("dashboard.interface_theme", "Interface theme"))}</legend>${[
              ["green", tr("theme.green", "Green")],
              ["blue", tr("theme.blue", "Blue")],
              ["slate", tr("theme.slate", "Slate")],
            ]
              .map(
                ([value, name]) =>
                  `<label><input type="radio" name="dashboard-theme" data-dashboard-theme="${value}" ${state.appConfig.ui_color_theme === value ? "checked" : ""}><span class="theme-swatch ${value}" aria-hidden="true"></span><b>${esc(name)}</b></label>`,
              )
              .join(
                "",
              )}</fieldset><button class="btn" id="dashAppearanceSettings">${esc(tr("dashboard.more_appearance_settings", "More appearance settings"))}</button></article>`
          : `<article class="card dashboard-quick-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("gear")}</span><b>${esc(tr("dashboard.appearance", "Appearance"))}</b></div><p>${esc(tr("permissions.appearance_denied", "Appearance controls are disabled for this role."))}</p></article>`
        : `<article class="card dashboard-quick-card dashboard-language-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("gear")}</span><b>${esc(tr("dashboard.language_settings", "Language Settings"))}</b></div><p>${esc(tr("dashboard.language_settings_help", "Choose the interface language and manage translation dictionaries."))}</p><div class="dashboard-quick-field dashboard-locale-field"><span>${esc(tr("dashboard.interface_language", "Interface language"))}</span><b><i class="dashboard-locale-symbol">${currentLanguageFlag}</i>${esc(currentLanguage)}</b></div><button class="btn primary" id="dashLanguages">${esc(tr("dashboard.manage_languages", "Manage languages"))}</button></article>`
    }
    <article class="card dashboard-quick-card dashboard-provider-card"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("spark")}</span><b>${esc(tr("dashboard.llm_provider_settings", "LLM Provider Settings"))}</b></div><p>${esc(tr("dashboard.llm_provider_help", "Configure the provider used for LLM-assisted workflows."))}</p><div class="dashboard-provider-fields"><div class="dashboard-quick-field"><span>${esc(tr("dashboard.default_provider", "Default provider"))}</span><b>${currentProvider ? esc(providerDisplayName(currentProvider)) : esc(tr("dashboard.not_configured", "Not configured"))}</b></div><div class="dashboard-quick-field"><span>${esc(tr("dashboard.model", "Model"))}</span><b>${currentProvider ? esc(currentProvider.model || "auto") : "—"}</b></div></div><button class="btn" id="dashProviders">${esc(isResearcher() ? tr("nav.rag", "Research") : tr("dashboard.manage_provider", "Manage provider"))}</button></article>
    <article class="card dashboard-quick-card dashboard-record-preview"><div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("record")}</span><b>${esc(tr("dashboard.record_view", "Record View"))}</b></div><button class="dashboard-text-link" id="dashRecordView" ${previewTarget ? "" : `disabled data-disabled-reason="${esc(tr("dashboard.no_record_available", "No record is available to open."))}"`}>${esc(tr("research.open", "Open"))} →</button></div>${
      previewRecord
        ? `<div class="dashboard-record-state">${esc(preview.lastViewed ? tr("dashboard.last_viewed_record", "Last viewed record") : tr("dashboard.random_record", "A record from the corpus"))}</div><div class="dashboard-record-meta"><b>${esc(previewRecord.work || previewRecord.record_id || tr("dashboard.record", "Record"))}</b><span class="dashboard-record-pages">${esc(mlaPageSpan(previewRecord) || "")}</span></div><div class="dashboard-record-text">${esc(
            String(previewRecord.text || "")
              .replace(/\s+/g, " ")
              .slice(0, 220),
          )}${String(previewRecord.text || "").length > 220 ? "…" : ""}</div>`
        : `<div class="dashboard-record-empty">${esc(tr("dashboard.no_record_selected", "No corpus record is currently available."))}</div>`
    }</article>
    ${latestAnnotation ? `<article class="card dashboard-quick-card dashboard-annotations-card"><div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("record")}</span><b>${esc(tr("dashboard.latest_annotation", "Latest annotation"))}</b></div><button class="dashboard-text-link" id="dashAnnotations">${esc(tr("annotations.view_all", "View all"))} →</button></div><button class="dashboard-annotation-preview" ${latestAnnotation.server ? `data-recent-server-annotation-record="${esc(latestAnnotation.annotation.record_id || "")}" data-recent-server-annotation-store="${esc(latestAnnotation.annotation.store || "")}"` : `data-recent-annotation-file="${esc(latestAnnotation.file.id)}" data-recent-annotation-index="${latestAnnotation.index}"`}><div class="dashboard-annotation-meta"><span class="dashboard-annotation-work">${esc(latestAnnotation.work)}</span><span class="dashboard-annotation-pages">${esc(mlaPageSpan(latestAnnotation.record) || tr("record.page_not_recorded", "Page not recorded"))}</span><span class="dashboard-annotation-author">${esc(latestAnnotation.annotation.initiated_by || latestAnnotation.annotation.author || tr("annotations.unknown_author", "Unknown author"))}</span><time>${esc(formatTimestamp(latestAnnotation.annotation.created_at))}</time><small>${esc(latestAnnotation.record.record_id || tr("nav.record", "Record"))}</small></div>${latestAnnotation.annotation.note ? `<p>${esc(latestAnnotation.annotation.note)}</p>` : latestAnnotation.annotation.quote ? `<blockquote>${esc(latestAnnotation.annotation.quote)}</blockquote>` : `<p>${esc(tr("annotations.record_note", "Record annotation"))}</p>`}</button></article>` : `<article class="card dashboard-quick-card dashboard-annotations-card"><div class="dashboard-section-heading"><div class="dashboard-card-title"><span class="dashboard-title-icon">${icon("record")}</span><b>${esc(tr("dashboard.annotations", "Annotations"))}</b></div><button class="dashboard-text-link" id="dashAnnotations">${esc(tr("research.open", "Open"))} →</button></div><p>${esc(isResearcher() ? tr("annotations.researcher_help", "Annotations are organized by work when available in the current workspace.") : tr("dashboard.annotations_help", "Collect notes, tags, and discussion threads attached to corpus evidence."))}</p></article>`}
    </section>${renderCorpusBuildsHomeCard()}${renderOperationsPanel()}</div>`;
    mountOperationsPanelHost();
    const goSearch = async () => {
      state.globalSearch = main.querySelector("#dashSearchQuery")?.value?.trim() || "";
      const work = main.querySelector("#dashSearchWork")?.value || "",
        semantic = state.globalSearchMode === "database";
      state.globalPage = 1;
      state.storeSearchResults = [];
      if (semantic) {
        if (!state.activeStore) {
          try {
            await refreshStores();
          } catch {
            // Best effort: keep going with what we have.
          }
          state.activeStore = recordStores()[0]?.name || "";
        }
        state.globalSearchMode = "database";
        if (!state.activeStore) {
          persistPrefs();
          if (canAccessPage("vector")) {
            toast(
              tr(
                "search.redirect_database",
                "Search needs a corpus database. Opening database creation now.",
              ),
              { tone: "info" },
            );
            openDatabaseCreationFromResearch();
          } else {
            navigateTo("global");
            toast(tr("research.no_database", "No corpus database available"), { tone: "warn" });
          }
          return;
        }
        state.dbSearchWhere = work ? { work } : {};
        state.storeQuery = state.globalSearch;
        if (state.globalSearch && state.dbSearchMethod === "filter")
          state.dbSearchMethod = "similarity";
        if (!state.globalSearch && work) state.dbSearchMethod = "filter";
        state.globalSearchAutoRun = false;
        state.storeSearchLoading = true;
        persistPrefs();
        navigateTo("global");
        try {
          const mode = state.dbSearchMethod || "similarity";
          const data = await api(`/api/stores/${encodeURIComponent(state.activeStore)}/search`, {
            method: "POST",
            body: JSON.stringify({
              query: state.globalSearch,
              mode,
              n_results: 100,
              where: Object.keys(dbSearchWhere()).length ? dbSearchWhere() : null,
              fetch_k: Number(state.dbSearchFetchK || 100),
              lambda_mult: Number(state.dbSearchLambda ?? 0.7),
            }),
          });
          state.storeSearchResults = data.results || [];
        } catch (error: Any) {
          toast(`${tr("research.search_failed", "Search failed")}: ${error.message}`, {
            tone: "danger",
          });
        } finally {
          state.storeSearchLoading = false;
          persistPrefs();
        }
      } else {
        state.globalSearchMode = "traditional";
        state.globalSearchAutoRun = false;
        if (isResearcher()) state.dbSearchWhere = work ? { work } : {};
        else
          state.globalFilters = work ? [{ id: uid(), field: "work", op: "eq", value: work }] : [];
        persistPrefs();
        navigateTo("global");
      }
    };
    main.querySelector("#dashStartSearch")?.addEventListener("click", () => navigateTo("global"));
    main.querySelector("#dashBrowseWorks")?.addEventListener("click", () => navigateTo("works"));
    main.querySelector("#dashViewAllWorks")?.addEventListener("click", () => navigateTo("works"));
    main.querySelector("#dashRunSearch")?.addEventListener("click", goSearch);
    main.querySelector("#dashSearchQuery")?.addEventListener("keydown", (event: Any) => {
      if (event.key === "Enter") {
        event.preventDefault();
        goSearch();
      }
    });
    main.querySelector("#dashAdvancedSearch")?.addEventListener("click", () => {
      state.globalSearch = main.querySelector("#dashSearchQuery")?.value?.trim() || "";
      const work = main.querySelector("#dashSearchWork")?.value || "";
      state.globalAdvancedOpen = true;
      if (state.globalSearchMode === "database") state.dbSearchWhere = work ? { work } : {};
      else if (!isResearcher())
        state.globalFilters = work ? [{ id: uid(), field: "work", op: "eq", value: work }] : [];
      persistPrefs();
      navigateTo("global");
    });
    main.querySelectorAll("[data-dash-search-mode]").forEach((button: Any) =>
      button.addEventListener("click", () => {
        state.globalSearchMode = button.dataset.dashSearchMode;
        persistPrefs();
        syncUrl({ replace: true });
        renderDashboard(main);
      }),
    );
    main
      .querySelectorAll("[data-dashboard-nav]")
      .forEach((button: Any) =>
        button.addEventListener("click", () => navigateTo(button.dataset.dashboardNav)),
      );
    main.querySelectorAll("[data-dashboard-work]").forEach((button: Any) =>
      button.addEventListener("click", () => {
        state.workOverview = button.dataset.dashboardWork || "";
        persistPrefs();
        navigateTo("works");
      }),
    );
    main.querySelectorAll("[data-dashboard-search-field]").forEach((button: Any) =>
      button.addEventListener("click", () =>
        searchByMetadata(button.dataset.dashboardSearchField, button.dataset.dashboardSearchValue, {
          contains: ["persons", "concepts", "topics"].includes(button.dataset.dashboardSearchField),
        }),
      ),
    );
    const carousel = main.querySelector("#dashWorksCarousel");
    const scrollWorks = (direction: Any) =>
      carousel?.scrollBy({
        left: direction * Math.max(280, carousel.clientWidth * 0.78),
        behavior: "smooth",
      });
    main.querySelector("#dashWorksPrev")?.addEventListener("click", () => scrollWorks(-1));
    main.querySelector("#dashWorksNext")?.addEventListener("click", () => scrollWorks(1));
    main.querySelectorAll("[data-recent-file]").forEach((button: Any) =>
      button.addEventListener("click", () =>
        navigateTo("record", {
          fileId: button.dataset.recentFile,
          index: +button.dataset.recentIndex,
        }),
      ),
    );
    main.querySelectorAll("[data-dashboard-theme]").forEach((input: Any) =>
      input.addEventListener("change", () => {
        applyUiTheme(input.dataset.dashboardTheme);
        persistPrefs();
        toast(tr("dashboard.appearance_saved", "Appearance updated"), { tone: "success" });
      }),
    );
    main
      .querySelector("#dashAppearanceSettings")
      ?.addEventListener("click", () => navigateTo("config"));
    main.querySelector("#dashLanguages")?.addEventListener("click", () => {
      if (isResearcher()) navigateTo("config");
      else
        window.dispatchEvent(
          new CustomEvent("derridai:navigate-native", { detail: { path: "/languages" } }),
        );
    });
    main
      .querySelector("#dashProviders")
      ?.addEventListener("click", () => navigateTo(isResearcher() ? "rag" : "providers"));
    main.querySelector("#dashRecordView")?.addEventListener("click", () => {
      if (!previewTarget) return;
      if (previewTarget.kind === "workspace")
        navigateTo("record", { fileId: previewTarget.fileId, index: previewTarget.index });
      else {
        state.activeStore = previewTarget.store;
        state.researcherRecordId = previewTarget.id;
        persistPrefs();
        navigateTo("record");
      }
    });
    main.querySelector("#dashMetricPrev")?.addEventListener("click", () => {
      state.dashboardMetricIndex =
        (state.dashboardMetricIndex + metricSets.length - 1) % metricSets.length;
      persistPrefs();
      syncUrl({ replace: true });
      renderDashboard(main);
    });
    main.querySelector("#dashMetricNext")?.addEventListener("click", () => {
      state.dashboardMetricIndex = (state.dashboardMetricIndex + 1) % metricSets.length;
      persistPrefs();
      syncUrl({ replace: true });
      renderDashboard(main);
    });
    main.querySelectorAll("[data-dashboard-metric]").forEach((button: Any) => {
      button.addEventListener("click", () => {
        state.dashboardMetricIndex = Number(button.dataset.dashboardMetric) || 0;
        persistPrefs();
        syncUrl({ replace: true });
        renderDashboard(main);
      });
      button.addEventListener("keydown", (event: Any) => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        if (event.key === "Home") state.dashboardMetricIndex = 0;
        else if (event.key === "End") state.dashboardMetricIndex = metricSets.length - 1;
        else
          state.dashboardMetricIndex =
            (state.dashboardMetricIndex +
              (event.key === "ArrowRight" ? 1 : -1) +
              metricSets.length) %
            metricSets.length;
        persistPrefs();
        syncUrl({ replace: true });
        renderDashboard(main);
        queueMicrotask(() =>
          main.querySelector(`[data-dashboard-metric="${state.dashboardMetricIndex}"]`)?.focus(),
        );
      });
    });
    main
      .querySelector("#dashAnnotations")
      ?.addEventListener("click", () => navigateTo("annotations"));
    main.querySelector("[data-recent-annotation-file]")?.addEventListener("click", (event: Any) =>
      navigateTo("record", {
        fileId: event.currentTarget.dataset.recentAnnotationFile,
        index: +event.currentTarget.dataset.recentAnnotationIndex,
      }),
    );
    main
      .querySelector("[data-recent-server-annotation-record]")
      ?.addEventListener("click", (event: Any) =>
        openSharedAnnotationRecord(
          event.currentTarget.dataset.recentServerAnnotationStore,
          event.currentTarget.dataset.recentServerAnnotationRecord,
        ),
      );
    wireCorpusBuildsHomeCard(main);
    decorateDisabledControls(main);
  }
  return {
    openSharedAnnotationRecord,
    dashboardTotals,
    dashboardWorkspaceRecordTarget,
    dashboardRecordPreview,
    renderDashboard,
  };
}
