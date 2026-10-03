<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { MetadataMemoryListFilters, MetadataMemoryPayload } from "../api/metadataMemory";
import MetadataMemoryFilters from "../components/metadata-memory/MetadataMemoryFilters.vue";
import MetadataMemoryRelations from "../components/metadata-memory/MetadataMemoryRelations.vue";
import MetadataMemoryTable from "../components/metadata-memory/MetadataMemoryTable.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiLoadingState from "../components/ui/UiLoadingState.vue";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import UiTooltip from "../components/ui/UiTooltip.vue";
import { useMetadataMemoryData } from "../composables/useMetadataMemoryData";
import { useI18nStore } from "../stores/i18n";

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const pageSize = 50;
const searchDebounceMs = 300;
const offset = ref(Math.max(0, Number(route.query.offset) || 0));
const query = ref(String(route.query.q || ""));
const field = ref(String(route.query.field || ""));
const kind = ref(String(route.query.kind || ""));
const buildId = ref(String(route.query.build || ""));
const language = ref(String(route.query.language || ""));
let searchTimer: number | undefined;
let applyingRouteState = false;

function snapshot(): MetadataMemoryListFilters {
  return {
    limit: pageSize,
    offset: offset.value,
    field: field.value,
    kind: kind.value,
    build_id: buildId.value,
    language: language.value,
    q: query.value.trim(),
  };
}

const applied = ref<MetadataMemoryListFilters>(snapshot());
const { payload, loading, ready, waiting, refreshing, readError, clearForNewQuery, refetch } =
  useMetadataMemoryData(applied);

const emptyFacets: MetadataMemoryPayload["facets"] = {
  fields: [],
  kinds: [],
  languages: [],
  builds: [],
};
const facets = computed(() => payload.value?.facets ?? emptyFacets);
const total = computed(() => payload.value?.total ?? 0);
const pageStart = computed(() => (total.value ? offset.value + 1 : 0));
const pageEnd = computed(() => Math.min(offset.value + pageSize, total.value));
const canPrevious = computed(() => ready.value && offset.value > 0 && !loading.value);
const canNext = computed(
  () => ready.value && offset.value + pageSize < total.value && !loading.value,
);
const hasFilters = computed(() =>
  Boolean(
    query.value.trim() ||
      field.value ||
      kind.value ||
      buildId.value ||
      language.value,
  ),
);
const stats = computed(() => {
  const summary = payload.value?.summary;
  if (!summary) return [];
  return [
    { key: "entries", value: summary.entries },
    { key: "evidence_bound", value: summary.evidence_bound },
    { key: "corrections", value: summary.corrections },
    { key: "fields", value: summary.fields },
  ];
});

async function load() {
  const next = snapshot();
  if (JSON.stringify(next) === JSON.stringify(applied.value)) {
    await refetch();
    return;
  }
  clearForNewQuery();
  applied.value = next;
}

function syncRoute(nextOffset = offset.value, push = false) {
  const location = {
    name: "metadatamemory",
    query: {
      ...route.query,
      q: query.value.trim() || undefined,
      field: field.value || undefined,
      kind: kind.value || undefined,
      build: buildId.value || undefined,
      language: language.value || undefined,
      offset: nextOffset > 0 ? String(nextOffset) : undefined,
    },
  };
  if (push) void router.push(location);
  else void router.replace(location);
}

function applyFilters() {
  window.clearTimeout(searchTimer);
  offset.value = 0;
  syncRoute(0);
  void load();
}

function clearFilters() {
  window.clearTimeout(searchTimer);
  applyingRouteState = true;
  query.value = "";
  field.value = "";
  kind.value = "";
  buildId.value = "";
  language.value = "";
  void nextTick(() => {
    applyingRouteState = false;
    applyFilters();
  });
}

function goTo(next: number) {
  offset.value = next;
  syncRoute(next, true);
  void load();
}

watch([field, kind, buildId, language], () => {
  if (!applyingRouteState) applyFilters();
});
watch(query, () => {
  if (applyingRouteState) return;
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(applyFilters, searchDebounceMs);
});

// A bookmarked page can outlive the result set it pointed into.  Correct the offset instead of
// rendering a successful-but-empty slice when newer memory contains fewer rows.
watch(payload, (next) => {
  if (!next) return;
  const lastOffset = next.total > 0 ? Math.floor((next.total - 1) / pageSize) * pageSize : 0;
  if (offset.value <= lastOffset) return;
  offset.value = lastOffset;
  syncRoute(lastOffset);
  clearForNewQuery();
  applied.value = snapshot();
});

