<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { metadataMemoryApi, type MetadataMemoryPayload } from "../api/metadataMemory";
import MetadataMemoryRelations from "../components/metadata-memory/MetadataMemoryRelations.vue";
import MetadataMemoryTable from "../components/metadata-memory/MetadataMemoryTable.vue";
import AppIcon from "../components/AppIcon.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import UiTooltip from "../components/ui/UiTooltip.vue";
import { useI18nStore } from "../stores/i18n";

const i18n = useI18nStore();
const pageSize = 50;
const searchDebounceMs = 300;
const loading = ref(false);
const error = ref("");
const offset = ref(0);
const query = ref("");
const field = ref("");
const kind = ref("");
const buildId = ref("");
const language = ref("");
const payload = ref<MetadataMemoryPayload>({
  items: [],
  total: 0,
  offset: 0,
  limit: pageSize,
  summary: { entries: 0, evidence_bound: 0, corrections: 0, fields: 0, backends: 0 },
  facets: { fields: [], kinds: [], languages: [], builds: [] },
  derived: true,
  authoritative_source: "",
  available: true,
  error: "",
});
// Only the newest request may update the page, so slow earlier responses cannot overwrite it.
let requestSeq = 0;
let searchTimer: number | undefined;

const pageStart = computed(() => (payload.value.total ? offset.value + 1 : 0));
const pageEnd = computed(() => Math.min(offset.value + pageSize, payload.value.total));
const canPrevious = computed(() => offset.value > 0 && !loading.value);
const canNext = computed(() => offset.value + pageSize < payload.value.total && !loading.value);
const stats = computed(() => [
  { key: "entries", value: payload.value.summary.entries },
  { key: "evidence_bound", value: payload.value.summary.evidence_bound },
  { key: "corrections", value: payload.value.summary.corrections },
  { key: "fields", value: payload.value.summary.fields },
]);

function kindLabel(value: string): string {
  if (value === "positive") return i18n.t("metadata_memory.kind_positive");
  if (value === "correction") return i18n.t("metadata_memory.kind_correction");
  return value;
}

const activeFilters = computed(() => {
  const chips: Array<{ key: string; label: string; clear: () => void }> = [];
  const add = (key: string, name: string, value: string, clear: () => void) => {
    if (value) chips.push({ key, label: `${name}: ${value}`, clear });
  };
  add("q", i18n.t("metadata_memory.search"), query.value.trim(), () => (query.value = ""));
  add("field", i18n.t("metadata_memory.field"), field.value, () => (field.value = ""));
  add(
    "kind",
    i18n.t("metadata_memory.kind"),
    kind.value ? kindLabel(kind.value) : "",
    () => (kind.value = ""),
  );
  add("build", i18n.t("metadata_memory.build"), buildId.value, () => (buildId.value = ""));
  add("language", i18n.t("metadata_memory.language"), language.value, () => (language.value = ""));
  return chips;
});

async function load() {
  const seq = ++requestSeq;
  loading.value = true;
  error.value = "";
  try {
    const next = await metadataMemoryApi.list({
      limit: pageSize,
      offset: offset.value,
      field: field.value,
      kind: kind.value,
      build_id: buildId.value,
      language: language.value,
      q: query.value.trim(),
    });
    if (seq !== requestSeq) return;
    payload.value = next;
    if (!next.available && next.error) error.value = next.error;
  } catch (exc) {
    if (seq === requestSeq) error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    if (seq === requestSeq) loading.value = false;
  }
}

function applyFilters() {
  window.clearTimeout(searchTimer);
  offset.value = 0;
  void load();
}

function clearFilters() {
  window.clearTimeout(searchTimer);
  query.value = "";
  field.value = "";
  kind.value = "";
  buildId.value = "";
  language.value = "";
  // The watchers below reload once for the select changes; reload here when only the search changed.
  applyFilters();
}

function goTo(next: number) {
  offset.value = next;
  void load();
}

// Selects apply immediately; free text waits for a pause in typing.
watch([field, kind, buildId, language], applyFilters);
watch(query, () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(applyFilters, searchDebounceMs);
});
onBeforeUnmount(() => window.clearTimeout(searchTimer));
onMounted(() => void load());
</script>

