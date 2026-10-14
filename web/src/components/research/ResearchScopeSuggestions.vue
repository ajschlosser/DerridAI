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
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { researchFiltersApi } from "../../api/researchFilters";
import type { ResearchFilterInventory } from "../../api/researchFilters";
import { researchFilterCatalog } from "../../domain/researchFilters";
import {
  appendFilterExpression,
  interpretResearchInstructionFilters,
} from "../../domain/researchInstructionFilters";
import { useI18nStore } from "../../stores/i18n";

const props = withDefaults(
  defineProps<{
    instructions: string;
    inventoryData?: ResearchFilterInventory | null;
    providerProfileId?: string;
    resolveModel?: typeof researchFiltersApi.resolve;
    filterExpression: string;
    collection: string;
    fields: string[];
    locales?: string[];
    disabled?: boolean;
    debounceMs?: number;
    /** Overridable for stories and tests. */
    loadInventory?: (body: {
      collection: string;
      locales?: string[];
    }) => Promise<ResearchFilterInventory>;
  }>(),
  { locales: () => [], disabled: false, debounceMs: 300, loadInventory: undefined },
);
const emit = defineEmits<{
  "update:filterExpression": [value: string];
  accepted: [source: "deterministic_natural_language" | "model_assisted"];
}>();

const i18n = useI18nStore();
const effectiveInventory = computed(() => props.inventoryData ?? inventory.value);
const catalog = computed(() =>
  researchFilterCatalog(props.fields, effectiveInventory.value?.fields),
);
const inventoryCache = new Map<string, ResearchFilterInventory>();
const inventory = ref<ResearchFilterInventory | null>(null);
// Debounced copy of the instructions: interpretation is local and cheap, but a
// screen-reader live region should not announce every keystroke.
const settled = ref(props.instructions);
let timer: ReturnType<typeof setTimeout> | undefined;
let ticket = 0;

watch(
  () => props.instructions,
  (value) => {
    clearTimeout(timer);
    timer = setTimeout(() => (settled.value = value), props.debounceMs);
  },
);
onBeforeUnmount(() => {
  clearTimeout(timer);
  ticket += 1;
});

// The inventory is fetched only once the instructions are non-empty, and then
// reused per collection; a stale response is dropped after a collection change.
watch(
  [
    () => props.collection,
    () => Boolean(settled.value.trim()),
    () => JSON.stringify(props.locales),
    () => props.disabled,
  ],
  async ([collection, hasText]) => {
    ticket += 1;
    const mine = ticket;
    inventory.value = null;
    if (props.inventoryData !== undefined || !collection || !hasText || props.disabled) return;
    const cacheKey = JSON.stringify([collection, props.locales]);
    const cached = inventoryCache.get(cacheKey);
    if (cached) {
      inventory.value = cached;
      return;
    }
    try {
      const result = await (props.loadInventory ?? researchFiltersApi.inventory)({
        collection,
        locales: props.locales,
      });
      if (mine !== ticket) return;
      inventoryCache.set(cacheKey, result);
      inventory.value = result;
    } catch {
      // Without an inventory only inventory-free phrases (speaker, pages, years) are proposed.
      if (mine === ticket) inventory.value = { works: [], truncated: false };
    }
  },
  { immediate: true },
);

const interpretation = computed(() =>
  interpretResearchInstructionFilters(
    settled.value,
    effectiveInventory.value ?? { works: [] },
    catalog.value,
  ),
);
const visible = computed(
  () => interpretation.value.proposals.length + interpretation.value.unresolved.length > 0,
);

