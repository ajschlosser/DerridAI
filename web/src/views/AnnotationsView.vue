<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import AnnotationFeedItem from "../components/annotations/AnnotationFeedItem.vue";
import { useAnnotationsWorkspace } from "../composables/useAnnotationsWorkspace";
import { useI18nStore } from "../stores/i18n";
import UiPageHeader from "../components/ui/UiPageHeader.vue";

const i18n = useI18nStore();
const annotations = useAnnotationsWorkspace();
const { snapshot, loading, error, removing } = annotations;
const emptyMessage = computed(() =>
  snapshot.value?.total
    ? i18n.t("annotations.empty")
    : i18n.t("annotations.none_yet"),
);

watch(
  () => i18n.locale,
  () => void annotations.load(true),
);
onMounted(() => void annotations.load());
</script>

<template>
  <main class="annotations-page" aria-labelledby="annotations-page-title" :aria-busy="loading">
    <UiPageHeader
      :kicker="i18n.t('section.corpus')"
      :title="i18n.t('nav.annotations')"
      title-id="annotations-page-title"
      :description="
        i18n.t('annotations.page_help')
      "
    />

    <section v-if="loading" class="card annotations-state" role="status">
      {{ i18n.t("ui.loading") }}
    </section>
    <section v-else-if="error" class="card annotations-state" role="alert">
      <strong>{{ i18n.t("annotations.open_failed") }}</strong>
      <p>{{ error }}</p>
      <button type="button" class="btn" @click="annotations.load(true)">
        {{ i18n.t("ui.retry") }}
      </button>
    </section>
    <template v-else-if="snapshot">
      <section class="card annotations-index-card">
        <div class="annotations-toolbar">
          <label class="search">
            <span class="sr-only">{{
              i18n.t("annotations.search_placeholder")
            }}</span>
            <input
              type="search"
              :value="snapshot.query"
              :placeholder="
                i18n.t('annotations.search_placeholder')
              "
              @input="annotations.setQuery(($event.target as HTMLInputElement).value)"
            />
          </label>
          <div class="view-tabs" role="tablist">
            <button
              type="button"
              class="view-tab"
              :class="{ active: snapshot.view === 'works' }"
              role="tab"
              :aria-selected="snapshot.view === 'works'"
              @click="annotations.setView('works')"
            >
              {{ i18n.t("annotations.by_work") }}
            </button>
            <button
              type="button"
              class="view-tab"
              :class="{ active: snapshot.view === 'recent' }"
              role="tab"
              :aria-selected="snapshot.view === 'recent'"
              @click="annotations.setView('recent')"
            >
              {{ i18n.t("annotations.recent") }}
            </button>
          </div>
          <span class="note"
            >{{
              i18n.tf("annotations.annotation_count", {
                count: snapshot.total.toLocaleString(i18n.locale),
              })
            }}
            · {{ snapshot.groups.length.toLocaleString(i18n.locale) }}
            {{ i18n.t("dynamic.works") }}</span
          >
        </div>
      </section>

      <section v-if="snapshot.view === 'recent'" class="card annotations-recent-card">
        <div class="cardhead">
          <div>
            <b>{{ i18n.t("annotations.recent_annotations") }}</b>
            <div class="note">
              {{ i18n.t("annotations.recent_help") }}
            </div>
          </div>
        </div>
        <div class="annotation-feed">
          <AnnotationFeedItem
            v-for="annotation in snapshot.annotations"
            :key="annotation.id"
            :annotation="annotation"
            :removing="removing === annotation.id"
            @open="annotations.openRecord"
            @remove="annotations.remove"
          />
          <div v-if="!snapshot.annotations.length" class="llm-empty">{{ emptyMessage }}</div>
        </div>
      </section>

      <section v-else class="annotation-work-groups">
        <details
          v-for="group in snapshot.groups"
          :key="group.work"
          class="card annotation-work-group"
          open
        >
          <summary>
            <span
              ><b>{{ group.work }}</b
              ><small
                >{{
                  i18n.tf("annotations.annotation_count", {
                    count: group.annotations.length.toLocaleString(i18n.locale),
                  })
                }}
                · {{ group.records.toLocaleString(i18n.locale) }}
                {{ i18n.t("dynamic.records") }}</small>
              ></span
            ><button
              type="button"
              class="btn tiny"
              @click.prevent="annotations.openWork(group.work)"
            >
              {{ i18n.t("works.open_overview") }}
            </button>
          </summary>
          <div class="annotation-feed">
            <AnnotationFeedItem
              v-for="annotation in group.annotations"
              :key="annotation.id"
              :annotation="annotation"
              :removing="removing === annotation.id"
              @open="annotations.openRecord"
              @remove="annotations.remove"
            />
          </div>
        </details>
        <div v-if="!snapshot.groups.length" class="card llm-empty">{{ emptyMessage }}</div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.annotations-page {
  display: grid;
  gap: var(--page-gap);
}
.annotations-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.annotations-toolbar .search {
  flex: 1 1 280px;
}
.annotations-toolbar input {
  width: 100%;
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 0 11px;
  background: var(--card);
  color: var(--text-2);
}
.view-tabs {
  display: flex;
  gap: 4px;
}
.view-tab {
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  padding: 0 10px;
  color: var(--text-2);
  font-weight: 800;
  cursor: pointer;
}
.view-tab.active {
  border-color: var(--ui-accent, #3c8d62);
  background: var(--soft);
}
.note,
.annotation-feed-meta,
.annotation-feed-item small {
  color: var(--muted);
  font-size: 0.8125rem;
}
.annotations-state {
  padding: 28px;
  text-align: center;
}
.annotations-state p {
  color: var(--muted);
}
.annotation-work-groups,
.annotation-feed {
  display: grid;
  gap: 10px;
}
.annotation-work-group {
  overflow: hidden;
}
.annotation-work-group summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  list-style: none;
}
.annotation-work-group summary > span {
  display: grid;
  gap: 3px;
}
.annotation-work-group summary small {
  color: var(--muted);
  font-size: 0.8125rem;
}
.annotation-feed {
  padding: 0 12px 12px;
}
.annotation-feed-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  padding: 11px;
}
.annotation-open-record {
  width: 30px;
  height: 30px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--card);
  color: var(--text-2);
  cursor: pointer;
}
.annotation-feed-copy {
  display: grid;
  gap: 7px;
  min-width: 0;
}
.annotation-feed-meta {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}
.annotation-feed-meta b {
  color: var(--text-2);
}
.annotation-feed-item blockquote {
  margin: 0;
  padding: 8px 10px;
  border-left: 3px solid var(--ui-accent, #3c8d62);
  background: var(--soft);
  color: var(--text-2);
  font:
    13px/1.55 Georgia,
    "Times New Roman",
    serif;
}
.annotation-feed-item p {
  margin: 0;
  color: var(--text-2);
  line-height: 1.5;
}
.annotation-tags {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}
.chip {
  border-radius: 999px;
  background: var(--soft);
  padding: 3px 7px;
  color: var(--text-2);
  font-size: 0.8125rem;
}
.btn {
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  padding: 0 10px;
  color: var(--text-2);
  font-weight: 800;
  cursor: pointer;
}
.btn.tiny {
  min-height: 30px;
  font-size: 0.8125rem;
}
.btn.danger {
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.llm-empty {
  padding: 24px;
  color: var(--muted);
  text-align: center;
}
button:focus-visible,
input:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 2px;
}
@media (max-width: 640px) {
  .annotation-feed-item {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .annotation-feed-item > .btn {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
