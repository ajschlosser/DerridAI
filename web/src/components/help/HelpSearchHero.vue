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
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import UiPageHeader from "../ui/UiPageHeader.vue";

const props = defineProps<{
  modelValue: string;
  searching: boolean;
  matchCount: number;
  pageCount: number;
  termCount: number;
  questionCount: number;
  isAdmin: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const i18n = useI18nStore();
const input = ref<HTMLInputElement | null>(null);
const query = computed({
  get: () => props.modelValue,
  set: (value: string) => emit("update:modelValue", value),
});

function clearSearch() {
  emit("update:modelValue", "");
  input.value?.focus();
}

function focusSearch() {
  input.value?.focus();
}

defineExpose({ focusSearch });
</script>

<template>
  <header class="help-hero">
    <UiPageHeader
      :kicker="i18n.t('help.kicker')"
      :title="i18n.t('help.title')"
      title-id="help-center-title"
      :description="i18n.t('help.intro')"
    />

    <div class="help-discovery">
      <div class="help-search-panel">
        <div class="help-search-heading">
          <div>
            <h2>{{ i18n.t("help.find_answer") }}</h2>
            <p>{{ i18n.t("help.find_answer_help") }}</p>
          </div>
          <span class="help-audience">
            <AppIcon :name="isAdmin ? 'roles' : 'record'" aria-hidden="true" />
            {{ i18n.t(isAdmin ? "help.audience_admin" : "help.audience_researcher") }}
          </span>
        </div>

        <div class="help-search-bar" role="search">
          <label class="help-search" for="help-search-input">
            <span class="sr-only">{{ i18n.t("help.search") }}</span>
            <span class="help-search-control">
              <AppIcon name="search" aria-hidden="true" />
              <input
                id="help-search-input"
                ref="input"
                v-model="query"
                class="control"
                type="search"
                :placeholder="i18n.t('help.search_placeholder')"
                autocomplete="off"
                aria-describedby="help-search-status help-search-examples"
                @keydown.esc="clearSearch"
              />
              <button
                v-if="modelValue"
                type="button"
                class="help-search-clear"
                :aria-label="i18n.t('help.clear_search')"
                @click="clearSearch"
              >
                <AppIcon name="close" aria-hidden="true" />
              </button>
              <kbd
                v-else
                class="help-kbd"
                :title="i18n.t('help.search_shortcut')"
                aria-hidden="true"
              >
                /
              </kbd>
            </span>
          </label>
          <div class="help-search-meta">
            <p id="help-search-status" class="help-search-status" role="status" aria-live="polite">
              {{
                searching
                  ? i18n.tf("help.results_found", { count: matchCount })
                  : i18n.t("help.search_hint")
              }}
            </p>
            <p id="help-search-examples" class="help-search-examples">
              {{ i18n.t("help.search_examples") }}
            </p>
          </div>
        </div>
      </div>

      <dl class="help-coverage" :aria-label="i18n.t('help.coverage_label')">
        <div>
          <dt>{{ i18n.t("help.pages_count_label") }}</dt>
          <dd>{{ pageCount.toLocaleString(i18n.locale) }}</dd>
        </div>
        <div>
          <dt>{{ i18n.t("help.terms_count_label") }}</dt>
          <dd>{{ termCount.toLocaleString(i18n.locale) }}</dd>
        </div>
        <div>
          <dt>{{ i18n.t("help.questions_count_label") }}</dt>
          <dd>{{ questionCount.toLocaleString(i18n.locale) }}</dd>
        </div>
      </dl>
    </div>
  </header>
</template>

<style scoped>
.help-hero {
  display: grid;
  gap: var(--space-4);
}

.help-discovery {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(13rem, 18rem);
  gap: var(--space-3);
  align-items: stretch;
}

.help-search-panel,
.help-coverage {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}

.help-search-panel {
  display: grid;
  gap: var(--space-3);
  padding: clamp(16px, 2.4vw, 24px);
  box-shadow: var(--shadow-card);
}

.help-search-heading {
  display: flex;
  gap: var(--space-3);
  align-items: start;
  justify-content: space-between;
}

.help-search-heading > div {
  display: grid;
  gap: 4px;
}

.help-search-heading h2,
.help-search-heading p {
  margin: 0;
}

.help-search-heading h2 {
  color: var(--text-primary);
  font-size: 1.125rem;
  letter-spacing: -0.01em;
}

.help-search-heading p {
  max-inline-size: var(--measure);
  color: var(--text-tertiary);
  font-size: 0.875rem;
  line-height: var(--lh-normal);
}

.help-audience {
  display: inline-flex;
  flex: 0 0 auto;
  gap: 6px;
  align-items: center;
  min-block-size: 30px;
  padding: 4px 9px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: var(--fw-bold);
}

.help-audience :deep(svg) {
  inline-size: 14px;
  block-size: 14px;
}

.help-search-bar {
  display: grid;
  gap: 7px;
}

.help-search {
  display: block;
}

.help-search-control {
  position: relative;
  display: block;
}

.help-search-control > :deep(svg) {
  position: absolute;
  inset-block-start: 50%;
  inset-inline-start: 16px;
  inline-size: 20px;
  block-size: 20px;
  color: var(--text-tertiary);
  pointer-events: none;
  transform: translateY(-50%);
}

.help-search-control input {
  inline-size: 100%;
  min-block-size: 54px;
  padding-inline: 48px 50px;
  border-color: var(--border-strong);
  border-radius: calc(var(--radius-card) - 2px);
  background: var(--surface-page);
  font-size: 1rem;
}

.help-search-control input::-webkit-search-cancel-button {
  display: none;
}

.help-search-control input:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.help-kbd {
  position: absolute;
  inset-block-start: 50%;
  inset-inline-end: 13px;
  min-inline-size: 27px;
  padding: 2px 7px;
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  background: var(--surface-inset);
  color: var(--text-secondary);
  font: inherit;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  text-align: center;
  pointer-events: none;
  transform: translateY(-50%);
}

.help-search-clear {
  position: absolute;
  inset-block-start: 50%;
  inset-inline-end: 8px;
  display: grid;
  place-items: center;
  inline-size: 38px;
  block-size: 38px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transform: translateY(-50%);
}

.help-search-clear:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.help-search-clear:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}

