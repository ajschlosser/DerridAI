<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  metadataMemoryApi,
  type MetadataMemoryEntry,
  type MetadataMemoryPayload,
} from "../api/metadataMemory";
import UiButton from "../components/ui/UiButton.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import { useI18nStore } from "../stores/i18n";

const i18n = useI18nStore();
const pageSize = 50;
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

const pageStart = computed(() => (payload.value.total ? offset.value + 1 : 0));
const pageEnd = computed(() => Math.min(offset.value + pageSize, payload.value.total));
const canPrevious = computed(() => offset.value > 0 && !loading.value);
const canNext = computed(() => offset.value + pageSize < payload.value.total && !loading.value);

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function kindLabel(value: string): string {
  if (value === "positive") return i18n.t("metadata_memory.kind_positive");
  if (value === "correction") return i18n.t("metadata_memory.kind_correction");
  return value;
}

function sourceLabel(item: MetadataMemoryEntry): string {
  const revision = item.record_revision ? ` · r${item.record_revision}` : "";
  return `${item.record_id}${revision}`;
}

function pageLabel(item: MetadataMemoryEntry): string {
  const start = item.page_start;
  const end = item.page_end;
  if (start === undefined || start === null || start === "") return "";
  return end !== undefined && end !== null && end !== "" && String(end) !== String(start)
    ? `${start}–${end}`
    : String(start);
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    payload.value = await metadataMemoryApi.list({
      limit: pageSize,
      offset: offset.value,
      field: field.value,
      kind: kind.value,
      build_id: buildId.value,
      language: language.value,
      q: query.value.trim(),
    });
    if (!payload.value.available && payload.value.error) error.value = payload.value.error;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

function applyFilters() {
  offset.value = 0;
  void load();
}

function clearFilters() {
  query.value = "";
  field.value = "";
  kind.value = "";
  buildId.value = "";
  language.value = "";
  offset.value = 0;
  void load();
}

function previousPage() {
  if (!canPrevious.value) return;
  offset.value = Math.max(0, offset.value - pageSize);
  void load();
}

function nextPage() {
  if (!canNext.value) return;
  offset.value += pageSize;
  void load();
}

onMounted(() => void load());
</script>

<template>
  <main class="vue-native-page metadata-memory-page" aria-labelledby="metadata-memory-title">
    <UiPageHeader
      :kicker="i18n.t('section.system')"
      :title="i18n.t('metadata_memory.title')"
      title-id="metadata-memory-title"
      :description="i18n.t('metadata_memory.help')"
    >
      <template #actions>
        <UiButton
          :label="i18n.t('metadata_memory.refresh')"
          :disabled="loading"
          @click="load"
        />
      </template>
    </UiPageHeader>

    <p class="memory-contract">
      <strong>{{ i18n.t("metadata_memory.authority_title") }}</strong>
      {{ i18n.t("metadata_memory.authority_help") }}
    </p>

    <section class="memory-summary" :aria-label="i18n.t('metadata_memory.summary')">
      <article class="card">
        <span>{{ i18n.t("metadata_memory.entries") }}</span>
        <strong>{{ payload.summary.entries.toLocaleString(i18n.locale) }}</strong>
      </article>
      <article class="card">
        <span>{{ i18n.t("metadata_memory.evidence_bound") }}</span>
        <strong>{{ payload.summary.evidence_bound.toLocaleString(i18n.locale) }}</strong>
      </article>
      <article class="card">
        <span>{{ i18n.t("metadata_memory.corrections") }}</span>
        <strong>{{ payload.summary.corrections.toLocaleString(i18n.locale) }}</strong>
      </article>
      <article class="card">
        <span>{{ i18n.t("metadata_memory.fields") }}</span>
        <strong>{{ payload.summary.fields.toLocaleString(i18n.locale) }}</strong>
      </article>
    </section>

    <p v-if="error" class="info error" role="alert">
      {{ i18n.t("metadata_memory.unavailable") }}: {{ error }}
    </p>

    <form class="card memory-filters" @submit.prevent="applyFilters">
      <label>
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
      <div class="filter-actions">
        <UiButton variant="primary" :label="i18n.t('metadata_memory.apply_filters')" type="submit" />
        <UiButton :label="i18n.t('metadata_memory.clear_filters')" type="button" @click="clearFilters" />
      </div>
    </form>

    <section class="card memory-table-card" aria-labelledby="metadata-memory-table-title">
      <header class="table-heading">
        <div>
          <h2 id="metadata-memory-table-title">{{ i18n.t("metadata_memory.precedents") }}</h2>
          <p>
            {{
              i18n.tf("metadata_memory.showing", {
                start: pageStart,
                end: pageEnd,
                total: payload.total,
              })
            }}
          </p>
        </div>
        <span v-if="loading" role="status">{{ i18n.t("metadata_memory.loading") }}</span>
      </header>

      <div class="tablewrap">
        <table>
          <thead>
            <tr>
              <th>{{ i18n.t("metadata_memory.field_value") }}</th>
              <th>{{ i18n.t("metadata_memory.authority") }}</th>
              <th>{{ i18n.t("metadata_memory.source") }}</th>
              <th>{{ i18n.t("metadata_memory.scope") }}</th>
              <th>{{ i18n.t("metadata_memory.evidence") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in payload.items" :key="item.id">
              <td>
                <b>{{ item.field }}</b>
                <pre class="memory-value">{{ displayValue(item.value) }}</pre>
                <p v-if="item.kind === 'correction' && item.rejected_value !== undefined" class="negative-precedent">
                  <span>{{ i18n.t("metadata_memory.rejected_value") }}</span>
                  {{ displayValue(item.rejected_value) }}
                </p>
              </td>
              <td>
                <div class="badge-row">
                  <span class="memory-badge">{{ kindLabel(item.kind) }}</span>
                  <span v-if="item.evidence_bound" class="memory-badge">
                    {{ i18n.t("metadata_memory.bound") }}
                  </span>
                </div>
                <small>{{ item.authority || "—" }}</small>
                <small v-if="item.review_method">{{ item.review_method }}</small>
              </td>
              <td>
                <b>{{ sourceLabel(item) }}</b>
                <small v-if="item.source_document_id">{{ item.source_document_id }}</small>
                <small v-if="pageLabel(item)">
                  {{ i18n.t("metadata_memory.page") }} {{ pageLabel(item) }}
                </small>
                <small v-if="item.source_current === false" class="stale-source">
                  {{ i18n.t("metadata_memory.source_stale") }}
                </small>
                <small v-if="item.evidence_current === false" class="stale-source">
                  {{ i18n.t("metadata_memory.evidence_stale") }}
                </small>
              </td>
              <td>
                <small v-if="item.build_id">{{ item.build_id }}</small>
                <small v-if="item.schema_id || item.schema_version">
                  {{ item.schema_id || "—" }}<template v-if="item.schema_version"> · {{ item.schema_version }}</template>
                </small>
                <small v-if="item.language || item.region_type">
                  {{ item.language || "—" }}<template v-if="item.region_type"> · {{ item.region_type }}</template>
                </small>
              </td>
              <td class="evidence-cell">
                <p v-if="item.evidence_text" class="evidence-text">{{ item.evidence_text }}</p>
                <p v-else-if="item.evidence_bound" class="note">
                  {{ i18n.t("metadata_memory.evidence_unresolved") }}
                </p>
                <p v-else class="note">{{ i18n.t("metadata_memory.context_only") }}</p>
                <small v-if="item.evidence_block_ids.length">
                  {{ i18n.t("metadata_memory.blocks") }}: {{ item.evidence_block_ids.join(", ") }}
                </small>
                <details v-if="item.context_text">
                  <summary>{{ i18n.t("metadata_memory.indexed_context") }}</summary>
                  <p>{{ item.context_text }}</p>
                </details>
              </td>
            </tr>
            <tr v-if="!loading && !payload.items.length">
              <td colspan="5" class="empty-cell">{{ i18n.t("metadata_memory.empty") }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer class="pagination">
        <UiButton
          :label="i18n.t('common.previous')"
          :disabled="!canPrevious"
          @click="previousPage"
        />
        <span>{{ pageStart }}–{{ pageEnd }} / {{ payload.total }}</span>
        <UiButton :label="i18n.t('common.next')" :disabled="!canNext" @click="nextPage" />
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
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
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
.memory-summary span {
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 700;
}
.memory-summary strong {
  font-size: 1.55rem;
}
.memory-filters {
  display: grid;
  grid-template-columns: minmax(220px, 1.5fr) repeat(4, minmax(130px, 1fr));
  gap: 10px;
  align-items: end;
  padding: 14px;
}
.memory-filters label {
  display: grid;
  gap: 5px;
  min-width: 0;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
}
.filter-actions {
  display: flex;
  gap: 8px;
  grid-column: 1 / -1;
}
.memory-table-card {
  min-width: 0;
  padding: 0;
  overflow: hidden;
}
.table-heading,
.pagination {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 14px;
}
.table-heading h2 {
  margin: 0;
  font-size: 1rem;
}
.table-heading p {
  margin: 4px 0 0;
  color: var(--muted);
}
.memory-table-card th {
  white-space: nowrap;
}
.memory-table-card td {
  min-width: 150px;
  vertical-align: top;
}
.memory-table-card td:first-child {
  min-width: 190px;
}
.evidence-cell {
  min-width: min(34rem, 42vw) !important;
}
.memory-value {
  margin: 6px 0 0;
  max-width: 28rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: inherit;
  font-size: 0.82rem;
}
.negative-precedent {
  margin: 8px 0 0;
  font-size: 0.8rem;
}
.negative-precedent span {
  display: block;
  color: var(--muted);
  font-weight: 700;
}
.badge-row {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.memory-badge {
  display: inline-flex;
  padding: 3px 6px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--soft);
  font-size: 0.75rem;
  font-weight: 700;
}
.memory-table-card small {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  overflow-wrap: anywhere;
}
.stale-source {
  font-weight: 700;
}
.evidence-text {
  margin: 0 0 8px;
  white-space: pre-wrap;
  line-height: 1.5;
}
.evidence-cell details {
  margin-top: 8px;
}
.evidence-cell details p {
  max-height: 14rem;
  overflow: auto;
  white-space: pre-wrap;
  line-height: 1.5;
}
.empty-cell {
  padding: 28px !important;
  text-align: center;
  color: var(--muted);
}
.pagination {
  border-top: 1px solid var(--line);
}
@media (max-width: 1000px) {
  .memory-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .memory-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 650px) {
  .memory-summary,
  .memory-filters {
    grid-template-columns: 1fr;
  }
  .table-heading,
  .pagination {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
