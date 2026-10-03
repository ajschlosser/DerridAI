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
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type { WorksIndexFreshness, WorksStore } from "../../types/works";
import UiButton from "../ui/UiButton.vue";

const props = defineProps<{
  mode: "admin" | "researcher";
  stores: WorksStore[];
  activeStore: string;
  activeStoreCount: number;
  sourceFileCount: number;
  totalRecords: number;
  indexFreshness: WorksIndexFreshness;
  storesEmptyLabel: string;
  dbUnavailableReason: string;
  canSyncAll: boolean;
  syncAllDisabledReason: string;
}>();
const emit = defineEmits<{ changeStore: [name: string]; syncAll: [] }>();
const i18n = useI18nStore();

const staleRecords = computed(
  () => props.indexFreshness.changedRecords + props.indexFreshness.absentRecords,
);

const indexSummary = computed(() => {
  if (props.mode === "researcher")
    return props.activeStore
      ? i18n.tf("works.database_records", {
          count: props.activeStoreCount.toLocaleString(i18n.locale),
        })
      : props.dbUnavailableReason;

  const freshness = props.indexFreshness;
  const values = {
    current: freshness.currentRecords.toLocaleString(i18n.locale),
    total: freshness.totalRecords.toLocaleString(i18n.locale),
    stale: staleRecords.value.toLocaleString(i18n.locale),
  };
  if (freshness.state === "current") return i18n.tf("works.index_current", values);
  if (freshness.state === "stale") return i18n.tf("works.index_stale", values);
  if (freshness.state === "unavailable") return i18n.t("works.index_unavailable");
  if (freshness.state === "empty") return i18n.t("works.index_empty");
  return i18n.tf("works.index_partial", values);
});
</script>

<template>
  <section
    class="works-context"
    :class="{ researcher: props.mode === 'researcher' }"
    :aria-label="i18n.t('works.context_label')"
  >
    <div v-if="props.mode === 'admin'" class="works-context-node" data-works-context="loaded">
      <span class="works-context-label">{{ i18n.t("works.working_corpus_title") }}</span>
      <strong>
        {{
          i18n.tf("works.loaded_summary", {
            files: props.sourceFileCount.toLocaleString(i18n.locale),
            records: props.totalRecords.toLocaleString(i18n.locale),
          })
        }}
      </strong>
      <small>{{ i18n.t("works.working_corpus_help") }}</small>
    </div>

    <div v-if="props.mode === 'admin'" class="works-context-arrow" aria-hidden="true">→</div>

    <div class="works-context-node works-context-index" data-works-context="database">
      <div class="works-context-index-heading">
        <span class="works-context-label">{{ i18n.t("works.search_index_title") }}</span>
        <label class="works-context-select">
          <span class="sr-only">{{ i18n.t("works.database_select") }}</span>
          <select
            id="worksStore"
            class="control compact-select"
            :value="props.activeStore"
            :disabled="!props.stores.length"
            @change="emit('changeStore', ($event.target as HTMLSelectElement).value)"
          >
            <option v-if="!props.stores.length" value="">{{ props.storesEmptyLabel }}</option>
            <option v-for="store in props.stores" :key="store.name" :value="store.name">
              {{ store.name }} ({{ store.count }})
            </option>
          </select>
        </label>
      </div>
      <strong class="works-context-index-summary" :data-index-state="props.indexFreshness.state">
        {{ indexSummary }}
      </strong>
      <small>
        {{
          props.mode === "admin"
            ? i18n.t("works.search_index_help")
            : i18n.t("works.database_researcher_help")
        }}
      </small>
      <UiButton
        v-if="props.mode === 'admin'"
        size="small"
        icon="database"
        :label="i18n.t('works.update_index')"
        :disabled="!props.canSyncAll"
        :disabled-reason="props.syncAllDisabledReason"
        @click="emit('syncAll')"
      />
    </div>
  </section>
</template>

<style scoped>
.works-context {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) auto minmax(18rem, 1.1fr);
  gap: var(--space-3);
  align-items: stretch;
  padding: var(--space-3) var(--space-4);
  border-block: 1px solid var(--border-subtle);
  background: var(--surface-raised);
}
.works-context.researcher {
  grid-template-columns: minmax(0, 1fr);
}
.works-context-node {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-1);
  align-content: center;
  min-width: 0;
}
.works-context-node strong {
  color: var(--text-primary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  overflow-wrap: anywhere;
}
.works-context-node small {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  line-height: var(--lh-normal);
}
.works-context-label {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.works-context-arrow {
  display: grid;
  place-items: center;
  color: var(--text-secondary);
  font-size: var(--fs-lg);
}
.works-context-index {
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: var(--space-3);
}
.works-context-index-heading,
.works-context-index-summary,
.works-context-index > small {
  grid-column: 1;
}
.works-context-index-heading {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.works-context-index > :deep(.ui-button-wrap) {
  grid-column: 2;
  grid-row: 1 / span 3;
  align-self: center;
}
.works-context-select {
  min-width: min(100%, 13rem);
}
.works-context-select select {
  width: 100%;
}
.works-context-index-summary[data-index-state="stale"] {
  color: var(--tone-warn-fg);
}
.works-context-index-summary[data-index-state="unavailable"] {
  color: var(--tone-danger-fg);
}
@media (max-width: 760px) {
  .works-context {
    grid-template-columns: minmax(0, 1fr);
  }
  .works-context-arrow {
    display: none;
  }
  .works-context-index {
    grid-template-columns: minmax(0, 1fr);
    padding-top: var(--space-2);
    border-top: 1px solid var(--border-subtle);
  }
  .works-context-index > :deep(.ui-button-wrap) {
    grid-column: 1;
    grid-row: auto;
    justify-self: start;
  }
}
</style>
