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
/**
 * Result rows for the library search. Each row's primary button carries
 * `data-result-primary` so the dialog can rove focus through the list.
 */
import { computed } from "vue";
import type { GutenbergHit } from "../../api/corpus";
import type { WorkGroup } from "../../features/corpus-builder/domain/wikisourceGroups";
import { useI18nStore } from "../../stores/i18n";

type Library = "gutenberg" | "wikisource";
const props = defineProps<{
  library: Library;
  gutenbergHits: GutenbergHit[];
  workGroups: WorkGroup[];
  searching: boolean;
  collectionReady: boolean;
  disabled: boolean;
  importing: string;
  languageName: (code: string) => string;
}>();
const emit = defineEmits<{
  importGutenberg: [etextId: number];
  importWikisource: [url: string];
}>();
const i18n = useI18nStore();

const importingAny = computed(() => Boolean(props.importing));
function formatNumber(value: number) {
  return new Intl.NumberFormat(i18n.locale || undefined).format(value);
}
/** "Livre I · 4,120 words", "2 matching parts · 10,143 words", or just the length of a work's own page. */
function partLine(group: WorkGroup) {
  const parts =
    group.parts.length === 1 && !group.isWorkPage
      ? group.parts[0].title.slice(group.work.length + 1)
      : group.parts.length > 1
        ? i18n.tf("pdf_corpus.library.matching_parts", { count: group.parts.length })
        : "";
  const words = group.words
    ? i18n.tf("pdf_corpus.library.words", { count: formatNumber(group.words) })
    : "";
  return [parts, words].filter(Boolean).join(" · ");
}
</script>

<template>
  <ul
    id="library-results"
    class="ls-results"
    :aria-label="
      library === 'gutenberg'
        ? i18n.t('pdf_corpus.gutenberg_results')
        : i18n.t('pdf_corpus.wikisource')
    "
    :aria-busy="searching"
  >
    <template v-if="library === 'gutenberg'">
      <li v-for="hit in gutenbergHits" :key="hit.etext_id" class="ls-row">
        <div class="ls-row-main">
          <b class="ls-row-title">{{ hit.title }}</b>
          <span class="ls-row-meta"
            >{{ hit.author || i18n.t("pdf_corpus.metadata_unset") }} ·
            {{ hit.language ? languageName(hit.language) : "" }} · #{{ hit.etext_id }}</span
          >
        </div>
        <button
          type="button"
          class="btn small primary"
          data-result-primary
          :disabled="disabled || importingAny"
          :aria-label="i18n.tf('pdf_corpus.library.import_label', { title: hit.title })"
          :aria-busy="importing === `gutenberg:${hit.etext_id}`"
          :title="collectionReady ? undefined : i18n.t('pdf_corpus.gutenberg_result_unavailable')"
          @click="emit('importGutenberg', hit.etext_id)"
        >
          {{
            importing === `gutenberg:${hit.etext_id}`
              ? i18n.t("pdf_corpus.library.importing")
              : i18n.t("pdf_corpus.library.import")
          }}
        </button>
      </li>
    </template>
    <template v-else>
      <li v-for="group in workGroups" :key="group.key" class="ls-row">
        <div class="ls-row-main">
          <b class="ls-row-title">{{ group.work }}</b>
          <span v-if="partLine(group)" class="ls-row-part">{{ partLine(group) }}</span>
          <span v-if="group.snippet" class="ls-row-snippet">{{ group.snippet }}</span>
        </div>
        <div class="ls-row-actions">
          <button
            type="button"
            class="btn small primary"
            data-result-primary
            :disabled="disabled || importingAny"
            :aria-label="i18n.tf('pdf_corpus.library.import_work_label', { title: group.work })"
            :aria-busy="importing === `wikisource:${group.workUrl}`"
            @click="emit('importWikisource', group.workUrl)"
          >
            {{
              importing === `wikisource:${group.workUrl}`
                ? i18n.t("pdf_corpus.library.importing")
                : i18n.t("pdf_corpus.library.import_work")
            }}
          </button>
          <button
            v-if="group.parts.length === 1 && !group.isWorkPage"
            type="button"
            class="btn small quiet"
            :disabled="disabled || importingAny"
            :aria-label="
              i18n.tf('pdf_corpus.library.import_part_label', { title: group.parts[0].title })
            "
            :aria-busy="importing === `wikisource:${group.parts[0].url}`"
            @click="emit('importWikisource', group.parts[0].url)"
          >
            {{
              importing === `wikisource:${group.parts[0].url}`
                ? i18n.t("pdf_corpus.library.importing")
                : i18n.t("pdf_corpus.library.import_part")
            }}
          </button>
        </div>
      </li>
    </template>
  </ul>
</template>

<style scoped>
.ls-results {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}
.ls-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 4px;
  border-bottom: 1px solid var(--border-subtle, var(--line));
}
.ls-row:last-child {
  border-bottom: 0;
}
.ls-row:focus-within {
  background: var(--surface-hover);
}
.ls-row-main {
  display: grid;
  flex: 1 1 auto;
  gap: 2px;
  min-width: 0;
}
.ls-row-title {
  font-size: var(--fs-base);
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.ls-row-meta,
.ls-row-part {
  color: var(--text-secondary, var(--muted));
  font-size: var(--fs-sm);
}
.ls-row-snippet {
  display: -webkit-box;
  overflow: hidden;
  color: var(--text-tertiary, var(--muted));
  font-size: var(--fs-sm);
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.ls-row-actions {
  display: flex;
  flex: none;
  flex-direction: column;
  align-items: stretch;
  gap: 4px;
}
.ls-row .btn {
  white-space: nowrap;
}
.btn.quiet {
  border-color: transparent;
  background: transparent;
}
.btn.quiet:hover:not(:disabled) {
  background: var(--surface-hover);
}
:is(button, select, .ls-chip):focus-visible {
  outline: 3px solid var(--focus-ring, var(--accent));
  outline-offset: 2px;
}
@media (max-width: 560px) {
  .ls-row {
    align-items: stretch;
    flex-direction: column;
  }
  .ls-row-actions {
    flex-direction: row;
  }
}
</style>
