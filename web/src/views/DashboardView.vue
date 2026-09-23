<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as runtime from "../runtime/runtime.js";
import { mlaPageSpan } from "../domain/citations";
import { icon } from "../domain/html";
import { commonWorkValue, workCoverUrl } from "../domain/workMetadata";
import AppIcon from "../components/AppIcon.vue";
import { useI18nStore } from "../stores/i18n";
import { corpusState } from "../state/workspaceState";
import { useJobsStore } from "../stores/jobs";

const i18n = useI18nStore();

const mainEl = ref<HTMLElement>();
const searchQueryInputEl = ref<HTMLInputElement>();
const searchWorkSelectEl = ref<HTMLSelectElement>();
const worksCarouselEl = ref<HTMLElement>();
const metricDotEls = ref<HTMLButtonElement[]>([]);

const isResearcher = ref(false);
const totals = ref<Record<string, number>>({ records: 0, dbs: 0 });
const words = ref(0);
const works = ref<Record<string, unknown>[]>([]);
const metricSets = ref<Record<string, unknown>[]>([]);
const activeMetricIndex = ref(0);
const globalSearch = ref("");
const globalSearchMode = ref("traditional");
const recent = ref<Record<string, unknown>[]>([]);
const currentProvider = ref<Record<string, unknown> | null>(null);
const currentLanguage = ref("");
const currentLanguageFlag = ref("🌐");
const latestAnnotation = ref<Record<string, unknown> | null>(null);
const previewRecord = ref<Record<string, unknown> | null>(null);
const previewTarget = ref<Record<string, unknown> | null>(null);
const previewLastViewed = ref(false);
const uiColorTheme = ref("green");
const corpusBuilds = ref<Record<string, unknown>[]>([]);
const corpusBuildsActive = ref(0);
const corpusBuildsAriaLabel = ref("");

const activeMetric = () => metricSets.value[activeMetricIndex.value] as Record<string, Any>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

function metricBodyHtml() {
  const metric = activeMetric();
  return metric ? runtime.dashboardMetricBody(metric) : "";
}

