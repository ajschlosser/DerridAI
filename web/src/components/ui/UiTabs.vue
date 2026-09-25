<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    tabs: { id: string; label: string }[];
    modelValue: string;
    tablistLabel: string;
    idPrefix?: string;
  }>(),
  { idPrefix: "ui" },
);
const emit = defineEmits<{ "update:modelValue": [string] }>();
const root = ref<HTMLElement | null>(null);
const activeId = computed(() =>
  props.tabs.some((tab) => tab.id === props.modelValue)
    ? props.modelValue
    : props.tabs[0]?.id || "",
);

function select(id: string) {
  emit("update:modelValue", id);
}
function onKey(event: KeyboardEvent, index: number) {
  if (!props.tabs.length) return;
  const last = props.tabs.length - 1;
  let next = index;
  if (event.key === "ArrowRight" || event.key === "ArrowDown")
    next = index === last ? 0 : index + 1;
  else if (event.key === "ArrowLeft" || event.key === "ArrowUp")
    next = index === 0 ? last : index - 1;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = last;
  else return;
  event.preventDefault();
  select(props.tabs[next].id);
  void nextTick(() => {
    const buttons = root.value?.querySelectorAll<HTMLButtonElement>("[role=tab]");
    buttons?.[next]?.focus();
  });
}
watch(activeId, (id) => {
  if (id && id !== props.modelValue) emit("update:modelValue", id);
});
</script>
<template>
  <div ref="root" class="ui-tabs" role="tablist" :aria-label="props.tablistLabel">
    <button
      v-for="(tab, index) in props.tabs"
      :id="`${props.idPrefix}-tab-${tab.id}`"
      :key="tab.id"
      type="button"
      class="ui-tab"
      role="tab"
      :aria-selected="tab.id === activeId"
      :aria-controls="`${props.idPrefix}-panel-${tab.id}`"
      :tabindex="tab.id === activeId ? 0 : -1"
      @click="select(tab.id)"
      @keydown="onKey($event, index)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
<style scoped>
.ui-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border-subtle);
  overflow-x: auto;
}
.ui-tab {
  min-height: var(--control-height);
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  padding: 8px 12px;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: 750;
  cursor: pointer;
}
.ui-tab:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}
.ui-tab[aria-selected="true"] {
  color: var(--accent-fg);
  border-bottom-color: var(--accent);
}
.ui-tab:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring, var(--accent));
  outline-offset: var(--focus-ring-offset);
}
</style>
