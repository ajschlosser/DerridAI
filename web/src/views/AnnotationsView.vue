<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppIcon from "../components/AppIcon.vue";
import { useAnnotations } from "../composables/useAnnotations";
import { useI18nStore } from "../stores/i18n";

const i18n = useI18nStore();
const route = useRoute();
const router = useRouter();
const { annotations, loading, load, remove } = useAnnotations();
const search = ref(String(route.query.q || ""));
const view = ref(String(route.query.view || "works"));
const error = ref("");
const filtered = computed(() => {
  const query = search.value.trim().toLocaleLowerCase();
  return annotations.value.filter(
    (item) =>
      !query ||
      [item.work, item.record_id, item.quote, item.note, ...(item.tags || [])].some((value) =>
        String(value || "")
          .toLocaleLowerCase()
          .includes(query),
      ),
  );
});
const grouped = computed(() => {
  const groups = new Map<string, typeof filtered.value>();
  for (const item of filtered.value) {
    const name = item.work || i18n.t("annotations.untitled_work", "Untitled work");
    groups.set(name, [...(groups.get(name) || []), item]);
  }
  return [...groups.entries()];
});
function syncUrl() {
  void router.replace({
    query: {
      ...route.query,
      q: search.value || undefined,
      view: view.value === "works" ? undefined : view.value,
    },
  });
}
async function deleteAnnotation(id: string) {
  try {
    await remove(id);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  }
}
function openRecord(id: string) {
  void router.push({ name: "record", query: { record: id } });
}
onMounted(async () => {
  try {
    await load(String(route.query.store || ""));
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : String(cause);
  }
});
</script>

<template>
  <main class="annotations-page" aria-labelledby="annotations-title">
    <header class="page-heading">
      <div>
        <p>{{ i18n.t("section.corpus", "Corpus") }}</p>
        <h1 id="annotations-title">{{ i18n.t("nav.annotations", "Annotations") }}</h1>
        <span>{{
          i18n.t("annotations.page_help", "Review notes and evidence attached to corpus records.")
        }}</span>
      </div>
    </header>
    <p v-if="error" class="info error" role="alert">{{ error }}</p>
    <section class="toolbar annotations-toolbar">
      <label class="search"
        ><span class="sr-only">{{ i18n.t("annotations.search", "Search annotations") }}</span
        ><input
          v-model="search"
          type="search"
          :placeholder="i18n.t('annotations.search', 'Search annotations')"
          @input="syncUrl"
      /></label>
      <div class="tools">
        <button
          type="button"
          class="btn small"
          :class="{ primary: view === 'works' }"
          @click="
            view = 'works';
            syncUrl;
          "
        >
          {{ i18n.t("annotations.by_work", "By work") }}
        </button>
        <button
          type="button"
          class="btn small"
          :class="{ primary: view === 'records' }"
          @click="
            view = 'records';
            syncUrl;
          "
        >
          {{ i18n.t("annotations.by_record", "By record") }}
        </button>
        <span class="note"
          >{{ filtered.length }} {{ i18n.t("dynamic.annotations", "annotations") }}</span
        >
      </div>
    </section>
    <div v-if="loading" class="page-loading" role="status">
      {{ i18n.t("annotations.loading", "Loading annotations") }}
    </div>
    <section v-else-if="!filtered.length" class="card annotation-empty-state">
      <AppIcon name="record" aria-hidden="true" /><strong>{{
        i18n.t("annotations.none", "No annotations found")
      }}</strong>
    </section>
    <section v-else class="annotation-groups">
      <template v-if="view === 'works'">
        <article v-for="[work, items] in grouped" :key="work" class="card annotation-group">
          <h2>{{ work }}</h2>
          <div class="annotation-list">
            <article v-for="annotation in items" :key="annotation.id" class="annotation-card">
              <blockquote v-if="annotation.quote">{{ annotation.quote }}</blockquote>
              <p v-if="annotation.note">{{ annotation.note }}</p>
              <div class="annotation-meta">
                <span>{{ annotation.author || annotation.initiated_by }}</span
                ><button type="button" @click="openRecord(annotation.record_id)">
                  {{ i18n.t("annotations.open_record", "Open record") }}</button
                ><button
                  v-if="annotation.removable !== false"
                  type="button"
                  @click="deleteAnnotation(annotation.id)"
                >
                  {{ i18n.t("ui.remove", "Remove") }}
                </button>
              </div>
            </article>
          </div>
        </article>
      </template>
      <div v-else class="annotation-list">
        <article v-for="annotation in filtered" :key="annotation.id" class="card annotation-card">
          <strong>{{ annotation.work || annotation.record_id }}</strong>
          <blockquote v-if="annotation.quote">{{ annotation.quote }}</blockquote>
          <p v-if="annotation.note">{{ annotation.note }}</p>
          <div class="annotation-meta">
            <button type="button" @click="openRecord(annotation.record_id)">
              {{ i18n.t("annotations.open_record", "Open record") }}</button
            ><button
              v-if="annotation.removable !== false"
              type="button"
              @click="deleteAnnotation(annotation.id)"
            >
              {{ i18n.t("ui.remove", "Remove") }}
            </button>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<style scoped>
.annotations-page {
  display: grid;
  gap: 14px;
  padding: 16px 18px 28px;
  max-width: 1440px;
  margin: 0 auto;
}
.annotations-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.annotations-toolbar .search {
  flex: 1;
  max-width: 520px;
}
.tools {
  display: flex;
  align-items: center;
  gap: 8px;
}
.annotation-groups,
.annotation-list {
  display: grid;
  gap: 12px;
}
.annotation-group {
  display: grid;
  gap: 12px;
  padding: 16px;
}
.annotation-group h2 {
  margin: 0;
  font:
    600 20px/1.2 Georgia,
    "Times New Roman",
    serif;
}
.annotation-card {
  display: grid;
  gap: 9px;
  padding: 13px;
}
.annotation-card blockquote {
  margin: 0;
  padding: 9px 10px;
  border-left: 3px solid var(--ui-accent, #3c8d62);
  background: var(--soft);
}
.annotation-card p {
  margin: 0;
  line-height: 1.5;
}
.annotation-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.annotation-meta span {
  margin-right: auto;
}
.annotation-meta button {
  border: 0;
  background: transparent;
  color: var(--text-2);
  font-weight: 700;
  cursor: pointer;
}
.annotation-empty-state {
  min-height: 220px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
}
</style>