async function refresh() {
  const state = runtime.state as unknown as Record<string, Any>;
  isResearcher.value = runtime.isResearcher();
  if (isResearcher.value) {
    try {
      await runtime.refreshStores();
      if (!state.activeStore) state.activeStore = runtime.recordStores()[0]?.name || "";
      if (state.activeStore) await runtime.refreshStoreWorks(true);
    } catch (error) {
      console.warn("Could not refresh researcher dashboard data", error);
    }
  }
  try {
    await runtime.refreshServerAnnotations(
      isResearcher.value && state.serverAnnotationsStore !== String(state.activeStore || ""),
    );
  } catch (error) {
    console.warn("Could not refresh annotations for dashboard", error);
  }

  totals.value = runtime.dashboardTotals();
  const workMap = isResearcher.value ? null : runtime.workIndex();
  const workItems: Any[] = isResearcher.value
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
    : [...(workMap as Map<string, Any>).values()]
        .map((item: Any) => {
          const year = commonWorkValue(item.rows, "publication_year");
          const totalWords = item.rows.reduce(
            (sum: number, row: Any) =>
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
        .sort((a: Any, b: Any) => a.work.localeCompare(b.work));
  words.value = workItems.reduce((sum, item) => sum + Number(item.totalWords || 0), 0);
  const singleLoadedWork =
    !isResearcher.value &&
    workItems.length === 1 &&
    (workMap as Map<string, Any>)?.has(workItems[0].work)
      ? (workMap as Map<string, Any>).get(workItems[0].work)
      : null;
  metricSets.value = singleLoadedWork
    ? runtime.workInsightMetrics(singleLoadedWork.rows, singleLoadedWork.work)
    : [
        {
          id: "average",
          type: "bars",
          title: i18n.t("dashboard.top_avg_record_length"),
          values: [...workItems]
            .sort((a, b) => b.averageRecordLength - a.averageRecordLength)
            .slice(0, 5)
            .map((item) => ({ key: item.work, value: item.averageRecordLength })),
          format: (value: number) => Number(value).toLocaleString(),
        },
        {
          id: "words",
          type: "bars",
          title: i18n.t("dashboard.top_total_words"),
          values: [...workItems]
            .sort((a, b) => b.totalWords - a.totalWords)
            .slice(0, 5)
            .map((item) => ({ key: item.work, value: item.totalWords })),
          format: (value: number) => runtime.compactNumber(value),
        },
        {
          id: "records",
          type: "bars",
          title: i18n.t("dashboard.top_works_records"),
          values: [...workItems]
            .sort((a, b) => b.count - a.count)
            .slice(0, 5)
            .map((item) => ({ key: item.work, value: item.count })),
          format: (value: number) => Number(value).toLocaleString(),
        },
        {
          id: "record-share",
          type: "pie",
          title: i18n.t("dashboard.work_record_share"),
          values: runtime.pieShareSeries(workItems, "count"),
          valueLabel: i18n.t("dynamic.records"),
        },
        {
          id: "word-share",
          type: "pie",
          title: i18n.t("dashboard.work_word_share"),
          values: runtime.pieShareSeries(workItems, "totalWords"),
          valueLabel: i18n.t("dashboard.words"),
        },
      ];
  state.dashboardMetricIndex = Math.max(
    0,
    Math.min(metricSets.value.length - 1, Number(state.dashboardMetricIndex) || 0),
  );
  activeMetricIndex.value = state.dashboardMetricIndex as number;

  recent.value = isResearcher.value
    ? runtime.hasCapability("activity.read")
      ? [
          ...(runtime.hasCapability("annotations.read")
            ? ((state.serverAnnotations || []) as Any[]).map((annotation: Any) => ({
                kind: "annotation",
                timestamp: annotation.created_at || "",
                annotation,
              }))
            : []),
          ...(runtime.hasCapability("rag.jobs.own")
            ? ((state.jobs || []) as Any[])
                .filter((job: Any) => job.type === "rag")
                .map((job: Any) => ({
                  kind: "rag",
                  timestamp: job.updated_at || job.finished_at || job.created_at || "",
                  job,
                }))
            : []),
        ]
          .sort(
            (a, b) =>
              new Date(String(b.timestamp) || 0).getTime() -
              new Date(String(a.timestamp) || 0).getTime(),
          )
          .slice(0, 4)
      : []
    : runtime.recentAuditChanges(4).map(({ file, record, index, update }: Any) => ({
        kind: "record",
        timestamp: update.timestamp || "",
        file,
        record,
        index,
        update,
      }));

  works.value = workItems.sort((a, b) => a.work.localeCompare(b.work));
  currentProvider.value = runtime.defaultProviderProfile();
  currentLanguage.value = state.translations?.info?.name || state.translations?.locale || "";
  currentLanguageFlag.value = state.translations?.info?.flag || "🌐";
  latestAnnotation.value =
    !isResearcher.value || runtime.hasCapability("annotations.read")
      ? runtime.recentAnnotations(1)[0] || null
      : null;
  uiColorTheme.value = state.appConfig?.ui_color_theme || "green";
  globalSearch.value = state.globalSearch || "";
  globalSearchMode.value = state.globalSearchMode || "traditional";

  const preview = await runtime.dashboardRecordPreview();
  previewRecord.value = preview.record;
  previewTarget.value = preview.target;
  previewLastViewed.value = preview.lastViewed;

  corpusBuildsAriaLabel.value = i18n.t("pdf_corpus.home_title");
  if (isResearcher.value) {
    corpusBuilds.value = [];
    corpusBuildsActive.value = 0;
  } else {
    const builds = ((state.jobs || []) as Any[])
      .filter((job) => job.type === "pdf_corpus")
      .slice(0, 4);
    corpusBuilds.value = builds;
    corpusBuildsActive.value = builds.filter((job) =>
      ["queued", "running", "cancelling"].includes(String(job.status)),
    ).length;
  }

  await nextTick();
  if (mainEl.value) runtime.decorateDisabledControls(mainEl.value);
}

function corpusBuildStatusLabel(job: Any) {
  const status = job.raw_status || job.status || "unknown";
  return `${String(status).replaceAll("_", " ")} · ${String(job.stage_detail || job.stage || "")}`;
}

function corpusBuildPercent(job: Any) {
  return Math.max(0, Math.min(100, Math.round(Number(job.progress || 0) * 100)));
}

async function persistAndRefresh() {
  runtime.persistPrefs();
  runtime.syncUrl({ replace: true });
  await refresh();
}

async function goSearch() {
  const state = runtime.state as unknown as Any;
  state.globalSearch = searchQueryInputEl.value?.value?.trim() || "";
  const work = searchWorkSelectEl.value?.value || "";
  const semantic = state.globalSearchMode === "database";
  state.globalPage = 1;
  state.storeSearchResults = [];
  if (semantic) {
    if (!state.activeStore) {
      try {
        await runtime.refreshStores();
      } catch {
        // Best effort: keep going with what we have.
      }
      state.activeStore = runtime.recordStores()[0]?.name || "";
    }
    state.globalSearchMode = "database";
    if (!state.activeStore) {
      runtime.persistPrefs();
      if (runtime.canAccessPage("vector")) {
        runtime.notifyToast(
          i18n.t("search.redirect_database"),
          { tone: "info" },
        );
        runtime.openDatabaseCreationFromResearch();
      } else {
        runtime.navigateTo("global");
        runtime.notifyToast(i18n.t("research.no_database"), {
          tone: "warn",
        });
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
    runtime.persistPrefs();
    runtime.navigateTo("global");
    try {
      const mode = state.dbSearchMethod || "similarity";
      const data: Any = await runtime.api(
        `/api/stores/${encodeURIComponent(state.activeStore)}/search`,
        {
          method: "POST",
          body: JSON.stringify({
            query: state.globalSearch,
            mode,
            n_results: 100,
            where: Object.keys(runtime.dbSearchWhere()).length ? runtime.dbSearchWhere() : null,
            fetch_k: Number(state.dbSearchFetchK || 100),
            lambda_mult: Number(state.dbSearchLambda ?? 0.7),
          }),
        },
      );
      state.storeSearchResults = data.results || [];
    } catch (error) {
      runtime.notifyToast(
        `${i18n.t("research.search_failed")}: ${error instanceof Error ? error.message : String(error)}`,
        { tone: "danger" },
      );
    } finally {
      state.storeSearchLoading = false;
      runtime.persistPrefs();
    }
  } else {
    state.globalSearchMode = "traditional";
    state.globalSearchAutoRun = false;
    if (isResearcher.value) state.dbSearchWhere = work ? { work } : {};
    else
      state.globalFilters = work
        ? [{ id: runtime.uid(), field: "work", op: "eq", value: work }]
        : [];
    runtime.persistPrefs();
    runtime.navigateTo("global");
  }
}

function onSearchQueryKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter") return;
  event.preventDefault();
  void goSearch();
}

async function setSearchMode(mode: string) {
  runtime.state.globalSearchMode = mode;
  await persistAndRefresh();
}

function goNav(view: string) {
  runtime.navigateTo(view);
}

async function openWork(work: string) {
  runtime.state.workOverview = work;
  runtime.persistPrefs();
  runtime.navigateTo("works");
}

function onMetricBodyClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null;
  const workButton = target?.closest<HTMLElement>("[data-dashboard-work]");
  if (workButton) {
    void openWork(workButton.dataset.dashboardWork || "");
    return;
  }
  const fieldButton = target?.closest<HTMLElement>("[data-dashboard-search-field]");
  if (fieldButton) {
    const field = fieldButton.dataset.dashboardSearchField || "";
    runtime.searchByMetadata(field, fieldButton.dataset.dashboardSearchValue, {
      contains: ["persons", "concepts", "topics"].includes(field),
    });
  }
}

function scrollWorks(direction: number) {
  const carousel = worksCarouselEl.value;
  if (!carousel) return;
  carousel.scrollBy({
    left: direction * Math.max(280, carousel.clientWidth * 0.78),
    behavior: "smooth",
  });
}

function openRecentRecord(fileId: string, index: number) {
  runtime.navigateTo("record", { fileId, index });
}

async function setUiTheme(value: string) {
  runtime.applyUiTheme(value);
  runtime.persistPrefs();
  runtime.notifyToast(i18n.t("dashboard.appearance_saved"), {
    tone: "success",
  });
  await refresh();
}

function openAppearanceSettings() {
  runtime.navigateTo("config");
}

function openLanguages() {
  if (isResearcher.value) runtime.navigateTo("config");
  else
    window.dispatchEvent(
      new CustomEvent("derridai:navigate-native", { detail: { path: "/languages" } }),
    );
}

function openProviders() {
  runtime.navigateTo(isResearcher.value ? "rag" : "providers");
}

function openRecordPreview() {
  const target = previewTarget.value as Any | null;
  if (!target) return;
  if (target.kind === "workspace") {
    runtime.navigateTo("record", { fileId: target.fileId, index: target.index });
  } else {
    runtime.state.activeStore = target.store;
    runtime.state.researcherRecordId = target.id;
    runtime.persistPrefs();
    runtime.navigateTo("record");
  }
}

async function stepMetric(delta: number) {
  const state = runtime.state as unknown as Any;
  state.dashboardMetricIndex =
    (Number(state.dashboardMetricIndex) + delta + metricSets.value.length) %
    metricSets.value.length;
  await persistAndRefresh();
}

async function selectMetric(index: number) {
  runtime.state.dashboardMetricIndex = index;
  await persistAndRefresh();
}

async function onMetricDotKeydown(event: KeyboardEvent) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const state = runtime.state as unknown as Any;
  const count = metricSets.value.length;
  if (event.key === "Home") state.dashboardMetricIndex = 0;
  else if (event.key === "End") state.dashboardMetricIndex = count - 1;
  else
    state.dashboardMetricIndex =
      (Number(state.dashboardMetricIndex) + (event.key === "ArrowRight" ? 1 : -1) + count) % count;
  await persistAndRefresh();
  queueMicrotask(() => metricDotEls.value[activeMetricIndex.value]?.focus());
}

function openAnnotations() {
  runtime.navigateTo("annotations");
}

function openRecentAnnotation(fileId: string, index: number) {
  runtime.navigateTo("record", { fileId, index });
}

function openSharedAnnotation(store: string, recordId: string) {
  runtime.openSharedAnnotationRecord(store, recordId);
}

function openCorpusBuilder() {
  window.dispatchEvent(
    new CustomEvent("derridai:navigate-native", {
      detail: { path: "/pdf?mode=builder", runtimeView: "pdf" },
    }),
  );
}

function openCorpusBuild(jobId: string) {
  runtime.openJobResults(jobId);
}

// Some runtime code (provider warm-up, work metadata updates) still asks the dashboard to refresh this way; it used
// to call the legacy renderer directly, and now dispatches this event instead of reaching into a Vue component.
function onDashboardRefreshRequested() {
  void refresh();
}

const jobs = useJobsStore();

// The loaded corpus and the job list also change outside this view: a file imported or closed while the dashboard is
// open, or a background job progressing, used to appear only after leaving and coming back. Refresh when either does.
watch(
  () => [corpusState.version, corpusState.activeFileId, jobs.version],
  () => void refresh(),
  { flush: "post" },
);

onMounted(async () => {
  await refresh();
  runtime.mountOperationsPanelHost();
  window.addEventListener("derridai:dashboard-refresh", onDashboardRefreshRequested);
});
onBeforeUnmount(() => {
  window.removeEventListener("derridai:dashboard-refresh", onDashboardRefreshRequested);
});
</script>

<template>
  <main id="main" class="runtime-surface" aria-live="polite" ref="mainEl">
    <div class="dashboard-page">
      <section class="dashboard-page-top">
        <article class="card dashboard-hero">
          <img src="/brand/derridai-mark.png" alt="" class="dashboard-hero-mark" />
          <div class="dashboard-hero-copy">
            <h1>{{ i18n.t("dashboard.welcome") }}</h1>
            <p class="dashboard-hero-tagline">
              {{ i18n.t("dashboard.tagline") }}
            </p>
            <blockquote>
              {{ i18n.t("dashboard.quote") }}
            </blockquote>
            <small>— Jacques Derrida</small>
            <div class="dashboard-hero-actions">
              <button class="btn dark" id="dashStartSearch" @click="goNav('global')">
                <AppIcon name="search" />{{
                  i18n.t("dashboard.start_searching")
                }}
              </button>
              <button class="btn" id="dashBrowseWorks" @click="goNav('works')">
                <AppIcon name="books" />{{ i18n.t("dashboard.browse_works") }}
              </button>
            </div>
          </div>
        </article>
        <article class="card dashboard-search-card">
          <div class="dashboard-card-title">
            <span class="dashboard-title-icon"><AppIcon name="search" /></span>
            <b>{{ i18n.t("dashboard.global_search") }}</b>
          </div>
          <div class="dashboard-search-tabs">
            <button
              :class="{ active: globalSearchMode === 'traditional' }"
              data-dash-search-mode="traditional"
              @click="setSearchMode('traditional')"
            >
              {{
                i18n.t(
                  "research.traditional_search",
                  isResearcher ? "Record search" : "Traditional search",
                )
              }}
            </button>
            <button
              :class="{ active: globalSearchMode !== 'traditional' }"
              data-dash-search-mode="database"
              @click="setSearchMode('database')"
            >
              {{ i18n.t("research.semantic_db_search") }}
            </button>
          </div>
          <div class="dashboard-search-line">
            <div class="dashboard-search-input">
              <AppIcon name="search" />
              <input
                id="dashSearchQuery"
                ref="searchQueryInputEl"
                :value.attr="globalSearch"
                :placeholder="i18n.t('dashboard.search_corpus_placeholder')"
                @keydown="onSearchQueryKeydown"
              />
            </div>
            <select
              id="dashSearchWork"
              ref="searchWorkSelectEl"
              class="control"
              :aria-label="i18n.t('field.work')"
            >
              <option value="">{{ i18n.t("dashboard.all_works") }}</option>
              <option v-for="item in works" :key="String(item.work)" :value="item.work">
                {{ item.work }}
              </option>
            </select>
            <button class="btn dark" id="dashRunSearch" @click="goSearch">
              <AppIcon name="search" />{{ i18n.t("ui.search") }}
            </button>
          </div>
          <div class="dashboard-search-footer">
            <button
              class="dashboard-advanced-link"
              id="dashAdvancedSearch"
              @click="goSearch"
              v-text="`${i18n.t('dashboard.advanced_filters')} →`"
            ></button>
            <p class="dashboard-search-help">
              {{
                i18n.t("dashboard.search_help")
              }}
            </p>
          </div>
        </article>
      </section>
      <section class="dashboard-page-middle">
        <article class="card dashboard-overview-card">
          <div class="dashboard-card-title">
            <span class="dashboard-title-icon"><AppIcon name="books" /></span>
            <b>{{ i18n.t("dashboard.corpus_overview") }}</b>
          </div>
          <div class="dashboard-overview-grid">
            <button data-dashboard-nav="works" @click="goNav('works')">
              <span class="dashboard-overview-icon"><AppIcon name="books" /></span>
              <strong>{{ works.length.toLocaleString() }}</strong>
              <small>{{ i18n.t("dashboard.works") }}</small>
            </button>
            <button
              :data-dashboard-nav="isResearcher ? 'vector' : 'list'"
              @click="goNav(isResearcher ? 'vector' : 'list')"
            >
              <span class="dashboard-overview-icon"><AppIcon name="record" /></span>
              <strong>{{ Number(totals.records || 0).toLocaleString() }}</strong>
              <small>{{ i18n.t("dashboard.records") }}</small>
            </button>
            <button
              :disabled="isResearcher"
              :data-disabled-reason="
                isResearcher
                  ? i18n.t('dashboard.words_hidden_researcher')
                  : undefined
              "
            >
              <span class="dashboard-overview-icon"><AppIcon name="list" /></span>
              <strong>{{ isResearcher ? "—" : runtime.compactNumber(words) }}</strong>
              <small>{{ i18n.t("dashboard.total_words") }}</small>
            </button>
            <button data-dashboard-nav="vector" @click="goNav('vector')">
              <span class="dashboard-overview-icon"><AppIcon name="database" /></span>
              <strong>{{ Number(totals.dbs || 0).toLocaleString() }}</strong>
              <small>{{ i18n.t("dashboard.databases") }}</small>
            </button>
          </div>
        </article>
        <article
          class="card dashboard-average-card dashboard-metric-carousel"
          aria-roledescription="carousel"
        >
          <div class="dashboard-metric-head">
            <div class="dashboard-card-title">
              <span class="dashboard-title-icon"><AppIcon name="chart" /></span>
              <b>{{ activeMetric()?.title }}</b>
            </div>
            <div class="dashboard-metric-controls">
              <button
                class="dashboard-metric-arrow"
                id="dashMetricPrev"
                type="button"
                :aria-label="i18n.t('dashboard.previous_chart')"
                @click="stepMetric(-1)"
                v-text="'←'"
              ></button>
              <span>{{ activeMetricIndex + 1 }} / {{ metricSets.length }}</span>
              <button
                class="dashboard-metric-arrow"
                id="dashMetricNext"
                type="button"
                :aria-label="i18n.t('dashboard.next_chart')"
                @click="stepMetric(1)"
                v-text="'→'"
              ></button>
            </div>
          </div>
          <div
            class="dashboard-metric-body"
            v-html="metricBodyHtml()"
            @click="onMetricBodyClick"
          ></div>
          <div
            class="dashboard-metric-dots"
            role="tablist"
            :aria-label="i18n.t('dashboard.work_charts')"
          >
            <button
              v-for="(metric, index) in metricSets"
              :key="String(metric.id)"
              ref="metricDotEls"
              type="button"
              role="tab"
              :data-dashboard-metric="index"
              :class="{ active: index === activeMetricIndex }"
              :aria-label="String(metric.title)"
              :aria-selected="index === activeMetricIndex"
              :tabindex="index === activeMetricIndex ? 0 : -1"
              @click="selectMetric(index)"
              @keydown="onMetricDotKeydown"
            ></button>
          </div>
        </article>
        <article class="card dashboard-activity-card">
          <div class="dashboard-card-title">
            <span class="dashboard-title-icon"><AppIcon name="history" /></span>
            <b>{{ i18n.t("dashboard.recent_activity") }}</b>
          </div>
          <div class="dashboard-activity-list">
            <template v-if="recent.length">
              <button
                v-for="(item, index) in recent"
                :key="index"
                class="dashboard-activity-row"
                v-bind="
                  item.kind === 'annotation'
                    ? {
                        'data-recent-server-annotation-record':
                          (item.annotation as Any).record_id || '',
                        'data-recent-server-annotation-store': (item.annotation as Any).store || '',
                      }
                    : item.kind === 'rag'
                      ? (item.job as Any).status === 'completed'
                        ? { 'data-recent-rag-result': (item.job as Any).id }
                        : {}
                      : {
                          'data-recent-file': (item.file as Any).id,
                          'data-recent-index': item.index,
                        }
                "
                @click="
                  item.kind === 'annotation'
                    ? openSharedAnnotation(
                        (item.annotation as Any).store || '',
                        (item.annotation as Any).record_id || '',
                      )
                    : item.kind === 'record'
                      ? openRecentRecord((item.file as Any).id, Number(item.index))
                      : undefined
                "
              >
                <span class="dashboard-activity-clock">
                  <AppIcon
                    :name="
                      item.kind === 'rag'
                        ? 'spark'
                        : item.kind === 'annotation'
                          ? 'record'
                          : 'history'
                    "
                  />
                </span>
                <time>{{
                  runtime.relativeTime(
                    item.kind === "record" ? (item.update as Any).timestamp : item.timestamp,
                  )
                }}</time>
                <span v-if="item.kind === 'annotation'">
                  {{ i18n.t("annotations.record_note") }} ·
                  {{
                    (item.annotation as Any).work ||
                    (item.annotation as Any).record_id ||
                    i18n.t("nav.record")
                  }}
                </span>
                <span v-else-if="item.kind === 'rag'">
                  {{ i18n.t("nav.rag") }} ·
                  {{
                    String((item.job as Any).prompt || (item.job as Any).label || "RAG").slice(
                      0,
                      90,
                    )
                  }}
                </span>
                <span v-else>
                  {{
                    runtime.label(
                      (item.update as Any).field_name ||
                        i18n.t("dashboard.updated_record"),
                    )
                  }}
                  ·
                  {{
                    (item.record as Any).work ||
                    (item.record as Any).record_id ||
                    (item.file as Any).name
                  }}
                </span>
              </button>
            </template>
            <div v-else class="dashboard-activity-empty">
              {{
                i18n.t("dashboard.no_recent_activity")
              }}
            </div>
          </div>
        </article>
      </section>
      <section class="card dashboard-works-card">
        <div class="dashboard-section-heading">
          <div class="dashboard-card-title">
            <span class="dashboard-title-icon"><AppIcon name="books" /></span>
            <b>{{ i18n.t("dashboard.works") }}</b>
          </div>
          <button
            class="dashboard-text-link"
            id="dashViewAllWorks"
            @click="goNav('works')"
            v-text="`${i18n.t('dashboard.view_all_works')} →`"
          ></button>
        </div>
        <div class="dashboard-work-carousel-shell">
          <button
            class="carousel-arrow"
            id="dashWorksPrev"
            type="button"
            :title="i18n.t('ui.previous')"
            :aria-label="i18n.t('ui.previous')"
            @click="scrollWorks(-1)"
            v-text="'‹'"
          ></button>
          <div class="dashboard-work-strip" id="dashWorksCarousel" ref="worksCarouselEl">
            <template v-if="works.length">
              <button
                v-for="(item, index) in works"
                :key="String(item.work)"
                class="dashboard-work-card"
                :data-dashboard-work="item.work"
                @click="openWork(String(item.work))"
              >
                <img
                  v-if="item.cover"
                  class="dashboard-book-cover image"
                  :src="String(item.cover)"
                  :alt="i18n.tf('works.cover_alt', { work: String(item.work) })"
                  loading="lazy"
                />
                <span v-else class="dashboard-book-cover placeholder">{{
                  String(index + 1).padStart(2, "0")
                }}</span>
                <span>
                  <b>{{ item.work }}</b>
                  <small>{{
                    item.year || i18n.t("dashboard.year_not_recorded")
                  }}</small>
                  <small
                    >{{ Number(item.count).toLocaleString() }}
                    {{ i18n.t("dynamic.records") }}</small
                  >
                </span>
              </button>
            </template>
            <div v-else class="note">{{ i18n.t("research.no_works") }}</div>
          </div>
          <button
            class="carousel-arrow"
            id="dashWorksNext"
            type="button"
            :title="i18n.t('ui.next')"
            :aria-label="i18n.t('ui.next')"
            @click="scrollWorks(1)"
            v-text="'›'"
          ></button>
        </div>
      </section>
      <section class="dashboard-page-lower">
        <article
          v-if="isResearcher && runtime.hasCapability('appearance.manage')"
          class="card dashboard-quick-card dashboard-appearance-card"
        >
          <div class="dashboard-card-title">
            <span class="dashboard-title-icon" v-html="icon('gear')"></span>
            <b>{{ i18n.t("dashboard.appearance") }}</b>
          </div>
          <p>
            {{
              i18n.t("dashboard.appearance_help")
            }}
          </p>
          <fieldset class="dashboard-theme-options">
            <legend>{{ i18n.t("dashboard.interface_theme") }}</legend>
            <label
              v-for="pair in [
                ['green', i18n.t('theme.green')],
                ['blue', i18n.t('theme.blue')],
                ['slate', i18n.t('theme.slate')],
              ]"
              :key="pair[0]"
            >
              <input
                type="radio"
                name="dashboard-theme"
                :data-dashboard-theme="pair[0]"
                :checked="uiColorTheme === pair[0]"
                @change="setUiTheme(pair[0])"
              />
              <span class="theme-swatch" :class="pair[0]" aria-hidden="true"></span>
              <b>{{ pair[1] }}</b>
            </label>
          </fieldset>
          <button class="btn" id="dashAppearanceSettings" @click="openAppearanceSettings">
            {{ i18n.t("dashboard.more_appearance_settings") }}
          </button>
        </article>
        <article v-else-if="isResearcher" class="card dashboard-quick-card">
          <div class="dashboard-card-title">
            <span class="dashboard-title-icon" v-html="icon('gear')"></span>
            <b>{{ i18n.t("dashboard.appearance") }}</b>
          </div>
          <p>
            {{
              i18n.t("permissions.appearance_denied")
            }}
          </p>
        </article>
        <article v-else class="card dashboard-quick-card dashboard-language-card">
          <div class="dashboard-card-title">
            <span class="dashboard-title-icon" v-html="icon('gear')"></span>
            <b>{{ i18n.t("dashboard.language_settings") }}</b>
          </div>
          <p>
            {{
              i18n.t("dashboard.language_settings_help")
            }}
          </p>
          <div class="dashboard-quick-field dashboard-locale-field">
            <span>{{ i18n.t("dashboard.interface_language") }}</span>
            <b
              ><i class="dashboard-locale-symbol">{{ currentLanguageFlag }}</i
              >{{ currentLanguage }}</b
            >
          </div>
          <button class="btn primary" id="dashLanguages" @click="openLanguages">
            {{ i18n.t("dashboard.manage_languages") }}
          </button>
        </article>
        <article class="card dashboard-quick-card dashboard-provider-card">
          <div class="dashboard-card-title">
            <span class="dashboard-title-icon"><AppIcon name="spark" /></span>
            <b>{{ i18n.t("dashboard.llm_provider_settings") }}</b>
          </div>
          <p>
            {{
              i18n.t("dashboard.llm_provider_help")
            }}
          </p>
          <div class="dashboard-provider-fields">
            <div class="dashboard-quick-field">
              <span>{{ i18n.t("dashboard.default_provider") }}</span>
              <b>{{
                currentProvider
                  ? runtime.providerDisplayName(currentProvider)
                  : i18n.t("dashboard.not_configured")
              }}</b>
            </div>
            <div class="dashboard-quick-field">
              <span>{{ i18n.t("dashboard.model") }}</span>
              <b>{{ currentProvider ? (currentProvider as Any).model || "auto" : "—" }}</b>
            </div>
          </div>
          <button class="btn" id="dashProviders" @click="openProviders">
            {{
              isResearcher
                ? i18n.t("nav.rag")
                : i18n.t("dashboard.manage_provider")
            }}
          </button>
        </article>
        <article class="card dashboard-quick-card dashboard-record-preview">
          <div class="dashboard-section-heading">
            <div class="dashboard-card-title">
              <span class="dashboard-title-icon"><AppIcon name="record" /></span>
              <b>{{ i18n.t("dashboard.record_view") }}</b>
            </div>
            <button
              class="dashboard-text-link"
              id="dashRecordView"
              :disabled="!previewTarget"
              :data-disabled-reason="
                !previewTarget
                  ? i18n.t('dashboard.no_record_available')
                  : undefined
              "
              @click="openRecordPreview"
              v-text="`${i18n.t('research.open')} →`"
            ></button>
          </div>
          <template v-if="previewRecord">
            <div class="dashboard-record-state">
              {{
                previewLastViewed
                  ? i18n.t("dashboard.last_viewed_record")
                  : i18n.t("dashboard.random_record")
              }}
            </div>
            <div class="dashboard-record-meta">
              <b>{{
                (previewRecord as Any).work ||
                (previewRecord as Any).record_id ||
                i18n.t("dashboard.record")
              }}</b>
              <span class="dashboard-record-pages">{{
                mlaPageSpan(previewRecord as Any) || ""
              }}</span>
            </div>
            <div class="dashboard-record-text">
              {{
                String((previewRecord as Any).text || "")
                  .replace(/\s+/g, " ")
                  .slice(0, 220)
              }}{{ String((previewRecord as Any).text || "").length > 220 ? "…" : "" }}
            </div>
          </template>
          <div v-else class="dashboard-record-empty">
            {{ i18n.t("dashboard.no_record_selected") }}
          </div>
        </article>
        <article
          v-if="latestAnnotation"
          class="card dashboard-quick-card dashboard-annotations-card"
        >
          <div class="dashboard-section-heading">
            <div class="dashboard-card-title">
              <span class="dashboard-title-icon"><AppIcon name="record" /></span>
              <b>{{ i18n.t("dashboard.latest_annotation") }}</b>
            </div>
            <button
              class="dashboard-text-link"
              id="dashAnnotations"
              @click="openAnnotations"
              v-text="`${i18n.t('annotations.view_all')} →`"
            ></button>
          </div>
          <button
            class="dashboard-annotation-preview"
            v-bind="
              (latestAnnotation as Any).server
                ? {
                    'data-recent-server-annotation-record':
                      (latestAnnotation as Any).annotation.record_id || '',
                    'data-recent-server-annotation-store':
                      (latestAnnotation as Any).annotation.store || '',
                  }
                : {
                    'data-recent-annotation-file': (latestAnnotation as Any).file.id,
                    'data-recent-annotation-index': (latestAnnotation as Any).index,
                  }
            "
            @click="
              (latestAnnotation as Any).server
                ? openSharedAnnotation(
                    (latestAnnotation as Any).annotation.store || '',
                    (latestAnnotation as Any).annotation.record_id || '',
                  )
                : openRecentAnnotation(
                    (latestAnnotation as Any).file.id,
                    Number((latestAnnotation as Any).index),
                  )
            "
          >
            <div class="dashboard-annotation-meta">
              <span class="dashboard-annotation-work">{{ (latestAnnotation as Any).work }}</span>
              <span class="dashboard-annotation-pages">{{
                mlaPageSpan((latestAnnotation as Any).record) ||
                i18n.t("record.page_not_recorded")
              }}</span>
              <span class="dashboard-annotation-author">{{
                (latestAnnotation as Any).annotation.initiated_by ||
                (latestAnnotation as Any).annotation.author ||
                i18n.t("annotations.unknown_author")
              }}</span>
              <time>{{
                runtime.formatTimestamp((latestAnnotation as Any).annotation.created_at)
              }}</time>
              <small>{{
                (latestAnnotation as Any).record.record_id || i18n.t("nav.record")
              }}</small>
            </div>
            <p v-if="(latestAnnotation as Any).annotation.note">
              {{ (latestAnnotation as Any).annotation.note }}
            </p>
            <blockquote v-else-if="(latestAnnotation as Any).annotation.quote">
              {{ (latestAnnotation as Any).annotation.quote }}
            </blockquote>
            <p v-else>{{ i18n.t("annotations.record_note") }}</p>
          </button>
        </article>
        <article v-else class="card dashboard-quick-card dashboard-annotations-card">
          <div class="dashboard-section-heading">
            <div class="dashboard-card-title">
              <span class="dashboard-title-icon"><AppIcon name="record" /></span>
              <b>{{ i18n.t("dashboard.annotations") }}</b>
            </div>
            <button
              class="dashboard-text-link"
              id="dashAnnotations"
              @click="openAnnotations"
              v-text="`${i18n.t('research.open')} →`"
            ></button>
          </div>
          <p>
            {{
              isResearcher
                ? i18n.t("annotations.researcher_help")
                : i18n.t("dashboard.annotations_help")
            }}
          </p>
        </article>
      </section>
      <section
        v-if="corpusBuilds.length || !isResearcher"
        class="card dashboard-corpus-builds"
        :aria-label="corpusBuildsAriaLabel"
      >
        <div class="dashboard-section-heading">
          <div class="dashboard-card-title">
            <span class="dashboard-title-icon"><AppIcon name="pdf" /></span>
            <b>{{ corpusBuildsAriaLabel }}</b>
            <span v-if="corpusBuildsActive" class="dashboard-corpus-active">
              {{ corpusBuildsActive }} {{ i18n.t("operations.active") }}
            </span>
          </div>
          <button
            class="dashboard-text-link"
            id="dashCorpusBuilder"
            @click="openCorpusBuilder"
            v-text="`${i18n.t('pdf_corpus.open_builder')} →`"
          ></button>
        </div>
        <p class="dashboard-corpus-help">
          {{
            i18n.t("pdf_corpus.home_help")
          }}
        </p>
        <div class="dashboard-corpus-list">
          <template v-if="corpusBuilds.length">
            <button
              v-for="job in corpusBuilds"
              :key="String((job as Any).id)"
              type="button"
              class="dashboard-corpus-row"
              :data-dashboard-corpus-build="(job as Any).id"
              @click="openCorpusBuild(String((job as Any).id))"
            >
              <span
                class="dashboard-corpus-state"
                :class="(job as Any).status || ''"
                aria-hidden="true"
              ></span>
              <span class="dashboard-corpus-copy">
                <b>{{
                  (job as Any).source_filename || i18n.t("pdf_corpus.source_pdf")
                }}</b>
                <small>{{ corpusBuildStatusLabel(job as Any) }}</small>
              </span>
              <span class="dashboard-corpus-progress">
                <b>{{ corpusBuildPercent(job as Any) }}%</b>
                <i><span :style="`width:${corpusBuildPercent(job as Any)}%`"></span></i>
              </span>
            </button>
          </template>
          <div v-else class="dashboard-corpus-empty">
            {{
              i18n.t("pdf_corpus.home_empty")
            }}
          </div>
        </div>
      </section>
      <div id="operationsPanelHost"></div>
    </div>
  </main>
</template>
