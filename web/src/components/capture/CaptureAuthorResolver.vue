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
import { ref, useId } from "vue";
import { corpusCaptureApi, type AuthorCandidate } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";

/**
 * Find the person a capture is about. The API prefers the installed Gutenberg
 * catalogue and falls back to Wikidata; the user always chooses a result.
 */
const props = defineProps<{ modelValue: AuthorCandidate | null }>();
const emit = defineEmits<{ "update:modelValue": [AuthorCandidate | null] }>();
const i18n = useI18nStore();
const id = useId();
const query = ref("");
const results = ref<AuthorCandidate[]>([]);
const searched = ref("");
const busy = ref(false);
const error = ref("");

async function search() {
  const text = query.value.trim();
  if (!text) return;
  busy.value = true;
  error.value = "";
  emit("update:modelValue", null);
  try {
    const language = (i18n.locale || "en").split("-")[0].toLowerCase();
    results.value = (await corpusCaptureApi.searchAuthors(text, language)).items;
    searched.value = text;
  } catch (cause) {
    results.value = [];
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    busy.value = false;
  }
}

function identity(person: AuthorCandidate) {
  return person.identity_id || (person.wikidata_qid ? `wikidata:${person.wikidata_qid}` : "");
}

function isChosen(person: AuthorCandidate) {
  return Boolean(props.modelValue && identity(props.modelValue) === identity(person));
}

function lifespan(person: AuthorCandidate) {
  const year = (value: number | null) =>
    value === null
      ? "?"
      : value < 0
        ? i18n.tf("capture.author.bce", { year: Math.abs(value) })
        : String(value);
  if (person.birth_year === null && person.death_year === null) return "";
  return `${year(person.birth_year)}–${person.death_year === null ? "" : year(person.death_year)}`;
}
</script>

<template>
  <div class="author-resolver">
    <form class="ar-search" role="search" @submit.prevent="search">
      <label :for="`${id}-q`">{{ i18n.t("capture.author.search_label") }}</label>
      <div class="ar-row">
        <input
          :id="`${id}-q`"
          v-model="query"
          class="control"
          type="search"
          autocomplete="off"
          :placeholder="i18n.t('capture.author.search_placeholder')"
        />
        <button type="submit" class="btn primary" :disabled="busy || !query.trim()">
          <AppIcon name="search" />{{
            busy ? i18n.t("capture.author.searching") : i18n.t("capture.author.search")
          }}
        </button>
      </div>
      <small class="ar-help">{{ i18n.t("capture.author.help") }}</small>
    </form>

    <p v-if="error" class="ar-error" role="alert">
      <AppIcon name="warning" />{{ i18n.tf("capture.author.failed", { error }) }}
    </p>
    <p v-else-if="searched && !results.length && !busy" class="ar-empty" role="status">
      {{ i18n.tf("capture.author.none", { query: searched }) }}
    </p>

    <fieldset v-if="results.length" class="ar-results">
      <legend>
        {{ i18n.tf("capture.author.results", { count: results.length, query: searched }) }}
      </legend>
      <p v-if="results.length > 1" class="ar-ambiguous" role="status">
        <AppIcon name="help" />{{ i18n.t("capture.author.ambiguous") }}
      </p>
      <label
        v-for="person in results"
        :key="identity(person)"
        class="ar-person"
        :class="{ 'is-chosen': isChosen(person) }"
        :data-identity="identity(person)"
      >
        <input
          type="radio"
          :name="`${id}-person`"
          :value="identity(person)"
          :checked="isChosen(person)"
          @change="emit('update:modelValue', person)"
        />
        <span class="ar-copy">
          <strong
            >{{ person.label }}
            <span v-if="lifespan(person)" class="ar-dates">({{ lifespan(person) }})</span></strong
          >
          <span v-if="person.description" class="ar-desc">{{ person.description }}</span>
          <small class="ar-meta">
            <span v-if="person.wikidata_qid">{{
              i18n.tf("capture.author.qid", { qid: person.wikidata_qid })
            }}</span>
            <span v-else>{{ i18n.t("capture.provider.gutenberg") }}</span>
            <span v-if="Object.keys(person.wikisource_sitelinks).length">
              ·
              {{
                i18n.tf("capture.author.wikisource_projects", {
                  count: Object.keys(person.wikisource_sitelinks).length,
                })
              }}</span
            >
          </small>
          <small v-if="person.aliases.length" class="ar-aliases">
            {{ i18n.t("capture.author.aliases") }}: {{ person.aliases.slice(0, 6).join("; ") }}
          </small>
        </span>
      </label>
    </fieldset>
  </div>
</template>

<style scoped>
.author-resolver {
  display: grid;
  gap: 12px;
}
.ar-search {
  display: grid;
  gap: 6px;
}
.ar-search label {
  font-weight: var(--fw-semibold);
}
.ar-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ar-row input {
  flex: 1 1 240px;
  min-width: 0;
}
.ar-help,
.ar-empty,
.ar-meta,
.ar-aliases {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.ar-error {
  display: flex;
  gap: 6px;
  color: var(--tone-danger-fg);
}
.ar-results {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  border: 0;
}
.ar-results legend {
  margin-bottom: 6px;
  font-weight: var(--fw-semibold);
}
.ar-ambiguous {
  display: flex;
  gap: 6px;
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--tone-info-border);
  border-radius: var(--radius-control);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: var(--fs-sm);
}
.ar-person {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  cursor: pointer;
}
.ar-person.is-chosen {
  border-color: var(--accent-border);
  background: var(--surface-selected);
}
.ar-person:focus-within {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: 2px;
}
.ar-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.ar-dates {
  color: var(--text-secondary);
  font-weight: var(--fw-regular);
}
.ar-desc {
  overflow-wrap: anywhere;
}
.ar-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
