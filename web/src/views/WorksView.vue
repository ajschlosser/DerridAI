<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import * as runtime from "../runtime/runtime.js";
import AppIcon from "../components/AppIcon.vue";
import UiButton from "../components/ui/UiButton.vue";
import { useI18nStore } from "../stores/i18n";

interface WorkSummary {
  work: string;
  count: number;
  review: number;
  files: string[];
  authors: string[];
  years: Array<string | number>;
  cover: string;
  status: string;
  metadata: Array<{field: string; mixed: boolean; value: unknown}>;
  citation: string;
  insights: Array<{id: string; field: string; type: string; values: Array<{key: string; value: number; other: boolean}>}>;
}
interface WorksSnapshot {
  activeStore: string;
  selectedWork: string;
  works: WorkSummary[];
}

const i18n = useI18nStore();
const query = ref("");
const snapshot = ref<WorksSnapshot>({activeStore: "", selectedWork: "", works: []});
const loading = ref(true);
const error = ref("");

const filteredWorks = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase(i18n.locale);
  return snapshot.value.works.filter(work => !needle || work.work.toLocaleLowerCase(i18n.locale).includes(needle));
});
const totalRecords = computed(() => snapshot.value.works.reduce((total, work) => total + work.count, 0));
const selected = computed(() => snapshot.value.works.find(work => work.work === snapshot.value.selectedWork) || null);
const corpusDbAvailable = computed(() => Boolean(runtime.hasCorpusDb?.()));
const canBulkPopulate = computed(() => snapshot.value.works.length > 0 && Boolean(runtime.getProviderProfilesForUi?.()?.length));

