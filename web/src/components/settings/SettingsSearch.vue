<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import type { SettingsSectionId } from "../../domain/settings";

export interface SettingsSearchHit {
  id: string;
  section: SettingsSectionId;
  label: string;
  group: string;
}

const props = defineProps<{
  modelValue: string;
  results: SettingsSearchHit[];
  label: string;
  placeholder: string;
  describedBy?: string;
  noResults: string;
  resultCount: string;
}>();
const emit = defineEmits<{"update:modelValue": [string]; choose: [SettingsSearchHit]}>();
const listId = "settings-search-results";
const activeIndex = ref(-1);
const input = ref<HTMLInputElement | null>(null);
const open = computed(() => Boolean(props.modelValue.trim()));

function onKey(event: KeyboardEvent) {
  if (event.key === "Escape") {
    emit("update:modelValue", "");
    activeIndex.value = -1;
    return;
  }
  if (!open.value || !props.results.length) return;
  if (event.key === "ArrowDown") {
    event.preventDefault();
    activeIndex.value = (activeIndex.value + 1) % props.results.length;
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    activeIndex.value = activeIndex.value <= 0 ? props.results.length - 1 : activeIndex.value - 1;
  } else if (event.key === "Enter" && activeIndex.value >= 0) {
    event.preventDefault();
    emit("choose", props.results[activeIndex.value]);
  }
}
function choose(item: SettingsSearchHit) {
  emit("choose", item);
  void nextTick(() => input.value?.focus());
}
</script>
<template>
  <div class="settings-search">
    <label class="settings-search-label" for="settings-search-input">{{ label }}</label>
    <input
      id="settings-search-input"
      ref="input"
      class="control settings-search-input"
      :value="modelValue"
      :placeholder="placeholder"
      :aria-describedby="describedBy"
      role="combobox"
      :aria-expanded="open ? 'true' : 'false'"
      aria-autocomplete="list"
      :aria-controls="listId"
      :aria-activedescendant="activeIndex >= 0 ? `settings-search-option-${activeIndex}` : undefined"
      autocomplete="off"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value); activeIndex = props.results.length ? 0 : -1"
      @keydown="onKey"
    >
    <p v-if="open" id="settings-search-count" class="settings-search-count">{{ resultCount }}</p>
    <ul v-if="open" :id="listId" class="settings-search-list" role="listbox" :aria-label="label">
      <li v-if="!results.length" class="settings-search-empty" role="presentation">{{ noResults }}</li>
      <li
        v-for="(item, index) in results"
        :id="`settings-search-option-${index}`"
        :key="item.id"
        role="option"
        :aria-selected="index === activeIndex"
        :class="{active: index === activeIndex}"
        @mousedown.prevent="choose(item)"
      >
        <b>{{ item.label }}</b>
        <small>{{ item.group }}</small>
      </li>
    </ul>
  </div>
</template>
<style scoped>
.settings-search{display:grid;gap:6px;min-width:0}
.settings-search-label{font-size:.8125rem;font-weight:700}
.settings-search-input{width:100%}
.settings-search-count{margin:0;color:var(--muted);font-size:.8125rem}
.settings-search-list{list-style:none;margin:0;padding:6px;border:1px solid var(--line);border-radius:12px;background:var(--surface-overlay);max-height:240px;overflow:auto}
.settings-search-list li[role=option]{width:100%;min-height:40px;display:flex;justify-content:space-between;gap:12px;align-items:center;padding:8px 10px;border:0;border-radius:8px;background:transparent;text-align:left;cursor:pointer}
.settings-search-list li.active,.settings-search-list li[role=option]:hover{background:var(--accent-soft)}
.settings-search-list b{font-size:.875rem}
.settings-search-list small{color:var(--muted);font-size:.8125rem;text-transform:uppercase;letter-spacing:.04em}
.settings-search-empty{padding:10px;color:var(--muted);font-size:.875rem}
</style>
