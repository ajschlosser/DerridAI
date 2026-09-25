<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import UiPageHeader from "../ui/UiPageHeader.vue";
import { useI18nStore } from "../../stores/i18n";
import { useDisabledReason } from "../../composables/useDisabledReason";
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
const loadedUnavailable = i18n.t("search.loaded_scope_unavailable");
const loadedDisabledReason = useDisabledReason(loadedDisabled, loadedUnavailable);
</script>

<template>
  <UiPageHeader
    class="search-workspace-header"
    :kicker="i18n.t('search.kicker')"
    :title="i18n.t('search.title')"
    :description="i18n.t('search.subtitle')"
    title-id="search-page-title"
    :actions-label="i18n.t('search.view_actions')"
  >
    <template #actions>
      <div class="search-workspace-actions">
        <button type="button" class="btn" @click="emit('views')">
          <AppIcon name="history" />{{ i18n.t("search.saved_views") }}
        </button>
        <button type="button" class="btn" @click="emit('save')">
          <AppIcon name="plus" />{{ i18n.t("search.save_view") }}
        </button>
        <button type="button" class="btn soft" @click="emit('share')">
          <AppIcon name="copy" />{{ i18n.t("search.copy_link") }}
        </button>
      </div>
    </template>
    <template #meta>
      <div class="search-scope-row">
        <div class="search-scope-switch" role="group" :aria-label="i18n.t('search.scope')">
          <button
            type="button"
            :class="{ active: scope === 'loaded' }"
            :aria-pressed="scope === 'loaded'"
            :disabled="loadedDisabled"
            :title="loadedDisabledReason || undefined"
            @click="emit('update:scope', 'loaded')"
          >
            <AppIcon name="list" />
            <span>{{ i18n.t("search.loaded_records") }}</span>
            <small>{{ Number(totalLoaded || 0).toLocaleString(i18n.locale) }}</small>
          </button>
          <button
            type="button"
            :class="{ active: scope === 'database' }"
            :aria-pressed="scope === 'database'"
            @click="emit('update:scope', 'database')"
          >
            <AppIcon name="database" />
            <span>{{ i18n.t("search.corpus_database") }}</span>
            <small>{{ Number(databaseCount || 0).toLocaleString(i18n.locale) }}</small>
          </button>
        </div>
        <p class="search-workspace-stats" aria-live="polite">
          <span
            ><AppIcon name="spark" />{{
              Number(selectedEvidence || 0).toLocaleString(i18n.locale)
            }}
            {{ i18n.t("dynamic.selected_evidence") }}</span
          >
        </p>
      </div>
    </template>
  </UiPageHeader>
</template>

<style scoped>
.search-workspace-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  justify-content: flex-end;
}
.search-workspace-actions :deep(svg),
.search-scope-switch :deep(svg),
.search-workspace-stats :deep(svg) {
  width: 1rem;
  height: 1rem;
  flex: 0 0 1rem;
}
.search-scope-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.search-scope-switch {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(10rem, 1fr));
  gap: 4px;
  min-width: min(24rem, 100%);
  padding: 4px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.search-scope-switch button {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: center;
  min-height: var(--control-height);
  padding: 6px 10px;
  border: 0;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-tertiary);
  text-align: left;
}
.search-scope-switch button span {
  color: inherit;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.search-scope-switch button small {
  min-width: 1.75rem;
  padding: 2px 6px;
  border-radius: var(--radius-pill);
  background: var(--surface-card);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
  text-align: center;
}
.search-scope-switch button:hover:not(:disabled) {
  background: var(--surface-hover);
  color: var(--text-primary);
}
.search-scope-switch button.active {
  background: var(--surface-card);
  color: var(--accent-fg);
  box-shadow: var(--shadow-card);
}
.search-scope-switch button:disabled {
  cursor: not-allowed;
  color: var(--text-tertiary);
  background: var(--surface-disabled);
}
.search-workspace-stats {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
.search-workspace-stats span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
@media (max-width: 800px) {
  .search-scope-switch {
    width: 100%;
    grid-template-columns: 1fr;
  }
  .search-workspace-actions {
    justify-content: flex-start;
  }
}
</style>
