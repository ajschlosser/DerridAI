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
import { nextTick, ref, watch } from "vue";
import UiLoadingState from "../ui/UiLoadingState.vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";
import type { ResponseFaqRecord } from "../../types/research";
import ResponseFaqList from "./ResponseFaqList.vue";

const props = withDefaults(
  defineProps<{
    open?: boolean;
    records?: ResponseFaqRecord[];
    selectedId?: string;
    search?: string;
    loading?: boolean;
    ready?: boolean;
    error?: string;
    count?: number;
    total?: number;
    page?: number;
    pages?: number;
  }>(),
  {
    open: false,
    records: () => [],
    selectedId: "",
    search: "",
    loading: false,
    ready: true,
    error: "",
    count: 0,
    total: 0,
    page: 1,
    pages: 1,
  },
);
const emit = defineEmits<{
  close: [];
  select: [record: ResponseFaqRecord];
  search: [value: string];
  page: [delta: number];
  retry: [];
}>();
const i18n = useI18nStore();
const dialog = ref<HTMLDialogElement | null>(null);
const searchInput = ref<HTMLInputElement | null>(null);

watch(
  () => props.open,
  async (value) => {
    await nextTick();
    const element = dialog.value;
    if (!element) return;
    if (value && !element.open) {
      element.showModal();
      await nextTick();
      searchInput.value?.focus();
    } else if (!value && element.open) element.close();
  },
  { immediate: true },
);

function requestClose() {
  emit("close");
}
function onNativeClose() {
  if (props.open) emit("close");
}
function onSearchInput(event: Event) {
  emit("search", (event.target as HTMLInputElement)?.value || "");
}
function choose(record: ResponseFaqRecord) {
  emit("select", record);
}
</script>

<template>
  <dialog
    ref="dialog"
    class="response-archive-dialog"
    aria-labelledby="responseArchiveTitle"
    @cancel.prevent="requestClose"
    @close="onNativeClose"
  >
    <div class="response-archive-shell">
      <header class="response-archive-head">
        <div>
          <span class="section-label">{{ i18n.t("faq.library_kicker") }}</span>
          <h2 id="responseArchiveTitle">{{ i18n.t("faq.library_title") }}</h2>
          <p>
            {{ i18n.t("faq.archive_help") }}
          </p>
        </div>
        <button
          type="button"
          class="response-archive-close"
          :aria-label="i18n.t('ui.close')"
          @click="requestClose"
        >
          ×
        </button>
      </header>

      <div class="response-archive-toolbar">
        <label class="response-archive-search">
          <span class="sr-only">{{ i18n.t("faq.search_label") }}</span>
          <AppIcon name="search" aria-hidden="true" />
          <input
            ref="searchInput"
            :value="search"
            type="search"
            autocomplete="off"
            :placeholder="i18n.t('faq.search_placeholder')"
            @input="onSearchInput"
          />
          <span v-if="loading" class="spinner" aria-hidden="true"></span>
        </label>
      </div>

      <div class="response-archive-index-head">
        <div>
          <strong>{{ i18n.t("faq.questions_label") }}</strong
          ><span>{{ i18n.t("faq.questions_help") }}</span>
        </div>
        <div v-if="ready" class="response-archive-count">
          <strong>{{ (search ? count : total).toLocaleString(i18n.locale) }}</strong
          ><span>{{
            search ? i18n.t("faq.question_matches") : i18n.t("faq.saved_questions")
          }}</span>
        </div>
      </div>

      <div class="response-archive-body" :aria-busy="loading">
        <div v-if="error" class="response-archive-empty" role="alert">
          <p>{{ i18n.tf(ready ? "faq.refresh_failed" : "faq.read_failed", { message: error }) }}</p>
          <button type="button" :disabled="loading" @click="emit('retry')">
            {{ i18n.t("ui.retry") }}
          </button>
        </div>
        <UiLoadingState
          v-else-if="loading"
          :variant="ready ? 'inline' : 'skeleton'"
          :label="i18n.t(ready ? 'loading.updating' : 'faq.loading')"
        />
        <div
          v-if="ready && search && !records.length && !loading && !error"
          class="response-archive-empty"
          role="status"
        >
          <AppIcon name="search" />
          <strong>{{ i18n.t("faq.no_matches") }}</strong>
          <p>{{ i18n.t("faq.no_matches_help") }}</p>
          <button type="button" @click="emit('search', '')">
            {{ i18n.t("ui.clear") }}
          </button>
        </div>
        <ResponseFaqList
          v-else-if="ready"
          :records="records"
          :selected-id="selectedId"
          :search="search"
          @select="choose"
        />
      </div>

      <footer v-if="records.length" class="response-archive-footer">
        <button type="button" :disabled="page <= 1 || loading" @click="emit('page', -1)">
          ← {{ i18n.t("ui.previous") }}
        </button>
        <span>{{ i18n.tf("faq.page_of", { page, pages }) }}</span>
        <button type="button" :disabled="page >= pages || loading" @click="emit('page', 1)">
          {{ i18n.t("ui.next") }} →
        </button>
      </footer>
    </div>
  </dialog>
