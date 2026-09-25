<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import type { SettingsSectionId } from "../../domain/settings";

const props = defineProps<{
  modelValue: SettingsSectionId;
  items: Array<{ id: SettingsSectionId; label: string }>;
  tablistLabel: string;
}>();
const emit = defineEmits<{
  "update:modelValue": [SettingsSectionId];
  select: [SettingsSectionId];
}>();
const root = ref<HTMLElement | null>(null);
const activeId = computed(() =>
  props.items.some((item) => item.id === props.modelValue)
    ? props.modelValue
    : props.items[0]?.id || "workspace",
);

function select(id: SettingsSectionId) {
  emit("update:modelValue", id);
  emit("select", id);
}
function onKey(event: KeyboardEvent, index: number) {
  if (!props.items.length) return;
  const last = props.items.length - 1;
  let next = index;
  if (event.key === "ArrowDown" || event.key === "ArrowRight")
    next = index === last ? 0 : index + 1;
  else if (event.key === "ArrowUp" || event.key === "ArrowLeft")
    next = index === 0 ? last : index - 1;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = last;
  else return;
  event.preventDefault();
  select(props.items[next].id);
  void nextTick(() => root.value?.querySelectorAll<HTMLButtonElement>("[role=tab]")[next]?.focus());
}
</script>
<template>
  <nav ref="root" class="settings-nav" :aria-label="tablistLabel">
    <div class="settings-nav-list" role="tablist" aria-orientation="vertical">
      <button
        v-for="(item, index) in items"
        :id="`settings-nav-${item.id}`"
        :key="item.id"
        type="button"
        role="tab"
        class="settings-nav-item"
        :aria-selected="item.id === activeId"
        :aria-controls="`settings-section-${item.id}`"
        :tabindex="item.id === activeId ? 0 : -1"
        @click="select(item.id)"
        @keydown="onKey($event, index)"
      >
        {{ item.label }}
      </button>
    </div>
  </nav>
</template>
<style scoped>
.settings-nav {
  min-width: 0;
}
.settings-nav-list {
  display: grid;
  gap: 4px;
}
.settings-nav-item {
  min-height: 40px;
  width: 100%;
  display: flex;
  align-items: flex-start;
  text-align: left;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  font-size: 0.875rem;
  font-weight: 700;
  line-height: 1.35;
}
.settings-nav-item[aria-selected="true"] {
  background: var(--accent-soft);
  border-color: var(--line-strong);
  color: var(--accent-fg);
  box-shadow: inset 3px 0 0 var(--accent);
}
.settings-nav-item:hover:not([aria-selected="true"]) {
  background: var(--panel-2);
  color: var(--text);
}
.settings-nav-item:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
@media (forced-colors: active) {
  .settings-nav-item[aria-selected="true"] {
    outline: 2px solid CanvasText;
  }
}
</style>
