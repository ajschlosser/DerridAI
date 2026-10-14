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
import { computed, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { SearchFacet } from "../../types/search";

const props = withDefaults(defineProps<{ facets: SearchFacet[]; compact?: boolean }>(), {
  compact: false,
});
const emit = defineEmits<{ toggle: [field: string, value: string]; clear: [] }>();
const i18n = useI18nStore();
const filter = ref("");
const visibleFacets = computed(() => {
  const q = filter.value.trim().toLocaleLowerCase();
  if (!q) return props.facets;
  return props.facets
    .map((facet) => ({
      ...facet,
      values: facet.values.filter((item) => item.label.toLocaleLowerCase().includes(q)),
    }))
    .filter((facet) => facet.values.length || facet.label.toLocaleLowerCase().includes(q));
});
const activeCount = computed(() =>
  props.facets.reduce((sum, facet) => sum + facet.values.filter((item) => item.selected).length, 0),
);
</script>

<template>
  <aside class="search-facets" :class="{ compact }" :aria-label="i18n.t('search.filters')">
    <div class="search-facets-head">
      <div>
        <span class="section-label">{{ i18n.t("search.refine") }}</span>
        <h2>{{ i18n.t("search.filters") }}</h2>
      </div>
      <button
        v-if="activeCount"
        type="button"
        class="text-button"
        v-text="`${i18n.t('search.clear_all')} (${activeCount})`"
        @click="emit('clear')"
      ></button>
    </div>
    <label class="search-facet-find">
      <span class="sr-only">{{ i18n.t("search.filter_facets") }}</span>
      <AppIcon name="search" />
      <input v-model="filter" type="search" :placeholder="i18n.t('search.filter_values')" />
    </label>
    <div v-if="visibleFacets.length" class="search-facet-groups">
      <details
        v-for="(facet, index) in visibleFacets"
        :key="facet.field"
        class="search-facet-group"
        :open="index < 4 || facet.values.some((item) => item.selected)"
      >
        <summary>
          <span>{{ facet.label }}</span
          ><span
            class="search-facet-active-count"
            v-if="facet.values.some((item) => item.selected)"
            >{{ facet.values.filter((item) => item.selected).length }}</span
          >
        </summary>
        <div class="search-facet-values">
          <label
            v-for="item in facet.values"
            :key="`${facet.field}:${item.value}`"
            class="search-facet-option"
            :class="{ selected: item.selected }"
          >
            <input
              type="checkbox"
              :checked="item.selected"
              @change="emit('toggle', facet.field, item.value)"
            />
            <span class="search-facet-label" :title="item.label">{{ item.label }}</span>
            <span class="search-facet-count">{{ item.count.toLocaleString(i18n.locale) }}</span>
          </label>
        </div>
      </details>
    </div>
    <p v-else class="search-facet-empty">{{ i18n.t("search.no_facet_values") }}</p>
  </aside>
</template>

<style scoped>
.search-facet-empty {
  margin: 12px 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}
</style>
