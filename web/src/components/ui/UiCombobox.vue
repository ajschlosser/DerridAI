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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
const props = withDefaults(
  defineProps<{
    modelValue: string;
    options?: string[];
    label: string;
    placeholder?: string;
    disabled?: boolean;
    allowCustom?: boolean;
    multiple?: boolean;
    type?: "text" | "number";
    /** Render a wrapping, auto-growing text box instead of a one-line input (long strings stay readable). */
    multiline?: boolean;
    /** Shown on a multi-select option that is already in the list; clicking it removes it. */
    selectedLabel?: string;
    /** Values the model proposed: listed first and marked, in words as well as colour. */
    recommended?: string[];
    recommendedLabel?: string;
  }>(),
  {
    options: () => [],
    placeholder: "",
    disabled: false,
    allowCustom: true,
    multiple: false,
    type: "text",
    multiline: false,
    selectedLabel: "Selected",
    recommended: () => [],
    recommendedLabel: "Suggested",
  },
);
const emit = defineEmits<{ "update:modelValue": [value: string]; change: [value: string] }>();
const comboId = useId();
const open = ref(false);
const active = ref(-1);
const input = ref<HTMLInputElement | HTMLTextAreaElement | null>(null);
const popup = ref({ left: 0, top: 0, width: 320, maxHeight: 240 });
const unique = computed(() =>
  Array.from(new Set(props.options.map((v) => String(v).trim()).filter(Boolean))),
);
const currentValues = computed(
  () =>
    new Set(
      String(props.modelValue || "")
        .split(/[\n,]/)
        .map((v) => v.trim())
        .filter(Boolean)
        .map((v) => v.toLocaleLowerCase()),
    ),
);
// Suggested values are matched case-insensitively so "Derrida" and "derrida" are one suggestion.
const recommendedSet = computed(
  () => new Set(props.recommended.map((v) => String(v).trim().toLocaleLowerCase()).filter(Boolean)),
);
const isRecommended = (value: string) => recommendedSet.value.has(value.toLocaleLowerCase());
/** In multi-select mode the text after the last comma is what is being typed, unless it is already a whole entry. */
const pendingQuery = computed(() => {
  const raw = String(props.modelValue || "");
  if (!props.multiple) return raw.trim().toLocaleLowerCase();
  const last = (raw.split(/[\n,]/).at(-1) || "").trim().toLocaleLowerCase();
  return unique.value.some((v) => v.toLocaleLowerCase() === last) ? "" : last;
});
/** A single value that is the model's suggestion carries the same ★ in the field as it does in the list. */
const valueIsRecommended = computed(
  () =>
    !props.multiple && Boolean(pendingQuery.value) && recommendedSet.value.has(pendingQuery.value),
);
const isSelected = (value: string) =>
  props.multiple && currentValues.value.has(value.toLocaleLowerCase());
const filtered = computed(() => {
  const q = pendingQuery.value;
  const matches = unique.value.filter((v) => {
    const lower = v.toLocaleLowerCase();
    return !q || lower.includes(q) || (!props.multiple && q.includes(lower));
  });
  // The model's proposal leads the list (stable, so the rest keep their order) and is never cut by the cap.
  return [...matches.filter(isRecommended), ...matches.filter((v) => !isRecommended(v))].slice(
    0,
    60,
  );
});
watch(
  () => props.modelValue,
  () => {
    active.value = -1;
  },
);
watch(open, (value) => {
  if (value) void nextTick(positionPopup);
});
/**
 * Toggle ``value`` in a comma-separated list: present values are removed, absent ones added.
 * Text still being typed after the last comma is dropped, since choosing an option finishes it.
 */
