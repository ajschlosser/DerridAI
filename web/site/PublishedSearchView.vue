<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD
-->

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import UiButton from "../src/components/ui/UiButton.vue";
import UiInput from "../src/components/ui/UiInput.vue";
import UiSelect from "../src/components/ui/UiSelect.vue";
import PublishedIndexStatus from "./PublishedIndexStatus.vue";
import PublishedMethodStrip from "./PublishedMethodStrip.vue";
import { usePublishedSite } from "./siteContext";
import { highlightSegments, snippetText } from "./textHighlight";

const site = usePublishedSite();
const query = ref("");
const mode = ref<"keyword" | "semantic" | "hybrid">(
  site.capabilities.value?.publicationVectors?.available ||
    site.capabilities.value?.localIndex?.complete
    ? "semantic"
    : "keyword",
);
const work = ref(site.searchWork.value);
site.searchWork.value = "";
const field = ref("");
const filterValue = ref("");
const running = ref(false);
const status = ref(
  site.t("site.runtime.search_prompt", {
    count: site.recordCount.value.toLocaleString(site.locale.value),
  }),
);
const statusTone = ref<"" | "warning" | "error">("");
const results = ref<any[]>([]);
const searchedQuery = ref("");
const methods = ref({
  text: mode.value !== "semantic",
  vector: mode.value !== "keyword",
  llm: false,
});

const localIndexVisible = computed(
  () =>
    Boolean(site.capabilities.value?.localIndex) &&
    !Boolean(site.capabilities.value?.localIndex?.usesPublishedVectors),
);
const resultCountText = computed(() =>
  site.t("site.runtime.results_count", { count: results.value.length }),
);

watch(mode, (value) => {
  methods.value = {
    text: value !== "semantic",
    vector: value !== "keyword",
    llm: false,
  };
});

watch(
  () => Boolean(site.capabilities.value?.localIndex?.complete),
  (complete) => {
    if (complete) mode.value = "semantic";
    else if (!site.capabilities.value?.publicationVectors?.available && mode.value !== "keyword") {
      mode.value = "keyword";
    }
  },
);

function clearFilters() {
  work.value = "";
  field.value = "";
  filterValue.value = "";
}

async function runSearch() {
  if (!site.client.value) return;
  running.value = true;
  statusTone.value = "";
  status.value =
    mode.value === "keyword"
      ? site.t("site.runtime.activity_text_search")
      : mode.value === "semantic"
        ? site.t("site.runtime.activity_vector_search")
        : site.t("site.runtime.activity_hybrid_search");
  results.value = [];
  searchedQuery.value = "";

  const stopProgress = site.subscribeProgress((message) => {
    status.value = message;
  });

  try {
    const filters: Record<string, unknown> = {};
    if (work.value) filters.work = work.value;
    if (field.value && filterValue.value) filters[field.value] = filterValue.value;
    const response = await site.client.value.search({
      query: query.value,
      mode: mode.value,
      filters,
      limit: 50,
    });
    methods.value = {
      text: response.modeUsed !== "semantic",
      vector: response.modeUsed !== "keyword",
      llm: false,
    };
    const warning = site.warningText(response.warnings);
    statusTone.value = warning ? "warning" : "";
    status.value = warning
      ? site.t("site.runtime.results_with_warning", {
          count: response.results.length,
          warning,
        })
      : site.t("site.runtime.results_count", { count: response.results.length });
    results.value = response.results;
    searchedQuery.value = mode.value === "keyword" ? query.value : "";
  } catch (error) {
    statusTone.value = "error";
    status.value = site.t("site.runtime.search_failed", {
      error: error instanceof Error ? error.message : String(error),
    });
  } finally {
    stopProgress();
    running.value = false;
  }
}

function snippet(record: any): string {
  return snippetText(
    String(record.text || ""),
    searchedQuery.value,
    site.locale.value,
  );
}

function segments(record: any) {
  return highlightSegments(snippet(record), searchedQuery.value, site.locale.value);
}
</script>

