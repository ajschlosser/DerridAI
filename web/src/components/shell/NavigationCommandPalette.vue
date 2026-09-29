<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import type { SidebarNavGroup } from "./sidebarNav";

const props = defineProps<{ groups: SidebarNavGroup[] }>();
const emit = defineEmits<{ navigate: [string]; search: [string] }>();
const i18n = useI18nStore();
const dialog = ref<HTMLDialogElement | null>(null);
const input = ref<HTMLInputElement | null>(null);
const query = ref("");

const matches = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase();
  const rows = props.groups.flatMap((group) =>
    group.items.map((item) => ({ ...item, section: group.section })),
  );
  if (!needle) return rows.slice(0, 12);
  return rows
    .filter((item) =>
      `${item.section} ${item.label}`.toLocaleLowerCase().includes(needle),
    )
    .slice(0, 12);
});

function open() {
  query.value = "";
  if (dialog.value && !dialog.value.open) dialog.value.showModal();
  void nextTick(() => input.value?.focus());
}
function close() {
  dialog.value?.close();
}
function navigate(id: string) {
  close();
  emit("navigate", id);
}
function search() {
  const value = query.value.trim();
  if (!value) return;
  close();
  emit("search", value);
}
function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter") return;
  if (matches.value.length) {
    event.preventDefault();
    navigate(matches.value[0].id);
  } else if (query.value.trim()) {
    event.preventDefault();
    search();
  }
}
defineExpose({ open, close });
</script>

<template>
  <dialog
    ref="dialog"
    class="navigation-command-dialog"
    :aria-label="i18n.t('nav.command_palette')"
    @cancel.prevent="close"
  >
    <div class="navigation-command-shell">
      <label class="navigation-command-input">
        <AppIcon name="search" aria-hidden="true" />
        <span class="sr-only">{{ i18n.t("nav.command_placeholder") }}</span>
        <input
          ref="input"
          v-model="query"
          type="search"
          autocomplete="off"
          :placeholder="i18n.t('nav.command_placeholder')"
          @keydown="onKeydown"
        />
        <kbd>Esc</kbd>
      </label>
      <div class="navigation-command-results">
        <button
          v-for="item in matches"
          :key="item.id"
          type="button"
           @click="navigate(item.id)"
        >
          <AppIcon :name="item.icon" aria-hidden="true" />
          <span>
            <b>{{ item.label }}</b>
            <small>{{ item.section }}</small>
          </span>
        </button>
        <button
          v-if="query.trim()"
          type="button"
          class="navigation-command-search"
          @click="search"
        >
          <AppIcon name="search" aria-hidden="true" />
          <span>
            <b>{{ i18n.tf("nav.search_corpus_for", { query: query.trim() }) }}</b>
            <small>{{ i18n.t("section.research") }}</small>
          </span>
        </button>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.navigation-command-dialog {
  width: min(620px, calc(100vw - 32px));
  max-height: min(620px, calc(100vh - 48px));
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--overlay, var(--card));
  color: var(--text);
  box-shadow: var(--shadow-lg, 0 18px 60px color-mix(in srgb, currentColor 18%, transparent));
}
.navigation-command-dialog::backdrop {
  background: color-mix(in srgb, var(--text) 28%, transparent);
}
.navigation-command-shell {
  display: grid;
}
.navigation-command-input {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
}
.navigation-command-input :deep(svg) {
  width: 20px;
  height: 20px;
  color: var(--muted);
}
.navigation-command-input input {
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 1rem;
}
.navigation-command-input kbd {
  color: var(--muted);
  font-size: 0.75rem;
}
.navigation-command-results {
  display: grid;
  gap: 2px;
  max-height: 480px;
  overflow: auto;
  padding: 8px;
}
.navigation-command-results button {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.navigation-command-results button:hover,
.navigation-command-results button:focus-visible {
  background: var(--soft);
}
.navigation-command-results :deep(svg) {
  width: 18px;
  height: 18px;
  color: var(--muted);
}
.navigation-command-results span {
  display: grid;
  gap: 2px;
}
.navigation-command-results b {
  font-size: 0.875rem;
}
.navigation-command-results small {
  color: var(--muted);
  font-size: 0.75rem;
}
.navigation-command-search {
  border-top: 1px solid var(--line) !important;
  border-radius: 0 0 8px 8px !important;
}
</style>
