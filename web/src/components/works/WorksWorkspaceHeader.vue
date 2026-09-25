<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import type { WorksStore } from "../../types/works";

const props = defineProps<{
  stores: WorksStore[];
  activeStore: string;
  activeStoreCount: number;
  totalWorks: number;
  totalRecords: number;
  sourceFileCount: number;
  storesEmptyLabel: string;
  dbUnavailableReason: string;
  canManageCorpus: boolean;
  canPopulate: boolean;
  canSyncAll: boolean;
  corpusManageDeniedReason: string;
  populateDisabledReason: string;
  syncAllDisabledReason: string;
}>();

const emit = defineEmits<{
  changeStore: [name: string];
  chooseJsonl: [];
  separate: [];
  populateAll: [];
  syncAll: [];
}>();

const i18n = useI18nStore();
</script>

<template>
  <header class="works-workspace-header" aria-labelledby="works-page-title">
    <div class="works-header-copy">
      <span class="section-label">{{ i18n.t("works.workspace_kicker") }}</span>
      <h1 id="works-page-title">{{ i18n.t("nav.works") }}</h1>
      <p>
        {{ i18n.t("works.workspace_help") }}
      </p>
    </div>

    <div class="works-header-actions" :aria-label="i18n.t('works.workspace_actions')">
      <button
        id="chooseWorksJsonl"
        type="button"
        class="btn small"
        :disabled="!props.canManageCorpus"
        :data-disabled-reason="props.canManageCorpus ? undefined : props.corpusManageDeniedReason"
        :title="props.canManageCorpus ? undefined : props.corpusManageDeniedReason"
        @click="emit('chooseJsonl')"
      >
        <AppIcon name="upload" aria-hidden="true" />{{ i18n.t("records.choose_jsonl") }}
      </button>
      <button id="separateWorks" type="button" class="btn small" @click="emit('separate')">
        <AppIcon name="filter" aria-hidden="true" />{{ i18n.t("works.separate_jsonl") }}
      </button>
      <button
        id="populateAllWorks"
        type="button"
        class="btn small soft"
        :disabled="!props.canPopulate"
        :data-disabled-reason="props.canPopulate ? undefined : props.populateDisabledReason"
        :title="props.canPopulate ? undefined : props.populateDisabledReason"
        @click="emit('populateAll')"
      >
        <AppIcon name="spark" aria-hidden="true" />{{ i18n.t("works.populate_all_metadata") }}
      </button>
      <button
        id="syncAllWorks"
        type="button"
        class="btn small primary"
        :disabled="!props.canSyncAll"
        :data-disabled-reason="props.canSyncAll ? undefined : props.syncAllDisabledReason"
        :title="props.canSyncAll ? undefined : props.syncAllDisabledReason"
        @click="emit('syncAll')"
      >
        <AppIcon name="database" aria-hidden="true" />{{ i18n.t("works.sync_all") }}
      </button>
    </div>

    <dl class="works-header-metrics" :aria-label="i18n.t('works.workspace_summary')">
      <div>
        <dt>{{ i18n.t("dynamic.works") }}</dt>
        <dd>{{ props.totalWorks.toLocaleString(i18n.locale) }}</dd>
      </div>
      <div>
        <dt>{{ i18n.t("dynamic.records") }}</dt>
        <dd>{{ props.totalRecords.toLocaleString(i18n.locale) }}</dd>
      </div>
      <div>
        <dt>{{ i18n.t("works.source_files") }}</dt>
        <dd>{{ props.sourceFileCount.toLocaleString(i18n.locale) }}</dd>
      </div>
    </dl>

    <label class="works-sync-target">
      <span>{{ i18n.t("works.sync_target") }}</span>
      <select
        id="worksStore"
        class="control compact-select"
        :value="props.activeStore"
        :disabled="!props.stores.length"
        :data-disabled-reason="props.stores.length ? undefined : props.dbUnavailableReason"
        :title="props.stores.length ? undefined : props.dbUnavailableReason"
        @change="emit('changeStore', ($event.target as HTMLSelectElement).value)"
      >
        <option v-if="!props.stores.length" value="">{{ props.storesEmptyLabel }}</option>
        <option v-for="store in props.stores" :key="store.name" :value="store.name">
          {{ store.name }} ({{ store.count }})
        </option>
      </select>
      <small>{{
        props.activeStore
          ? `${props.activeStoreCount.toLocaleString(i18n.locale)} ${i18n.t("dynamic.records")}`
          : props.dbUnavailableReason
      }}</small>
    </label>
  </header>
</template>

<style scoped>
.works-workspace-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 27rem);
  gap: 1rem;
  align-items: start;
  padding: 1.25rem;
  border: 1px solid color-mix(in srgb, var(--border) 72%, transparent);
  border-radius: 12px;
  background:
    linear-gradient(
      135deg,
      color-mix(in srgb, var(--surface-card) 96%, var(--accent) 4%),
      var(--surface-card)
    ),
    var(--surface-card);
  box-shadow: var(--shadow-soft);
}

.works-header-copy {
  min-width: 0;
}

.works-header-copy h1 {
  margin: 0.2rem 0 0;
  color: var(--text);
  font-size: clamp(2rem, 4vw, 3.25rem);
  line-height: 0.95;
  letter-spacing: 0;
}

.works-header-copy p {
  max-width: 48rem;
  margin: 0.65rem 0 0;
  color: var(--muted);
  font-size: 0.98rem;
  line-height: 1.55;
}

.works-header-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.55rem;
}

.works-header-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0;
}

.works-header-metrics div,
.works-sync-target {
  min-width: 0;
  border: 1px solid color-mix(in srgb, var(--border) 72%, transparent);
  border-radius: 10px;
  background: color-mix(in srgb, var(--surface-raised) 88%, transparent);
}

.works-header-metrics div {
  padding: 0.8rem;
}

.works-header-metrics dt {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.works-header-metrics dd {
  margin: 0.3rem 0 0;
  color: var(--text);
  font-size: 1.45rem;
  font-weight: 850;
  line-height: 1;
}

.works-sync-target {
  display: grid;
  gap: 0.45rem;
  padding: 0.8rem;
}

.works-sync-target > span {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.works-sync-target small {
  min-height: 1rem;
  color: var(--muted);
  font-size: 0.78rem;
}

@media (max-width: 860px) {
  .works-workspace-header {
    grid-template-columns: 1fr;
  }

  .works-header-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 560px) {
  .works-header-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