watch(
  () => [
    route.query.q,
    route.query.field,
    route.query.kind,
    route.query.build,
    route.query.language,
    route.query.offset,
  ],
  ([q, nextField, nextKind, nextBuild, nextLanguage, nextOffset]) => {
    const state = {
      q: String(q || ""),
      field: String(nextField || ""),
      kind: String(nextKind || ""),
      build: String(nextBuild || ""),
      language: String(nextLanguage || ""),
      offset: Math.max(0, Number(nextOffset) || 0),
    };
    if (
      state.q === query.value &&
      state.field === field.value &&
      state.kind === kind.value &&
      state.build === buildId.value &&
      state.language === language.value &&
      state.offset === offset.value
    )
      return;
    applyingRouteState = true;
    query.value = state.q;
    field.value = state.field;
    kind.value = state.kind;
    buildId.value = state.build;
    language.value = state.language;
    offset.value = state.offset;
    window.clearTimeout(searchTimer);
    void nextTick(() => {
      applyingRouteState = false;
    });
    void load();
  },
);

onBeforeUnmount(() => window.clearTimeout(searchTimer));
</script>

<template>
  <main class="vue-native-page metadata-memory-page" aria-labelledby="metadata-memory-title">
    <UiPageHeader
      :kicker="i18n.t('section.ai_automation')"
      :title="i18n.t('metadata_memory.title')"
      title-id="metadata-memory-title"
      :description="i18n.t('metadata_memory.help')"
    />

    <p class="memory-contract">
      <strong>{{ i18n.t("metadata_memory.authority_title") }}</strong>
      {{ i18n.t("metadata_memory.authority_help") }}
    </p>

    <MetadataMemoryRelations />

    <section
      v-if="ready"
      class="memory-summary"
      :aria-label="i18n.t('metadata_memory.summary')"
    >
      <article v-for="stat in stats" :key="stat.key" class="card">
        <span class="stat-label">
          {{ i18n.t(`metadata_memory.${stat.key}`) }}
          <UiTooltip :text="i18n.t(`metadata_memory.${stat.key}_help`)" placement="bottom" />
        </span>
        <strong>{{ stat.value.toLocaleString(i18n.locale) }}</strong>
      </article>
    </section>
    <UiLoadingState
      v-else-if="waiting"
      class="memory-summary-loading"
      variant="skeleton"
      :skeleton-count="4"
      :label="i18n.t('metadata_memory.loading')"
    />

    <div v-if="readError" class="info error memory-read-error" role="alert">
      <p>
        {{
          i18n.tf(ready ? "metadata_memory.refresh_failed" : "metadata_memory.read_failed", {
            message: readError,
          })
        }}
      </p>
      <UiButton
        :label="i18n.t('ui.retry')"
        :disabled="loading"
        @click="refetch"
      />
    </div>

    <section
      class="card memory-table-card"
      aria-labelledby="metadata-memory-table-title"
      :aria-busy="waiting || refreshing"
    >
      <header class="table-heading">
        <div>
          <h2 id="metadata-memory-table-title">{{ i18n.t("metadata_memory.precedents") }}</h2>
          <p role="status" aria-live="polite">
            {{
              waiting
                ? i18n.t("metadata_memory.loading")
                : refreshing
                  ? i18n.t("metadata_memory.updating")
                  : ready
                    ? i18n.tf("metadata_memory.showing", {
                        start: pageStart,
                        end: pageEnd,
                        total,
                      })
                    : i18n.t("metadata_memory.unavailable")
            }}
          </p>
        </div>
      </header>

      <MetadataMemoryFilters
        v-model:query="query"
        v-model:field="field"
        v-model:kind="kind"
        v-model:build-id="buildId"
        v-model:language="language"
        :facets="facets"
        @apply="applyFilters"
        @clear="clearFilters"
      />

      <UiLoadingState
        v-if="waiting"
        class="memory-table-loading"
        variant="skeleton"
        :label="i18n.t('metadata_memory.loading')"
      />

      <MetadataMemoryTable
        v-else-if="ready && payload"
        :items="payload.items"
        :loading="refreshing"
        :filtered="hasFilters"
      />

      <footer v-if="ready" class="pagination" :aria-label="i18n.t('metadata_memory.pagination')">
        <UiButton
          :label="i18n.t('common.previous')"
          :disabled="!canPrevious"
          @click="goTo(Math.max(0, offset - pageSize))"
        />
        <span>{{ pageStart }}–{{ pageEnd }} / {{ total }}</span>
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
.memory-summary-loading,
.memory-table-loading {
  padding: 14px;
}
.memory-read-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.memory-read-error p {
  margin: 0;
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
.pagination {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
}
@media (max-width: 1000px) {
  .memory-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 650px) {
  .memory-summary {
    grid-template-columns: 1fr;
  }
  .memory-read-error {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
