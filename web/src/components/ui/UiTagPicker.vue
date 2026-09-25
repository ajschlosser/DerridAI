<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue: string[];
    options: string[];
    label: string;
    placeholder?: string;
    disabled?: boolean;
  }>(),
  {
    placeholder: "",
    disabled: false,
  },
);
const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();
const id = useId();
const query = ref("");
const open = ref(false);
const active = ref(-1);
const input = ref<HTMLInputElement | null>(null);

const selected = computed(() => new Set(props.modelValue.map((value) => value.toLocaleUpperCase())));
const filtered = computed(() => {
  const needle = query.value.trim().toLocaleUpperCase();
  return props.options
    .filter((option) => !selected.value.has(option.toLocaleUpperCase()))
    .filter((option) => !needle || option.toLocaleUpperCase().includes(needle))
    .slice(0, 40);
});

function commit(value: string) {
  const option = props.options.find((item) => item.toLocaleUpperCase() === value.toLocaleUpperCase());
  if (!option || selected.value.has(option.toLocaleUpperCase())) return;
  emit("update:modelValue", [...props.modelValue, option]);
  query.value = "";
  active.value = -1;
  open.value = true;
  void nextTick(() => input.value?.focus());
}

function remove(value: string) {
  emit("update:modelValue", props.modelValue.filter((item) => item !== value));
}

function scheduleClose() {
  window.setTimeout(() => {
    open.value = false;
    active.value = -1;
  }, 120);
}

function keydown(event: KeyboardEvent) {
  if (event.key === "ArrowDown") {
    event.preventDefault();
    open.value = true;
    active.value = Math.min(filtered.value.length - 1, active.value + 1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    open.value = true;
    active.value = Math.max(0, active.value - 1);
  } else if (event.key === "Enter") {
    const candidate = active.value >= 0 ? filtered.value[active.value] : filtered.value[0];
    if (candidate) {
      event.preventDefault();
      commit(candidate);
    }
  } else if (event.key === "Escape") {
    open.value = false;
    active.value = -1;
  } else if (event.key === "Backspace" && !query.value && props.modelValue.length) {
    remove(props.modelValue.at(-1) || "");
  }
}
</script>

<template>
  <div class="ui-tag-picker">
    <div class="tag-shell" :data-disabled="disabled ? 'true' : 'false'">
      <span v-for="value in modelValue" :key="value" class="tag-chip">
        <span>{{ value }}</span>
        <button
          type="button"
          :disabled="disabled"
          :aria-label="`Remove ${value}`"
          @click="remove(value)"
        >
          ×
        </button>
      </span>
      <input
        ref="input"
        v-model="query"
        type="text"
        role="combobox"
        :aria-label="label"
        aria-autocomplete="list"
        :aria-expanded="open && filtered.length > 0"
        :aria-controls="`${id}-listbox`"
        :placeholder="modelValue.length ? '' : placeholder"
        :disabled="disabled"
        @focus="open = true"
        @input="
          open = true;
          active = -1;
        "
        @keydown="keydown"
        @blur="scheduleClose"
      />
    </div>
    <ul
      v-if="open && filtered.length"
      :id="`${id}-listbox`"
      class="tag-options"
      role="listbox"
    >
      <li
        v-for="(option, index) in filtered"
        :key="option"
        role="option"
        :aria-selected="false"
        :data-active="index === active ? 'true' : 'false'"
        @mousedown.prevent="commit(option)"
      >
        {{ option }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.ui-tag-picker {
  position: relative;
  min-width: 0;
}
.tag-shell {
  min-height: var(--control-height);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 5px 8px;
  border: 1px solid var(--border-control, var(--line));
  border-radius: var(--radius-control);
  background: var(--surface-control, var(--card));
}
.tag-shell:focus-within {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.tag-shell[data-disabled="true"] {
  opacity: 0.65;
}
.tag-shell input {
  flex: 1 1 9rem;
  min-width: 7rem;
  min-height: 28px;
  border: 0;
  outline: 0;
  background: transparent;
  color: inherit;
  font: inherit;
}
.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  min-height: 26px;
  padding-inline-start: 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--soft);
  font-size: 0.78rem;
  font-weight: 700;
}
.tag-chip button {
  width: 26px;
  height: 26px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  border-radius: 50%;
}
.tag-chip button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: -2px;
}
.tag-options {
  position: absolute;
  z-index: 40;
  inset-inline: 0;
  top: calc(100% + 4px);
  max-height: 240px;
  overflow: auto;
  margin: 0;
  padding: 4px;
  list-style: none;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-overlay);
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
}
.tag-options li {
  padding: 8px 10px;
  border-radius: var(--radius-control);
  cursor: pointer;
  font-size: 0.84rem;
}
.tag-options li:hover,
.tag-options li[data-active="true"] {
  background: var(--surface-hover);
}
</style>