function toggleValue(current: string, value: string) {
  const raw = String(current || "");
  const parts = raw.split(/[\n,]/).map((v) => v.trim());
  const last = (parts.at(-1) || "").toLocaleLowerCase();
  // A trailing token only counts as a finished entry when it is one of the known options.
  const lastIsWhole = unique.value.some((v) => v.toLocaleLowerCase() === last);
  const entries = (lastIsWhole || !last ? parts : parts.slice(0, -1)).filter(Boolean);
  const target = value.trim();
  const present = entries.some((v) => v.toLocaleLowerCase() === target.toLocaleLowerCase());
  const next = present
    ? entries.filter((v) => v.toLocaleLowerCase() !== target.toLocaleLowerCase())
    : [...new Set([...entries, target].filter(Boolean))];
  return next.join(", ");
}
function positionPopup() {
  const el = input.value;
  if (!el) return;
  const rect = el.getBoundingClientRect();
  const margin = 8;
  const viewportWidth = Math.max(320, window.innerWidth);
  const below = window.innerHeight - rect.bottom;
  const above = rect.top;
  const maxHeight = Math.max(120, Math.min(320, (below >= 180 ? below : above) - 16));
  const width = Math.min(Math.max(rect.width, 240), viewportWidth - margin * 2);
  const left = Math.min(
    Math.max(margin, rect.left),
    Math.max(margin, viewportWidth - width - margin),
  );
  popup.value = {
    left,
    top: below >= 180 ? rect.bottom + 4 : Math.max(margin, rect.top - maxHeight - 4),
    width,
    maxHeight,
  };
}
function commit(value: string) {
  const next = props.multiple ? toggleValue(props.modelValue, value) : value;
  emit("update:modelValue", next);
  emit("change", next);
  // A multi-select stays open so several values can be added or removed in one go.
  if (!props.multiple) {
    open.value = false;
    active.value = -1;
  }
  void nextTick(() => {
    input.value?.focus();
    grow();
  });
}
/** Size a multiline box to its content so a long value is fully visible without scrolling. */
function grow() {
  const el = input.value;
  if (!props.multiline || !el || !("style" in el)) return;
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}
function onInput(event: Event) {
  emit("update:modelValue", (event.target as HTMLInputElement | HTMLTextAreaElement).value);
  open.value = true;
  positionPopup();
  grow();
}
function keydown(event: KeyboardEvent) {
  if (event.key === "ArrowDown") {
    event.preventDefault();
    open.value = true;
    positionPopup();
    active.value = Math.min(filtered.value.length - 1, active.value + 1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    open.value = true;
    positionPopup();
    active.value = Math.max(0, active.value - 1);
  } else if (event.key === "Enter" && open.value && active.value >= 0) {
    event.preventDefault();
    commit(filtered.value[active.value]);
  } else if (
    event.key === "Enter" &&
    props.multiline &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.shiftKey
  ) {
    // Wrapping is visual only; metadata values never contain a hard line break from Enter.
    event.preventDefault();
  } else if (event.key === "Escape") {
    open.value = false;
    active.value = -1;
  }
}
function blur() {
  window.setTimeout(() => {
    open.value = false;
    active.value = -1;
  }, 150);
}
function reposition() {
  if (open.value) positionPopup();
}
watch(
  () => props.modelValue,
  () => void nextTick(grow),
);
onMounted(() => {
  grow();
  window.addEventListener("resize", reposition);
  window.addEventListener("scroll", reposition, true);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", reposition);
  window.removeEventListener("scroll", reposition, true);
});
</script>
<template>
  <div class="ui-combobox">
    <textarea
      v-if="multiline"
      ref="input"
      class="control combo-textarea"
      rows="1"
      role="combobox"
      :aria-label="label"
      aria-autocomplete="list"
      :aria-expanded="open && filtered.length > 0"
      :aria-controls="`${comboId}-listbox`"
      :aria-describedby="valueIsRecommended ? `${comboId}-recommended` : undefined"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput"
      @focus="
        open = true;
        positionPopup();
      "
      @keydown="keydown"
      @blur="blur"
    ></textarea>
    <input
      v-else
      ref="input"
      class="control"
      :type="type"
      role="combobox"
      :aria-label="label"
      aria-autocomplete="list"
      :aria-expanded="open && filtered.length > 0"
      :aria-controls="`${comboId}-listbox`"
      :aria-describedby="valueIsRecommended ? `${comboId}-recommended` : undefined"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput"
      @focus="
        open = true;
        positionPopup();
      "
      @keydown="keydown"
      @blur="blur"
    />
    <span
      v-if="valueIsRecommended"
      :id="`${comboId}-recommended`"
      class="combo-badge combo-value-badge"
      data-testid="combo-value-recommended"
      ><span aria-hidden="true">★</span> {{ recommendedLabel }}</span
    >
    <datalist :id="`${comboId}-options`">
      <option v-for="option in unique" :key="option" :value="option" />
    </datalist>
    <Teleport to="body"
      ><ul
        v-if="open && filtered.length"
        :id="`${comboId}-listbox`"
        class="combo-list"
        role="listbox"
        :aria-multiselectable="multiple ? 'true' : undefined"
        :style="{
          left: `${popup.left}px`,
          top: `${popup.top}px`,
          width: `${popup.width}px`,
          maxHeight: `${popup.maxHeight}px`,
        }"
      >
        <li
          v-for="(option, index) in filtered"
          :key="option"
          role="option"
          :aria-selected="multiple ? isSelected(option) : option === modelValue"
          :data-active="index === active ? 'true' : 'false'"
          :data-selected="isSelected(option) ? 'true' : undefined"
          :data-recommended="isRecommended(option) ? 'true' : undefined"
          @mousedown.prevent="commit(option)"
        >
          <span v-if="multiple" class="combo-check" aria-hidden="true">{{
            isSelected(option) ? "✓" : ""
          }}</span>
          <span class="combo-option-text">{{ option }}</span>
          <span v-if="isSelected(option)" class="combo-state">{{ selectedLabel }}</span>
          <span v-if="isRecommended(option)" class="combo-badge"
            ><span aria-hidden="true">★</span> {{ recommendedLabel }}</span
          >
        </li>
      </ul></Teleport
    >
  </div>
