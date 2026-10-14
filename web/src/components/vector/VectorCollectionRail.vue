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
import UiButton from "../ui/UiButton.vue";
import { useI18nStore } from "../../stores/i18n";
import type { VectorCollection } from "../../types/vector";

const props = defineProps<{
  collections: VectorCollection[];
  activeName: string;
  filter: string;
  canCreate?: boolean;
  createDisabledReason?: string;
}>();
const emit = defineEmits<{
  "update:filter": [string];
  select: [name: string];
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
        :disabled="canCreate === false"
        :disabled-reason="createDisabledReason"
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