function added(expression: string) {
  return props.filterExpression.includes(expression);
}
function add(
  expression: string,
  source: "deterministic_natural_language" | "model_assisted" = "deterministic_natural_language",
) {
  emit("update:filterExpression", appendFilterExpression(props.filterExpression, expression));
  emit("accepted", source);
}
const modelResult = ref<Awaited<ReturnType<typeof researchFiltersApi.resolve>> | null>(null);
const modelBusy = ref(false);
const modelError = ref(false);
let modelRequest: AbortController | null = null;
watch([() => props.collection, () => props.instructions, () => props.providerProfileId], () => {
  modelRequest?.abort();
  modelResult.value = null;
  modelError.value = false;
  modelBusy.value = false;
});
onBeforeUnmount(() => modelRequest?.abort());
async function resolveAmbiguity() {
  modelRequest?.abort();
  const controller = new AbortController();
  modelRequest = controller;
  modelBusy.value = true;
  modelError.value = false;
  modelResult.value = null;
  try {
    const result = await (props.resolveModel ?? researchFiltersApi.resolve)(
      {
        collection: props.collection,
        instructions: props.instructions,
        provider_profile_id: props.providerProfileId,
        locales: props.locales,
      },
      controller.signal,
    );
    if (controller.signal.aborted) return;
    modelResult.value = result;
  } catch {
    if (!controller.signal.aborted) modelError.value = true;
  } finally {
    if (!controller.signal.aborted) modelBusy.value = false;
  }
}
function reason(item: { reason: string; phrase: string; params: Record<string, string> }) {
  return i18n.tf(`research.scope.reason.${item.reason}`, { ...item.params, phrase: item.phrase });
}
</script>

<template>
  <section v-if="visible" class="research-scope" aria-live="polite">
    <h3>{{ i18n.t("research.scope.title") }}</h3>
    <p class="note">{{ i18n.t("research.scope.help") }}</p>
    <ul v-if="interpretation.proposals.length" class="research-scope-proposals">
      <li v-for="proposal in interpretation.proposals" :key="proposal.id">
        <q>{{ proposal.phrase }}</q>
        <code>{{ proposal.expression }}</code>
        <span v-if="!proposal.verified" class="note">{{
          i18n.t("research.scope.unverified")
        }}</span>
        <span v-if="added(proposal.expression)" class="research-scope-added">
          <span aria-hidden="true">✓ </span>{{ i18n.t("research.scope.added") }}
        </span>
        <button
          v-else
          type="button"
          class="btn"
          :disabled="disabled"
          :aria-label="i18n.tf('research.scope.add_label', { expression: proposal.expression })"
          @click="add(proposal.expression)"
        >
          {{ i18n.t("research.scope.add") }}
        </button>
      </li>
    </ul>
    <template v-if="interpretation.unresolved.length">
      <h4>{{ i18n.t("research.scope.unresolved_title") }}</h4>
      <ul class="research-scope-unresolved">
        <li v-for="(item, index) in interpretation.unresolved" :key="index">
          <span aria-hidden="true">ℹ </span>{{ reason(item) }}
        </li>
      </ul>
      <p class="note">{{ i18n.t("research.scope.model_help") }}</p>
      <button
        class="btn"
        type="button"
        :disabled="disabled || modelBusy || !effectiveInventory?.fields?.length"
        @click="resolveAmbiguity"
      >
        {{ i18n.t(modelBusy ? "research.scope.model_busy" : "research.scope.model_resolve") }}
      </button>
    </template>
    <p v-if="modelError" role="alert">{{ i18n.t("research.scope.model_error") }}</p>
    <div v-if="modelResult" role="status">
      <p>{{ i18n.tf("research.scope.model_label", { model: modelResult.model }) }}</p>
      <code v-if="modelResult.expression">{{ modelResult.expression }}</code>
      <button
        v-if="modelResult.expression && !added(modelResult.expression)"
        class="btn"
        type="button"
        :disabled="disabled"
        @click="add(modelResult.expression, 'model_assisted')"
      >
        {{ i18n.t("research.scope.add") }}
      </button>
      <p v-for="(phrase, index) in modelResult.unresolved" :key="index">{{ phrase }}</p>
      <p v-if="!modelResult.expression">{{ i18n.t("research.scope.model_empty") }}</p>
    </div>
  </section>
</template>

<style scoped>
.research-scope {
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-inset);
  font-size: 0.8125rem;
}
.research-scope h3,
.research-scope h4 {
  margin: 0;
  font-size: 0.875rem;
}
.research-scope ul {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.research-scope-proposals li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.research-scope-added {
  color: var(--tone-ok-fg);
  font-weight: 700;
}
</style>
