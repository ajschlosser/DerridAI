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
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";

type PageInfo = {
  pdf_page: number;
  printed_page_label?: string | null;
  printed_page_label_source?: string | null;
  width?: number;
  height?: number;
};
const props = withDefaults(defineProps<{ pages?: PageInfo[]; disabled?: boolean }>(), {
  pages: () => [],
  disabled: false,
});
const emit = defineEmits<{ save: [labels: Record<number, string | null>] }>();
const i18n = useI18nStore();
const offset = ref(0);
const pageSize = 25;
const draft = ref<Record<number, string>>({});
const dirty = ref(new Set<number>());
const visible = computed(() => props.pages.slice(offset.value, offset.value + pageSize));
const pageNumber = computed(() => Math.floor(offset.value / pageSize) + 1);
const pageCount = computed(() => Math.max(1, Math.ceil(props.pages.length / pageSize)));
const rangeStart = computed(() => (props.pages.length ? offset.value + 1 : 0));
const rangeEnd = computed(() => Math.min(offset.value + pageSize, props.pages.length));
watch(
  () => props.pages,
  () => {
    draft.value = Object.fromEntries(
      props.pages.map((page) => [page.pdf_page, String(page.printed_page_label ?? "")]),
    );
    dirty.value = new Set();
    offset.value = 0;
  },
  { immediate: true, deep: true },
);
function update(page: number, value: string) {
  draft.value = { ...draft.value, [page]: value };
  const next = new Set(dirty.value);
  next.add(page);
  dirty.value = next;
}
function save() {
  const labels: Record<number, string | null> = {};
  for (const page of dirty.value) labels[page] = draft.value[page]?.trim() || null;
  emit("save", labels);
}
function previous() {
  offset.value = Math.max(0, offset.value - pageSize);
}
function next() {
  if (offset.value + pageSize < props.pages.length) offset.value += pageSize;
}
</script>

<template>
  <section class="page-label-editor" :aria-label="i18n.t('pdf_corpus.page_mapping')">
    <header class="editor-head">
      <div>
        <b>{{ i18n.t("pdf_corpus.page_mapping") }}</b>
        <p>{{ i18n.t("pdf_corpus.page_mapping_help") }}</p>
        <span class="range" aria-live="polite"
          >{{ rangeStart }}–{{ rangeEnd }} / {{ props.pages.length }}</span
        >
      </div>
      <button
        type="button"
        class="btn small"
        :disabled="disabled || dirty.size === 0"
        @click="save"
      >
        {{ i18n.tf("pdf_corpus.save_page_overrides", { count: dirty.size }) }}
      </button>
    </header>
    <div
      class="page-table"
      role="table"
      :aria-label="i18n.t('pdf_corpus.page_mapping')"
      :aria-rowcount="props.pages.length + 1"
    >
      <div class="page-row page-head" role="row">
        <span role="columnheader">{{ i18n.t("pdf_corpus.physical_pdf_page") }}</span
        ><span role="columnheader">{{ i18n.t("pdf_corpus.printed_label") }}</span
        ><span role="columnheader">{{ i18n.t("pdf_corpus.label_source") }}</span>
      </div>
      <div
        v-for="page in visible"
        :key="page.pdf_page"
        class="page-row"
        :class="{ dirty: dirty.has(page.pdf_page) }"
        role="row"
        :aria-selected="dirty.has(page.pdf_page) ? 'true' : undefined"
      >
        <span role="cell">{{ page.pdf_page }}</span>
        <span role="cell">
          <label :for="`pdf-label-${page.pdf_page}`" class="sr-only">{{
            i18n.tf("pdf_corpus.printed_label_for_page", { page: page.pdf_page })
          }}</label>
          <input
            :id="`pdf-label-${page.pdf_page}`"
            class="control compact"
            type="text"
            autocomplete="off"
            maxlength="32"
            :value="draft[page.pdf_page] || ''"
            :disabled="disabled"
            :aria-label="i18n.tf('pdf_corpus.printed_page_value', { page: page.pdf_page })"
            @input="update(page.pdf_page, ($event.target as HTMLInputElement).value)"
          />
        </span>
        <span role="cell"
          ><span class="source-pill">{{
            page.printed_page_label_source || i18n.t("pdf_corpus.unknown")
          }}</span></span
        >
      </div>
    </div>
    <footer>
      <button type="button" class="btn small" @click="previous" :disabled="offset === 0">
        {{ i18n.t("ui.previous") }}</button
      ><span>{{ pageNumber }} / {{ pageCount }}</span
      ><button
        type="button"
        class="btn small"
        @click="next"
        :disabled="offset + pageSize >= pages.length"
      >
        {{ i18n.t("ui.next") }}
      </button>
    </footer>
  </section>
</template>

<style scoped>
.page-label-editor {
  display: grid;
  gap: 9px;
  padding: 10px 0;
}
.editor-head {
  align-items: center;
}
.range {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 0.75rem;
}
.page-label-editor > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.page-label-editor b {
  font-size: 0.8125rem;
}
.page-label-editor p {
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.4;
  max-width: 720px;
}
.page-table {
  border: 1px solid var(--line);
  border-radius: 9px;
  max-height: min(46vh, 430px);
  overflow: auto;
}
.page-row {
  display: grid;
  grid-template-columns: 140px minmax(120px, 1fr) minmax(120px, 1fr);
  gap: 10px;
  align-items: center;
  padding: 5px 8px;
  border-bottom: 1px solid var(--line);
  font-size: 0.8125rem;
}
.page-row:last-child {
  border-bottom: 0;
}
.page-head {
  position: sticky;
  z-index: 1;
  top: 0;
  background: var(--soft);
  font-weight: 800;
}
.page-row:not(.page-head):has(input:focus-within) {
  background: color-mix(in srgb, var(--accent) 8%, var(--card));
}
.page-row.dirty input {
  border-color: var(--accent);
}
.compact {
  min-height: 30px;
  padding: 5px 7px;
}
.source-pill {
  display: inline-block;
  padding: 2px 6px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 0.8125rem;
}
.page-label-editor > footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  align-items: center;
  font-size: 0.8125rem;
  color: var(--muted);
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.control:focus-visible,
.btn:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 650px) {
  .page-row {
    grid-template-columns: 70px 1fr;
  }
  .page-row > *:last-child {
    grid-column: 2;
  }
  .page-label-editor > header {
    flex-direction: column;
  }
}
.page-row > [role="cell"]:has(> input) {
  min-width: 0;
}
.page-row > [role="cell"] > input {
  width: 100%;
}
</style>
