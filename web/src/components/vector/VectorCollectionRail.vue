<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiButton from "../ui/UiButton.vue";
import { useI18nStore } from "../../stores/i18n";
import type { VectorCollection } from "../../types/vector";

const props = defineProps<{
  collections: VectorCollection[];
  activeName: string;
  filter: string;
}>();
const emit = defineEmits<{
  "update:filter": [string];
  select: [name: string];
  refresh: [];
  create: [];
}>();
const i18n = useI18nStore();

function statusOf(store: VectorCollection) {
  return String(store.status || (store.count || 0 ? "ready" : "empty")).toLowerCase();
}
</script>
<template>
  <aside class="card vector-collection-sidebar">
    <div class="vector-collection-head">
      <div>
        <b>{{ i18n.t("vector.collections") }}</b>
        <span
          >{{ props.collections.length.toLocaleString(i18n.locale) }}
          {{ i18n.t("vector.collections") }}</span
        >
      </div>
      <UiButton
        icon="refresh"
        icon-only
        size="small"
        :label="i18n.t('ui.refresh')"
        @click="emit('refresh')"
      />
    </div>
    <div class="vector-rail-actions">
      <label class="sr-only" for="vector-collection-filter">{{
        i18n.t("vector.filter_collections")
      }}</label>
      <input
        id="vector-collection-filter"
        class="control"
        :value="props.filter"
        :placeholder="i18n.t('vector.filter_collections')"
        autocomplete="off"
        @input="emit('update:filter', ($event.target as HTMLInputElement).value)"
      />
      <UiButton
        :label="i18n.t('vector.new_collection_short')"
        icon="plus"
        variant="primary"
        @click="emit('create')"
      />
    </div>
    <div
      v-if="props.collections.length"
      class="vector-collection-list"
      role="listbox"
      :aria-label="i18n.t('vector.collections')"
    >
      <button
        v-for="store in props.collections"
        :key="store.name"
        type="button"
        class="storeitem"
        :class="{ active: store.name === props.activeName }"
        role="option"
        :aria-selected="store.name === props.activeName"
        @click="emit('select', store.name)"
      >
        <span
          class="vector-store-status-dot"
          :class="`vector-store-status-${statusOf(store)}`"
          aria-hidden="true"
        ></span>
        <span>
          <b>{{ store.name }}</b>
          <small
            >{{ Number(store.count || 0).toLocaleString(i18n.locale) }} ·
            {{ store.retrieval_mode || "semantic" }} ·
            {{ statusOf(store).replaceAll("_", " ") }}</small
          >
        </span>
        <span aria-hidden="true">›</span>
      </button>
    </div>
    <div v-else class="vector-rail-empty">{{ i18n.t("vector.no_collection_matches") }}</div>
  </aside>
</template>

<style scoped>
.vector-rail-empty {
  padding: 18px 12px;
  color: var(--muted);
  font-size: 0.82rem;
  text-align: center;
}
</style>