<template>
  <main class="vue-native-page metadata-memory-page" aria-labelledby="metadata-memory-title">
    <UiPageHeader
      :kicker="i18n.t('section.ai_automation')"
      :title="i18n.t('metadata_memory.title')"
      title-id="metadata-memory-title"
      :description="i18n.t('metadata_memory.help')"
    >
      <template #actions>
        <UiButton :label="i18n.t('metadata_memory.refresh')" :disabled="loading" @click="load" />
      </template>
    </UiPageHeader>

    <p class="memory-contract">
      <strong>{{ i18n.t("metadata_memory.authority_title") }}</strong>
      {{ i18n.t("metadata_memory.authority_help") }}
    </p>

    <MetadataMemoryRelations />

    <section class="memory-summary" :aria-label="i18n.t('metadata_memory.summary')">
      <article v-for="stat in stats" :key="stat.key" class="card">
        <span class="stat-label">
          {{ i18n.t(`metadata_memory.${stat.key}`) }}
          <UiTooltip :text="i18n.t(`metadata_memory.${stat.key}_help`)" placement="bottom" />
        </span>
        <strong>{{ stat.value.toLocaleString(i18n.locale) }}</strong>
      </article>
    </section>

    <p v-if="error" class="info error" role="alert">
      {{ i18n.t("metadata_memory.unavailable") }}: {{ error }}
    </p>

    <section class="card memory-table-card" aria-labelledby="metadata-memory-table-title">
      <header class="table-heading">
        <div>
          <h2 id="metadata-memory-table-title">{{ i18n.t("metadata_memory.precedents") }}</h2>
          <p role="status">
            {{
              loading
                ? i18n.t("metadata_memory.updating")
                : i18n.tf("metadata_memory.showing", {
                    start: pageStart,
                    end: pageEnd,
                    total: payload.total,
                  })
            }}
          </p>
        </div>
      </header>

      <form class="memory-filters" role="search" @submit.prevent="applyFilters">
        <label class="filter-search">
          <span>{{ i18n.t("metadata_memory.search") }}</span>
          <input
            v-model="query"
            class="control"
            type="search"
            :placeholder="i18n.t('metadata_memory.search_placeholder')"
          />
        </label>
        <label>
          <span>{{ i18n.t("metadata_memory.field") }}</span>
          <select v-model="field" class="control">
            <option value="">{{ i18n.t("metadata_memory.all_fields") }}</option>
            <option v-for="value in payload.facets.fields" :key="value" :value="value">
              {{ value }}
            </option>
          </select>
        </label>
        <label>
          <span>{{ i18n.t("metadata_memory.kind") }}</span>
          <select v-model="kind" class="control">
            <option value="">{{ i18n.t("metadata_memory.all_kinds") }}</option>
            <option v-for="value in payload.facets.kinds" :key="value" :value="value">
              {{ kindLabel(value) }}
            </option>
          </select>
        </label>
        <label>
          <span>{{ i18n.t("metadata_memory.build") }}</span>
          <select v-model="buildId" class="control">
            <option value="">{{ i18n.t("metadata_memory.all_builds") }}</option>
            <option v-for="value in payload.facets.builds" :key="value" :value="value">
              {{ value }}
            </option>
          </select>
        </label>
        <label>
          <span>{{ i18n.t("metadata_memory.language") }}</span>
          <select v-model="language" class="control">
            <option value="">{{ i18n.t("metadata_memory.all_languages") }}</option>
            <option v-for="value in payload.facets.languages" :key="value" :value="value">
              {{ value }}
            </option>
          </select>
        </label>
      </form>

      <ul
        v-if="activeFilters.length"
        class="filter-chips"
        :aria-label="i18n.t('metadata_memory.active_filters')"
      >
        <li v-for="chip in activeFilters" :key="chip.key">
          <button
            type="button"
            class="chip"
            :aria-label="i18n.tf('metadata_memory.remove_filter', { label: chip.label })"
            @click="chip.clear()"
          >
            {{ chip.label }} <AppIcon name="close" />
          </button>
        </li>
        <li>
          <button type="button" class="chip-clear" @click="clearFilters">
            {{ i18n.t("metadata_memory.clear_filters") }}
          </button>
        </li>
      </ul>

      <MetadataMemoryTable
        :items="payload.items"
        :loading="loading"
        :filtered="activeFilters.length > 0"
      />

      <footer class="pagination">
        <UiButton
          :label="i18n.t('common.previous')"
          :disabled="!canPrevious"
          @click="goTo(Math.max(0, offset - pageSize))"
        />
        <span>{{ pageStart }}–{{ pageEnd }} / {{ payload.total }}</span>
        <UiButton
          :label="i18n.t('common.next')"
          :disabled="!canNext"
          @click="goTo(offset + pageSize)"
        />
      </footer>
    </section>
  </main>
</template>

<style scoped>
.metadata-memory-page {
  display: grid;
  gap: var(--page-gap, 12px);
  align-content: start;
}
.memory-contract {
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface-inset);
  line-height: 1.55;
}
.memory-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.memory-summary article {
  display: grid;
  gap: 4px;
  padding: 14px;
}
.stat-label {
  display: flex;
  align-items: center;
  gap: 2px;
  color: var(--text-secondary, var(--muted));
  font-size: 0.8125rem;
  font-weight: 700;
}
.memory-summary strong {
  font-size: 1.55rem;
}
.memory-table-card {
  min-width: 0;
  padding: 0;
  overflow: hidden;
}
.table-heading {
  padding: 14px;
}
.table-heading h2 {
  margin: 0;
  font-size: 1rem;
}
.table-heading p {
  margin: 4px 0 0;
  color: var(--text-secondary, var(--muted));
}
.memory-filters {
  display: grid;
  grid-template-columns: minmax(220px, 1.6fr) repeat(4, minmax(130px, 1fr));
  gap: 10px;
  align-items: end;
  padding: 0 14px 12px;
}
.memory-filters label {
  display: grid;
  gap: 5px;
  min-width: 0;
  color: var(--text-secondary, var(--muted));
  font-size: 0.8125rem;
  font-weight: 700;
}
.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0 14px 12px;
  list-style: none;
}
.chip,
.chip-clear {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 28px;
  padding: 3px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-inset);
  color: inherit;
  font: inherit;
  font-size: 0.8125rem;
  cursor: pointer;
}
.chip:hover {
  background: var(--surface-hover);
}
.chip-clear {
  border-color: transparent;
  background: none;
  color: var(--accent-fg, var(--accent));
  font-weight: 700;
  text-decoration: underline;
}
.chip:focus-visible,
.chip-clear:focus-visible {
  outline: var(--focus-ring-width, 3px) solid var(--focus-ring);
  outline-offset: 2px;
}
.chip :deep(svg) {
  width: 12px;
  height: 12px;
}
.pagination {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
}
@media (max-width: 1000px) {
  .memory-summary,
  .memory-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .filter-search {
    grid-column: 1 / -1;
  }
}
@media (max-width: 650px) {
  .memory-summary,
  .memory-filters {
    grid-template-columns: 1fr;
  }
}
</style>