.help-search-clear :deep(svg) {
  inline-size: 17px;
  block-size: 17px;
}

.help-search-meta {
  display: flex;
  gap: var(--space-2);
  align-items: start;
  justify-content: space-between;
}

.help-search-status,
.help-search-examples {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: var(--lh-normal);
}

.help-search-status {
  min-block-size: 1.25rem;
}

.help-search-examples {
  max-inline-size: 22rem;
  text-align: end;
}

.help-coverage {
  display: grid;
  grid-template-rows: repeat(3, 1fr);
  margin: 0;
  overflow: clip;
}

.help-coverage > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: center;
  padding: 12px 14px;
}

.help-coverage > div + div {
  border-block-start: 1px solid var(--border-subtle);
}

.help-coverage dt {
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 650;
}

.help-coverage dd {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.25rem;
  font-weight: var(--fw-bold);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 820px) {
  .help-discovery {
    grid-template-columns: 1fr;
  }

  .help-coverage {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-template-rows: none;
  }

  .help-coverage > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }

  .help-coverage > div + div {
    border-block-start: 0;
    border-inline-start: 1px solid var(--border-subtle);
  }
}

@media (max-width: 620px) {
  .help-search-heading,
  .help-search-meta {
    align-items: stretch;
    flex-direction: column;
  }

  .help-audience {
    align-self: start;
  }

  .help-search-examples {
    max-inline-size: none;
    text-align: start;
  }

  .help-coverage {
    grid-template-columns: 1fr;
  }

  .help-coverage > div {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .help-coverage > div + div {
    border-inline-start: 0;
    border-block-start: 1px solid var(--border-subtle);
  }
}

@media (forced-colors: active) {
  .help-search-panel,
  .help-coverage,
  .help-audience,
  .help-kbd {
    border-color: CanvasText;
  }
}
</style>