<template>
  <div class="stack">
    <section class="search-surface" aria-labelledby="search-heading">
      <div class="search-head">
        <h2 id="search-heading">{{ site.t("site.runtime.search") }}</h2>
        <p>{{ site.t("site.runtime.search_intro") }}</p>
      </div>

      <form
        class="search-form"
        role="search"
        :aria-label="site.t('site.runtime.search')"
        @submit.prevent="runSearch"
      >
        <div class="search-row" data-tour="search">
          <UiInput
            v-model="query"
            class="control"
            type="search"
            autocomplete="off"
            :placeholder="site.t('site.runtime.search_placeholder')"
            :aria-label="site.t('site.runtime.search_query_label')"
          />
          <UiButton
            variant="primary"
            type="submit"
            :label="site.t('site.runtime.search')"
            :disabled="running"
          />
        </div>

        <div class="search-toolbar">
          <label class="search-mode-field">
            <span>{{ site.t("site.runtime.search_mode") }}</span>
            <UiSelect
              v-model="mode"
              class="control"
              :aria-label="site.t('site.runtime.search_mode')"
            >
              <option value="keyword">{{ site.t("site.runtime.keyword") }}</option>
              <option value="semantic" :disabled="!site.capabilities.value?.provider?.embeddings">
                {{ site.t("site.runtime.semantic") }}
              </option>
              <option value="hybrid" :disabled="!site.capabilities.value?.provider?.embeddings">
                {{ site.t("site.runtime.hybrid") }}
              </option>
            </UiSelect>
          </label>
          <PublishedMethodStrip
            :text="methods.text"
            :vector="methods.vector"
            :llm="methods.llm"
          />
        </div>

        <details class="search-refine" data-tour="filters">
          <summary>{{ site.t("site.runtime.refine_search") }}</summary>
          <div class="filters">
            <label class="field">
              <span>{{ site.t("site.runtime.work_filter") }}</span>
              <UiSelect
                v-model="work"
                class="control"
                :aria-label="site.t('site.runtime.work_filter')"
              >
                <option value="">{{ site.t("site.runtime.all_works") }}</option>
                <option
                  v-for="item in site.publication.works || []"
                  :key="item.work"
                  :value="item.work"
                >
                  {{ item.work }}
                </option>
              </UiSelect>
            </label>
            <label class="field">
              <span>{{ site.t("site.runtime.field_filter") }}</span>
              <UiSelect
                v-model="field"
                class="control"
                :aria-label="site.t('site.runtime.field_filter')"
              >
                <option value="">{{ site.t("site.runtime.any_field") }}</option>
                <option v-for="key in site.filterFields()" :key="key" :value="key">
                  {{ key.replaceAll("_", " ") }}
                </option>
              </UiSelect>
            </label>
            <label class="field">
              <span>{{ site.t("site.runtime.filter_value") }}</span>
              <UiInput
                v-model="filterValue"
                class="control"
                :placeholder="site.t('site.runtime.filter_value')"
                :aria-label="site.t('site.runtime.filter_value')"
              />
            </label>
            <div class="field">
              <span class="sr-only">{{ site.t("site.runtime.clear_filters") }}</span>
              <UiButton :label="site.t('site.runtime.clear_filters')" @click="clearFilters" />
            </div>
          </div>
        </details>
      </form>

      <div
        class="status"
        :class="statusTone"
        role="status"
        aria-live="polite"
      >
        {{ status }}
      </div>

      <PublishedIndexStatus
        v-if="localIndexVisible"
        initial-build-label-key="site.runtime.index_build_browser"
      />
    </section>

    <div v-if="results.length || searchedQuery" class="results-heading">
      <h2>{{ site.t("site.runtime.search_results") }}</h2>
      <span class="meta">{{ resultCountText }}</span>
    </div>

    <div class="search-results" aria-live="polite">
      <div v-if="searchedQuery && !results.length" class="empty">
        {{ site.t("site.runtime.no_results") }}
      </div>
      <article v-for="item in results" :key="item.record.record_id" class="result card">
        <div class="result-head">
          <div>
            <strong>{{ item.record.work || item.record.record_id }}</strong>
            <div class="meta">{{ site.client.value?.citations.format(item.record).plain }}</div>
          </div>
        </div>
        <div class="snippet">
          <template v-for="(segment, index) in segments(item.record)" :key="index">
            <mark v-if="segment.highlighted">{{ segment.text }}</mark>
            <template v-else>{{ segment.text }}</template>
          </template>
        </div>
        <UiButton
          :label="site.t('site.runtime.view_record')"
          @click="site.openRecord(item.record, searchedQuery)"
        />
      </article>
    </div>
  </div>
</template>
