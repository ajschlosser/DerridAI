<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { SearchScope } from "../../types/search";

const props = withDefaults(
  defineProps<{
    scope: SearchScope;
    researcher?: boolean;
    totalLoaded?: number;
    databaseCount?: number;
    selectedEvidence?: number;
    canUseLoaded?: boolean;
  }>(),
  { researcher: false, totalLoaded: 0, databaseCount: 0, selectedEvidence: 0, canUseLoaded: true },
);
const emit = defineEmits<{
  "update:scope": [scope: SearchScope];
  save: [];
  share: [];
  views: [];
}>();
const i18n = useI18nStore();
const loadedDisabled = computed(() => props.researcher || !props.canUseLoaded);
</script>

<template>
  <header class="search-workspace-header" aria-labelledby="search-page-title">
    <div
      class="search-scope-switch"
      role="group"
      :aria-label="i18n.t('search.scope', 'Search scope')"
    >
      <button
        type="button"
        :class="{ active: scope === 'loaded' }"
        :aria-pressed="scope === 'loaded'"
        :disabled="loadedDisabled"
        :title="
          loadedDisabled
            ? i18n.t(
                'search.loaded_scope_unavailable',
                'Loaded-record search is available to administrators with local JSONL records.',
              )
            : ''
        "
        @click="emit('update:scope', 'loaded')"
      >
        <AppIcon name="list" />
        <span>{{ i18n.t("search.loaded_records", "Loaded records") }}</span>
        <small>{{ Number(totalLoaded || 0).toLocaleString(i18n.locale) }}</small>
      </button>
      <button
        type="button"
        :class="{ active: scope === 'database' }"
        :aria-pressed="scope === 'database'"
        @click="emit('update:scope', 'database')"
      >
        <AppIcon name="database" />
        <span>{{ i18n.t("search.corpus_database", "Corpus database") }}</span>
        <small>{{ Number(databaseCount || 0).toLocaleString(i18n.locale) }}</small>
      </button>
    </div>
    <div class="search-workspace-heading">
      <span class="section-label">{{ i18n.t("search.kicker", "Corpus exploration") }}</span>
      <h1 id="search-page-title">{{ i18n.t("search.title", "Search") }}</h1>
      <p>
        {{
          i18n.t(
            "search.subtitle",
            "Explore loaded records or search the corpus database without losing the context of your query, filters, and evidence.",
          )
        }}
      </p>
    </div>
    <div
      class="search-workspace-actions"
      :aria-label="i18n.t('search.view_actions', 'Search view actions')"
    >
      <button type="button" class="btn" @click="emit('views')">
        <AppIcon name="history" />{{ i18n.t("search.saved_views", "Saved views") }}
      </button>
      <button type="button" class="btn" @click="emit('save')">
        <AppIcon name="plus" />{{ i18n.t("search.save_view", "Save view") }}
      </button>
      <button type="button" class="btn soft" @click="emit('share')">
        <AppIcon name="copy" />{{ i18n.t("search.copy_link", "Copy link") }}
      </button>
    </div>
    <div class="search-workspace-stats" aria-live="polite">
      <span
        ><AppIcon name="spark" />{{ Number(selectedEvidence || 0).toLocaleString(i18n.locale) }}
        {{ i18n.t("dynamic.selected_evidence", "selected evidence") }}</span
      >
    </div>
  </header>
</template>

<style scoped>
.search-workspace-header {
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px 18px;
  align-items: center;
  padding: 14px 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: color-mix(in srgb, var(--panel) 94%, var(--accent-soft));
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.07);
  backdrop-filter: blur(14px);
}

.search-workspace-heading {
  min-width: 0;
}

.search-workspace-heading h1 {
  margin: 0;
  font:
    600 clamp(22px, 2.05vw, 31px) / 1.12 Georgia,
    "Times New Roman",
    serif;
  letter-spacing: -0.018em;
}

.search-workspace-heading p {
  max-width: 72ch;
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.45;
}

.search-workspace-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}

.search-workspace-actions .btn svg,
.search-workspace-stats svg,
.search-scope-switch svg {
  width: 16px;
  height: 16px;
}

.search-scope-switch {
  display: inline-grid;
  grid-template-columns: 1fr;
  gap: 4px;
  min-width: 190px;
  padding: 4px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.search-scope-switch button {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-height: 34px;
  padding: 5px 9px;
  color: var(--muted);
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 9px;
}

.search-scope-switch button span {
  color: inherit;
  font-size: 0.8125rem;
  font-weight: 760;
}

.search-scope-switch button small {
  min-width: 28px;
  padding: 2px 6px;
  font-size: 0.8125rem;
  font-weight: 800;
  text-align: center;
  background: color-mix(in srgb, var(--text) 6%, transparent);
  border-radius: 999px;
}

.search-scope-switch button:hover:not(:disabled) {
  color: var(--text);
  background: color-mix(in srgb, var(--card) 72%, transparent);
}

.search-scope-switch button.active {
  color: var(--accent-fg);
  background: var(--panel);
  box-shadow:
    0 1px 4px color-mix(in srgb, var(--text) 8%, transparent),
    inset 0 0 0 1px color-mix(in srgb, var(--accent) 16%, transparent);
}

.search-scope-switch button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.search-workspace-stats {
  grid-column: 3;
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 650;
}

.search-workspace-stats span {
  display: inline-flex;
  gap: 6px;
  align-items: center;
}

@media (max-width: 1050px) {
  .search-workspace-header {
    grid-template-columns: 1fr auto;
  }

  .search-scope-switch {
    grid-column: 1 / -1;
    grid-template-columns: repeat(2, minmax(160px, 1fr));
    width: 100%;
  }

  .search-workspace-actions {
    justify-content: flex-end;
  }

  .search-workspace-stats {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .search-workspace-header {
    grid-template-columns: 1fr;
    padding: 14px 15px;
  }

  .search-workspace-actions {
    justify-content: flex-start;
    width: 100%;
  }

  .search-workspace-actions .btn {
    flex: 1 1 auto;
    justify-content: center;
  }

  .search-scope-switch {
    grid-template-columns: 1fr;
  }
}
</style>