function refresh() {
  loading.value = true;
  error.value = "";
  try {
    snapshot.value = (runtime.getWorksWorkspaceSnapshot?.() || {activeStore: "", selectedWork: "", works: []}) as WorksSnapshot;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}
function selectWork(work: string) {
  runtime.state.workOverview = work;
  runtime.persistPrefs();
  refresh();
}
function statusLabel(status: string) {
  if (status === "synced") return i18n.t("works.synced", "Synced");
  if (status === "changed") return i18n.t("works.pending_changes", "Pending changes");
  if (status === "exists") return i18n.t("works.in_database", "In database");
  if (status === "absent") return i18n.t("works.not_in_database", "Not in database");
  if (status === "none") return i18n.t("works.no_database", "No database");
  return i18n.t("works.status_loading", "Checking status");
}
function openRecords(work: WorkSummary, needsReview = false) {
  runtime.openWorksSearch?.(work.work, {needsReview});
}
function editMetadata(work: WorkSummary) {
  runtime.openWorksMetadataEditor?.(work.work);
}
function populateMetadata(work: WorkSummary) {
  runtime.openWorksMetadataLlm?.(work.work);
}
function openInsight(work: WorkSummary, field: string, value: string) {
  runtime.openWorksInsight?.(work.work, field, value);
}
function metadataLabel(field: string) {
  return i18n.t(`record.${field}`, field.replaceAll("_", " "));
}
function metadataText(item: WorkSummary["metadata"][number]) {
  if (item.mixed) return i18n.t("works.mixed", "Mixed");
  if (Array.isArray(item.value)) return item.value.join(", ");
  return item.value === null || item.value === undefined || item.value === "" ? "—" : String(item.value);
}
function insightTitle(id: string) {
  const titles: Record<string, [string, string]> = {
    persons: ["dashboard.top_persons_work", "Top persons mentioned"],
    concepts: ["dashboard.top_concepts_work", "Top concepts mentioned"],
    topics: ["dashboard.top_topics_work", "Top topics"],
    targets: ["dashboard.top_discourse_targets_work", "Top discourse targets"],
    roles: ["dashboard.discourse_roles_share_work", "Discourse roles"],
  };
  const [key, fallback] = titles[id] || ["works.work_insights", "Work insights"];
  return i18n.t(key, fallback).replace(" in the work", "").replace(" mentioned in the work", "");
}
async function syncWork(work: WorkSummary) {
  if (!runtime.hasCorpusDb?.()) return;
  await runtime.syncWorks?.(work.work);
  refresh();
}
function separateWorks() { runtime.openWorksSeparate?.(); }
function populateAll() { runtime.openWorksBulkMetadataLlm?.(); }
function openAnnotations(work: WorkSummary) { runtime.openWorksAnnotations?.(work.work); }
function removeWork(work: WorkSummary) { runtime.openWorksRemove?.(work.work); }
function addJsonl() {
  document.querySelector<HTMLInputElement>("#fileInput")?.click();
}
function onWorksChanged() {
  refresh();
}
onMounted(() => {
  refresh();
  window.addEventListener("derridai:works-changed", onWorksChanged);
});
onUnmounted(() => window.removeEventListener("derridai:works-changed", onWorksChanged));
</script>

<template>
  <main class="works-native-page">
    <header class="works-page-header">
      <div>
        <p class="page-kicker">{{ i18n.t("section.corpus", "Corpus") }}</p>
        <h1>{{ i18n.t("works.title", "Works") }}</h1>
        <p>{{ i18n.t("works.page_help", "Organize, inspect, and synchronize the works in your scholarly corpus.") }}</p>
      </div>
      <div class="works-page-summary" aria-live="polite">
        <strong>{{ snapshot.works.length.toLocaleString(i18n.locale) }}</strong>
        <span>{{ i18n.t("works.title_count", "works") }}</span>
        <strong>{{ totalRecords.toLocaleString(i18n.locale) }}</strong>
        <span>{{ i18n.t("dynamic.records", "records") }}</span>
      </div>
    </header>

    <div v-if="error" class="info error" role="alert">{{ error }}</div>

    <section class="works-toolbar card" :aria-label="i18n.t('works.toolbar', 'Work library controls')">
      <label class="works-search">
        <span class="sr-only">{{ i18n.t("works.filter_title", "Filter works by title") }}</span>
        <AppIcon name="search" aria-hidden="true" />
        <input v-model="query" type="search" :placeholder="i18n.t('works.filter_title', 'Filter works by title')" />
      </label>
      <div class="works-toolbar-actions">
        <UiButton icon="plus" :label="i18n.t('works.add_jsonl', 'Add a JSONL file')" @click="addJsonl" />
        <UiButton size="small" :label="i18n.t('works.separate_jsonl', 'Separate works')" @click="separateWorks" />
        <UiButton size="small" variant="soft" :disabled="!canBulkPopulate" :label="i18n.t('works.populate_all_metadata', 'Populate all metadata with LLM')" @click="populateAll" />
        <span class="works-database-context">{{ snapshot.activeStore || i18n.t("research.none_selected", "No database selected") }}</span>
      </div>
    </section>

    <section v-if="loading" class="card works-loading" aria-live="polite">{{ i18n.t("works.loading", "Loading works") }}</section>
    <section v-else-if="!filteredWorks.length" class="card">
      <div class="works-empty">
        <AppIcon name="books" aria-hidden="true" />
        <h2>{{ query ? i18n.t("works.no_matches", "No works match this search") : i18n.t("works.no_works", "No works loaded yet") }}</h2>
        <p>{{ query ? i18n.t("works.no_matches_help", "Try a different title or clear the filter.") : i18n.t("works.add_jsonl_help", "Open another corpus source and add its works to this workspace.") }}</p>
        <UiButton v-if="!query" variant="primary" icon="plus" :label="i18n.t('works.add_jsonl', 'Add a JSONL file')" @click="addJsonl" />
      </div>
    </section>

    <section v-else class="works-layout" :aria-label="i18n.t('works.library', 'Work library')">
      <div class="works-library" :aria-label="i18n.t('works.library', 'Work library')">
        <article v-for="work in filteredWorks" :key="work.work" class="work-card card" :class="{selected: selected?.work === work.work}">
          <button class="work-card-select" type="button" :aria-current="selected?.work === work.work ? 'true' : undefined" @click="selectWork(work.work)">
            <span class="work-cover" aria-hidden="true">
              <img v-if="work.cover" :src="work.cover" alt="" loading="lazy" />
              <AppIcon v-else name="books" />
            </span>
            <span class="work-card-copy">
              <strong>{{ work.work }}</strong>
              <small>{{ work.authors.join(', ') || i18n.t('works.unknown_author', 'Unknown author') }}<template v-if="work.years.length"> · {{ work.years.join(', ') }}</template></small>
              <span class="work-card-status" :class="`status-${work.status}`"><i aria-hidden="true"></i>{{ statusLabel(work.status) }}</span>
            </span>
          </button>
          <div class="work-card-stats">
            <button type="button" @click="openRecords(work)"><strong>{{ work.count.toLocaleString(i18n.locale) }}</strong><span>{{ i18n.t('dynamic.records', 'records') }}</span></button>
            <button type="button" :disabled="!work.review" @click="openRecords(work, true)"><strong>{{ work.review.toLocaleString(i18n.locale) }}</strong><span>{{ i18n.t('works.need_review', 'need review') }}</span></button>
            <span><strong>{{ work.files.length.toLocaleString(i18n.locale) }}</strong><span>{{ i18n.t('works.files', 'files') }}</span></span>
          </div>
          <div class="work-card-actions">
            <UiButton size="small" :disabled="!corpusDbAvailable" :label="i18n.t('works.sync', 'Sync')" @click="syncWork(work)" />
            <UiButton size="small" :label="i18n.t('works.edit_metadata', 'Edit metadata')" @click="editMetadata(work)" />
            <UiButton size="small" variant="soft" :label="i18n.t('works.populate_metadata_llm', 'Populate metadata with LLM')" @click="populateMetadata(work)" />
            <UiButton v-if="work.review" size="small" :label="i18n.tf('works.review_flagged', 'Review flagged ({count})', {count: work.review.toLocaleString(i18n.locale)})" @click="openRecords(work, true)" />
            <UiButton size="small" :label="i18n.t('works.view_annotations', 'Annotations')" @click="openAnnotations(work)" />
            <UiButton size="small" variant="danger" :label="i18n.t('works.remove_entire', 'Remove entire work')" @click="removeWork(work)" />
          </div>
        </article>
      </div>

      <aside v-if="selected" class="works-selection card" aria-live="polite">
        <p class="page-kicker">{{ i18n.t("works.selected_work", "Selected work") }}</p>
        <div class="works-selection-cover">
          <img v-if="selected.cover" :src="selected.cover" alt="" loading="lazy" />
          <AppIcon v-else name="books" aria-hidden="true" />
        </div>
        <h2>{{ selected.work }}</h2>
        <p>{{ i18n.tf("works.selected_summary", "{records} records across {files} source files", {records: selected.count.toLocaleString(i18n.locale), files: selected.files.length.toLocaleString(i18n.locale)}) }}</p>
        <dl class="works-metadata-grid">
          <div v-for="item in selected.metadata.filter(item => item.value !== null || item.mixed)" :key="item.field">
            <dt>{{ metadataLabel(item.field) }}</dt>
            <dd>{{ metadataText(item) }}</dd>
          </div>
        </dl>
        <dl class="works-citation">
          <dt>{{ metadataLabel("full_citation") }}</dt>
          <dd>{{ selected.citation || "—" }}</dd>
        </dl>
        <section class="works-insights" :aria-label="i18n.t('works.work_insights', 'Work insights')">
          <div class="works-insights-heading">
            <h3>{{ i18n.t("works.indexed_patterns", "Indexed patterns in this work") }}</h3>
            <p>{{ i18n.t("works.work_insights_help", "Counts are derived from the currently loaded records and use the corpus metadata fields directly.") }}</p>
          </div>
          <div class="works-insights-grid">
            <article v-for="metric in selected.insights" :key="metric.id" class="works-insight-card">
              <h4>{{ insightTitle(metric.id) }}</h4>
              <ol v-if="metric.values.length">
                <li v-for="value in metric.values" :key="value.key">
                  <button v-if="!value.other" type="button" @click="openInsight(selected, metric.field, value.key)"><span>{{ value.key }}</span><strong>{{ value.value.toLocaleString(i18n.locale) }}</strong></button>
                  <span v-else><span>{{ value.key }}</span><strong>{{ value.value.toLocaleString(i18n.locale) }}</strong></span>
                </li>
              </ol>
              <p v-else class="note">{{ i18n.t("works.no_indexed_values", "No indexed values in the loaded records.") }}</p>
            </article>
          </div>
        </section>
        <div class="works-selection-actions">
          .works-selection{position:sticky;top:calc(var(--ref-topbar) + 58px);display:grid;gap:8px;padding:16px}.works-selection-cover{width:76px;height:112px;display:grid;place-items:center;overflow:hidden;border:1px solid var(--ref-line);border-radius:5px;background:#f1f4f6;color:#8794a5}.works-selection-cover img{width:100%;height:100%;object-fit:cover}.works-selection h2{margin:0;color:var(--ref-text);font:600 1.35rem/1.2 Georgia,"Times New Roman",serif;overflow-wrap:anywhere}.works-selection>p:not(.page-kicker){margin:0;color:var(--ref-muted);font-size:.875rem;line-height:1.5}.works-metadata-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin:6px 0 0}.works-metadata-grid>div,.works-citation{min-width:0;padding:7px 8px;border:1px solid var(--ref-line);border-radius:6px;background:#fafbfd}.works-metadata-grid dt,.works-citation dt{color:var(--ref-muted);font-size:.6875rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase}.works-metadata-grid dd,.works-citation dd{margin:3px 0 0;color:var(--ref-text);font-size:.75rem;overflow-wrap:anywhere}.works-insights{display:grid;gap:7px;margin-top:4px}.works-insights-heading h3{margin:0;color:var(--ref-text);font-size:.9375rem}.works-insights-heading p{margin:3px 0 0;color:var(--ref-muted);font-size:.75rem;line-height:1.4}.works-insights-grid{display:grid;gap:7px}.works-insight-card{padding:8px;border:1px solid var(--ref-line);border-radius:6px;background:#fff}.works-insight-card h4{margin:0 0 5px;color:var(--ref-muted);font-size:.6875rem;letter-spacing:.04em;text-transform:uppercase}.works-insight-card ol{display:grid;gap:2px;margin:0;padding:0;list-style:none}.works-insight-card li>button,.works-insight-card li>span{display:flex;justify-content:space-between;gap:7px;width:100%;padding:3px 4px;border:0;background:transparent;color:var(--ref-text);text-align:left;font-size:.75rem}.works-insight-card li>button{cursor:pointer}.works-insight-card li>button:hover{background:var(--ui-accent-soft);color:var(--ui-accent-dark)}.works-insight-card strong{font-variant-numeric:tabular-nums}.works-selection-actions{display:flex;flex-wrap:wrap;gap:7px;margin-top:4px}.works-empty,.works-loading{display:grid;justify-items:center;gap:10px;padding:48px 20px;text-align:center}.works-empty>svg{width:42px;height:42px;color:var(--ui-accent)}.works-empty h2{margin:0;color:var(--ref-text);font:600 1.3rem/1.2 Georgia,"Times New Roman",serif}.works-empty p{max-width:52ch;margin:0;color:var(--ref-muted)}
          <UiButton variant="primary" icon="search" :label="i18n.t('works.search_records', 'Search records')" @click="openRecords(selected)" />
          <UiButton icon="edit" :label="i18n.t('works.edit_metadata', 'Edit work metadata')" @click="editMetadata(selected)" />
        </div>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.works-native-page{width:min(1540px,calc(100% - 34px));margin:18px auto 56px;display:grid;gap:16px}.works-page-header{display:flex;justify-content:space-between;gap:24px;align-items:end}.page-kicker{margin:0 0 5px;color:var(--ui-accent-dark);font-size:.75rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.works-page-header h1{margin:0;color:var(--ref-text);font:600 2rem/1.1 Georgia,"Times New Roman",serif}.works-page-header p:not(.page-kicker){margin:7px 0 0;color:var(--ref-muted);font-size:.9375rem}.works-page-summary{display:grid;grid-template-columns:auto auto;gap:0 8px;align-items:baseline;min-width:150px}.works-page-summary strong{color:var(--ui-accent-dark);font-size:1.25rem;font-variant-numeric:tabular-nums;text-align:right}.works-page-summary span{color:var(--ref-muted);font-size:.8125rem}.works-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 12px}.works-search{display:grid;grid-template-columns:18px minmax(0,1fr);align-items:center;gap:7px;min-width:min(420px,100%);height:40px;padding:0 10px;border:1px solid var(--ref-line-strong);border-radius:7px;background:#fff;color:var(--ui-accent-dark)}.works-search input{width:100%;min-width:0;border:0;outline:0;background:transparent;color:var(--ref-text);font:inherit}.works-toolbar-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.works-database-context{max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ref-muted);font-size:.8125rem}.works-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,330px);gap:16px;align-items:start}.works-library{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px}.work-card{display:grid;gap:10px;padding:13px}.work-card.selected{border-color:var(--ui-accent);box-shadow:0 0 0 2px var(--ui-accent-focus)}.work-card-select{display:grid;grid-template-columns:58px minmax(0,1fr);gap:11px;align-items:start;width:100%;padding:0;border:0;background:transparent;color:inherit;text-align:left;cursor:pointer}.work-card-select:focus-visible{outline:3px solid var(--ui-accent-focus);outline-offset:4px;border-radius:7px}.work-cover{width:58px;height:84px;display:grid;place-items:center;overflow:hidden;border:1px solid var(--ref-line);border-radius:5px;background:#f1f4f6;color:#8794a5}.work-cover img{width:100%;height:100%;object-fit:cover}.work-card-copy{display:grid;gap:5px;min-width:0}.work-card-copy strong{overflow-wrap:anywhere;color:var(--ref-text);font-size:1rem;line-height:1.25}.work-card-copy small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ref-muted);font-size:.8125rem}.work-card-status{display:flex;align-items:center;gap:5px;color:var(--ref-muted);font-size:.75rem;font-weight:700}.work-card-status i{width:7px;height:7px;border-radius:50%;background:#94a3b8}.work-card-status.status-synced i{background:#27805f}.work-card-status.status-changed i{background:#b7791f}.work-card-status.status-absent i{background:#b44a4a}.work-card-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.work-card-stats>*{display:grid;gap:2px;padding:7px 8px;border:1px solid var(--ref-line);border-radius:6px;background:#fafbfd;text-align:left}.work-card-stats button{color:var(--ui-accent-dark);cursor:pointer}.work-card-stats button:hover:not(:disabled){background:var(--ui-accent-soft)}.work-card-stats button:disabled{color:var(--ref-muted);cursor:default}.work-card-stats strong{font-size:.9375rem;font-variant-numeric:tabular-nums}.work-card-stats span{color:var(--ref-muted);font-size:.75rem}.work-card-actions{display:flex;flex-wrap:wrap;gap:6px}.works-selection{position:sticky;top:calc(var(--ref-topbar) + 58px);display:grid;gap:8px;padding:16px}.works-selection h2{margin:0;color:var(--ref-text);font:600 1.35rem/1.2 Georgia,"Times New Roman",serif;overflow-wrap:anywhere}.works-selection>p:not(.page-kicker){margin:0;color:var(--ref-muted);font-size:.875rem;line-height:1.5}.works-selection-actions{display:flex;flex-wrap:wrap;gap:7px;margin-top:4px}.works-empty,.works-loading{display:grid;justify-items:center;gap:10px;padding:48px 20px;text-align:center}.works-empty>svg{width:42px;height:42px;color:var(--ui-accent)}.works-empty h2{margin:0;color:var(--ref-text);font:600 1.3rem/1.2 Georgia,"Times New Roman",serif}.works-empty p{max-width:52ch;margin:0;color:var(--ref-muted)}
@media(max-width:900px){.works-layout{grid-template-columns:1fr}.works-selection{position:static}.works-page-header{align-items:start;flex-direction:column}.works-page-summary{grid-template-columns:auto auto}}
@media(max-width:620px){.works-native-page{width:calc(100% - 16px);margin-top:10px}.works-toolbar{align-items:stretch;flex-direction:column}.works-search{min-width:0}.works-toolbar-actions{justify-content:space-between}.works-library{grid-template-columns:1fr}.work-card-actions .btn{flex:1}.work-card-stats{gap:4px}}
</style>
