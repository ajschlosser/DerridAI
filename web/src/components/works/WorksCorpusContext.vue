<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import type { WorksStore } from "../../types/works";
import UiButton from "../ui/UiButton.vue";

const props = defineProps<{
  mode: "admin" | "researcher";
  stores: WorksStore[];
  activeStore: string;
  activeStoreCount: number;
  sourceFileCount: number;
  totalRecords: number;
  storesEmptyLabel: string;
  dbUnavailableReason: string;
  canSyncAll: boolean;
  syncAllDisabledReason: string;
}>();
const emit = defineEmits<{ changeStore: [name: string]; syncAll: [] }>();
const i18n = useI18nStore();
</script>

<template>
  <section
    class="works-context"
    :class="{ single: props.mode === 'researcher' }"
    :aria-label="i18n.t('works.context_label')"
  >
    <div v-if="props.mode === 'admin'" class="works-context-panel" data-works-context="loaded">
      <h2>{{ i18n.t("works.loaded_title") }}</h2>
      <p class="works-context-figure">
        {{
          i18n.tf("works.loaded_summary", {
            files: props.sourceFileCount.toLocaleString(i18n.locale),
            records: props.totalRecords.toLocaleString(i18n.locale),
          })
        }}
      </p>
      <p class="works-context-help">{{ i18n.t("works.loaded_help") }}</p>
    </div>

    <div class="works-context-panel" data-works-context="database">
      <h2>{{ i18n.t("works.database_title") }}</h2>
      <div class="works-context-row">
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
        <UiButton
          v-if="props.mode === 'admin'"
          size="small"
          icon="database"
          :label="i18n.t('works.sync_workspace')"
          :disabled="!props.canSyncAll"
          :disabled-reason="props.syncAllDisabledReason"
          @click="emit('syncAll')"
        />
      </div>
      <p class="works-context-figure">
        {{
          props.activeStore
            ? i18n.tf("works.database_records", {
                count: props.activeStoreCount.toLocaleString(i18n.locale),
              })
            : props.dbUnavailableReason
        }}
      </p>
      <p class="works-context-help">
        {{
          props.mode === "admin"
            ? i18n.t("works.database_help")
            : i18n.t("works.database_researcher_help")
        }}
      </p>
    </div>
  </section>
</template>

<style scoped>
.works-context {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}
.works-context.single {
  grid-template-columns: minmax(0, 1fr);
}
.works-context-panel {
  display: grid;
  gap: var(--space-2);
  align-content: start;
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.works-context-panel h2 {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.works-context-figure {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--fs-md);
  font-weight: var(--fw-semibold);
  overflow-wrap: anywhere;
}
.works-context-help {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.works-context-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
}
.works-context-select {
  flex: 1 1 12rem;
  min-width: 0;
}
.works-context-select select {
  width: 100%;
}
@media (max-width: 760px) {
  .works-context {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