</template>

<style scoped>
.response-archive-dialog {
  width: min(780px, calc(100vw - 28px));
  height: min(820px, calc(100dvh - 28px));
  max-width: none;
  max-height: none;
  margin: auto;
  padding: 0;
  border: 0;
  border-radius: 18px;
  background: var(--card);
  box-shadow: 0 28px 90px rgba(15, 23, 42, 0.28);
  overflow: hidden;
}
.response-archive-dialog::backdrop {
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(4px);
}
.response-archive-shell {
  height: 100%;
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr) auto;
}
.response-archive-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 22px 16px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, var(--card), var(--card));
}
.response-archive-head h2 {
  margin: 3px 0 4px;
  color: var(--text);
  font-size: 1.375rem;
  line-height: 1.15;
  letter-spacing: -0.015em;
}
.response-archive-head p {
  max-width: 610px;
  margin: 0;
  color: var(--muted);
  font-size: 0.78125rem;
  line-height: 1.5;
}
.response-archive-close {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  color: var(--text-2);
  font-size: 1.3125rem;
  cursor: pointer;
}
.response-archive-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 9px;
  padding: 13px 16px 10px;
}
.response-archive-search {
  min-height: 44px;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 0 11px;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  background: var(--card);
}
.response-archive-search:focus-within {
  border-color: var(--ui-accent);
  box-shadow: 0 0 0 3px var(--ui-accent-focus);
}
.response-archive-search svg {
  width: 16px;
  height: 16px;
  color: var(--muted);
}
.response-archive-search input {
  min-width: 0;
  width: 100%;
  border: 0 !important;
  outline: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
  padding: 0 !important;
  font-size: 0.875rem;
}
.response-archive-search .spinner {
  width: 14px;
  height: 14px;
}
.response-archive-index-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 18px 10px;
  border-bottom: 1px solid var(--line);
}
.response-archive-index-head > div:first-child {
  display: grid;
  gap: 2px;
}
.response-archive-index-head > div:first-child strong {
  color: var(--text-2);
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.response-archive-index-head > div:first-child span {
  color: var(--muted);
  font-size: 0.8125rem;
}
.response-archive-count {
  display: flex;
  align-items: baseline;
  gap: 5px;
  color: var(--muted);
  font-size: 0.8125rem;
  white-space: nowrap;
}
.response-archive-count strong {
  color: var(--text-2);
  font-size: 0.78125rem;
}
.response-archive-body {
  min-height: 0;
  overflow: auto;
  padding: 8px 9px 10px;
  scrollbar-gutter: stable;
  background: var(--card);
}
.response-archive-empty {
  min-height: 300px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 7px;
  padding: 24px;
  text-align: center;
}
.response-archive-empty > svg {
  width: 25px;
  height: 25px;
  color: var(--muted);
}
.response-archive-empty strong {
  color: var(--text-2);
  font-size: 0.84375rem;
}
.response-archive-empty p {
  max-width: 330px;
  margin: 0;
  color: var(--muted);
  font-size: 0.78125rem;
  line-height: 1.5;
}
.response-archive-empty button {
  min-height: 36px;
  border: 0;
  background: transparent;
  color: var(--accent-fg);
  font-weight: 800;
  cursor: pointer;
}
.response-archive-footer {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-top: 1px solid var(--line);
  background: var(--card);
}
.response-archive-footer span {
  text-align: center;
  color: var(--muted);
  font-size: 0.8125rem;
}
.response-archive-footer button {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--card);
  padding: 0 10px;
  color: var(--text-2);
  font-weight: 750;
  cursor: pointer;
}
.response-archive-footer button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.response-archive-dialog :is(button, input):focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 2px;
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
@media (max-width: 600px) {
  .response-archive-dialog {
    width: calc(100vw - 10px);
    height: calc(100dvh - 10px);
    border-radius: 13px;
  }
  .response-archive-head {
    padding: 16px;
  }
  .response-archive-toolbar {
    grid-template-columns: 1fr;
    padding-inline: 11px;
  }
  .response-archive-index-head {
    align-items: flex-start;
  }
  .response-archive-index-head > div:first-child span {
    display: none;
  }
  .response-archive-footer {
    grid-template-columns: 1fr 1fr;
  }
  .response-archive-footer span {
    grid-column: 1/-1;
    grid-row: 1;
  }
  .response-archive-footer button {
    grid-row: 2;
  }
}
@media (prefers-reduced-motion: reduce) {
  .response-archive-dialog::backdrop {
    backdrop-filter: none;
  }
}
</style>
