<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { ref, watch } from "vue";
import UiButton from "../ui/UiButton.vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { DashboardSearchMode, DashboardWork } from "../../types/dashboard";
const props = defineProps<{
  query: string;
  mode: DashboardSearchMode;
  works: DashboardWork[];
}>();
const emit = defineEmits<{ submit: [query: string, work: string, mode: DashboardSearchMode] }>();
const i18n = useI18nStore();
const query = ref(props.query);
const work = ref("");
const mode = ref<DashboardSearchMode>(props.mode);
watch(
  () => props.query,
  (value) => (query.value = value),
);
watch(
  () => props.mode,
  (value) => (mode.value = value),
);
function submit() {
  emit("submit", query.value, work.value, mode.value);
}
</script>
<template>
  <section class="search-panel card" aria-labelledby="home-search-title">
    <div class="heading">
      <AppIcon name="search" aria-hidden="true" />
      <h2 id="home-search-title">{{ i18n.t("dashboard.global_search", "Global Search") }}</h2>
    </div>
    <form @submit.prevent="submit">
      <fieldset>
        <legend class="sr-only">{{ i18n.t("search.search_controls", "Search controls") }}</legend>
        <div
          class="modes"
          role="group"
          :aria-label="i18n.t('dashboard.search_method', 'Search method')"
        >
          <UiButton
            size="small"
            :variant="mode === 'traditional' ? 'primary' : 'ghost'"
            :pressed="mode === 'traditional'"
            :label="i18n.t('research.traditional_search', 'Traditional search')"
            @click="mode = 'traditional'"
          /><UiButton
            size="small"
            :variant="mode === 'database' ? 'primary' : 'ghost'"
            :pressed="mode === 'database'"
            :label="i18n.t('research.semantic_db_search', 'Semantic DB Search')"
            @click="mode = 'database'"
          />
        </div>
        <label
          ><span>{{ i18n.t("search.query", "Search query") }}</span
          ><input
            v-model="query"
            type="search"
            autocomplete="off"
            :placeholder="
              i18n.t('dashboard.search_corpus_placeholder', 'Search the corpus…')
            " /></label
        ><label
          ><span>{{ i18n.t("field.work", "Work") }}</span
          ><select v-model="work">
            <option value="">{{ i18n.t("dashboard.all_works", "All works") }}</option>
            <option v-for="item in works" :key="item.work" :value="item.work">
              {{ item.work }}
            </option>
          </select></label
        ><UiButton
          type="submit"
          variant="primary"
          icon="search"
          :label="i18n.t('ui.search', 'Search')"
        />
      </fieldset>
    </form>
    <p>
      {{
        i18n.t(
          "dashboard.search_help",
          "Search across works, metadata, annotations, and—when available—the semantic database.",
        )
      }}
    </p>
  </section>
</template>
<style scoped>
.search-panel {
  padding: var(--space-5);
}
.heading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.heading h2 {
  margin: 0;
  font-size: var(--fs-lg);
}
fieldset {
  display: grid;
  grid-template-columns: 1fr 160px auto;
  gap: var(--space-3);
  padding: 0;
  border: 0;
}
.modes {
  grid-column: 1/-1;
  display: flex;
  gap: var(--space-1);
  padding: var(--space-1);
  background: var(--soft);
  border-radius: var(--radius-sm);
}
label {
  display: grid;
  gap: var(--space-1);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  color: var(--text-2);
}
input,
select {
  min-height: 40px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--text);
  padding: var(--space-2);
  font: inherit;
}
input:focus-visible,
select:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
p {
  margin: var(--space-3) 0 0;
  color: var(--muted);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
@media (max-width: 620px) {
  fieldset {
    grid-template-columns: 1fr;
  }
  .modes {
    grid-column: auto;
  }
}
</style>