</template>
<style scoped>
.ui-combobox {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: min(320px, 100%);
  flex: 1;
}
.ui-combobox > .control {
  flex: 1;
  min-width: 0;
}
.combo-value-badge {
  white-space: nowrap;
}
.control {
  width: 100%;
  min-height: var(--control-height);
}
.combo-list {
  position: fixed;
  z-index: 2147483000;
  overflow: auto;
  margin: 0;
  padding: 4px;
  list-style: none;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-overlay);
  background: var(--surface-overlay);
  color: var(--text-primary);
  box-shadow: var(--shadow-overlay);
}
.combo-list li {
  padding: 8px 10px;
  border-radius: var(--radius-control);
  cursor: pointer;
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
.combo-list li {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.combo-list li[data-recommended="true"] {
  border-inline-start: 3px solid var(--tone-info-edge);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-weight: 650;
}
.combo-list li[data-selected="true"] {
  background: var(--surface-selected);
  font-weight: 650;
}
.combo-check {
  flex: none;
  inline-size: 1.1em;
  color: var(--ui-accent, var(--accent));
  font-weight: 800;
  text-align: center;
}
.combo-option-text {
  flex: 1;
  min-width: 0;
}
.combo-state {
  flex: none;
  color: var(--text-secondary);
  font-size: 0.75rem;
}
.combo-textarea {
  resize: none;
  overflow: hidden;
  line-height: var(--lh-normal, 1.45);
  padding-block: 8px;
}
.combo-badge {
  flex: none;
  font-size: 0.75rem;
  font-weight: 700;
}
.combo-list li:hover,
.combo-list li[data-active="true"] {
  background: var(--surface-hover);
}
.control:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
</style>
