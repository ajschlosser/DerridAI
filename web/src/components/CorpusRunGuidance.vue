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
import { computed, nextTick, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import AppIcon from "./AppIcon.vue";
import UiButton from "./ui/UiButton.vue";

export interface RunGuidanceEntry {
  instructions: string;
  look_for: string[];
  required?: boolean;
}

export interface RunGuidanceField {
  name: string;
  label: string;
  group: string;
}

type Filter = "all" | "configured" | "required";

const MAX_TERMS = 40;
const props = withDefaults(
  defineProps<{
    modelValue: Record<string, RunGuidanceEntry>;
    fields: RunGuidanceField[];
    disabled?: boolean;
  }>(),
  { disabled: false },
);
const emit = defineEmits<{ "update:modelValue": [value: Record<string, RunGuidanceEntry>] }>();
const i18n = useI18nStore();
const importInput = ref<HTMLInputElement | null>(null);
const cueInput = ref<HTMLInputElement | null>(null);
const notice = ref("");
const error = ref("");
const query = ref("");
const filter = ref<Filter>("all");
const selectedName = ref("");
const cueDraft = ref("");

function isConfigured(entry?: RunGuidanceEntry) {
  return Boolean(entry && (entry.instructions.trim() || entry.look_for.length || entry.required));
}
const configuredCount = computed(
  () => props.fields.filter((field) => isConfigured(props.modelValue[field.name])).length,
);
const requiredCount = computed(
  () => props.fields.filter((field) => props.modelValue[field.name]?.required === true).length,
);
const visibleFields = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase();
  return props.fields.filter((field) => {
    const entry = props.modelValue[field.name];
    if (filter.value === "configured" && !isConfigured(entry)) return false;
    if (filter.value === "required" && entry?.required !== true) return false;
    return (
      !needle || `${field.label} ${field.name} ${field.group}`.toLocaleLowerCase().includes(needle)
    );
  });
});
const groups = computed(() => {
  const byGroup = new Map<string, RunGuidanceField[]>();
  for (const field of visibleFields.value) {
    byGroup.set(field.group, [...(byGroup.get(field.group) || []), field]);
  }
  return [...byGroup.entries()].map(([label, items]) => ({ label, items }));
});
const selected = computed(() => props.fields.find((field) => field.name === selectedName.value));
const entry = computed<RunGuidanceEntry>(
  () =>
    props.modelValue[selectedName.value] || {
      instructions: "",
      look_for: [],
      required: false,
    },
);

watch(
  () => props.fields,
  (fields) => {
    if (!fields.some((field) => field.name === selectedName.value))
      selectedName.value = fields[0]?.name || "";
  },
  { immediate: true },
);
watch(selectedName, () => {
  cueDraft.value = "";
});

function update(field: string, patch: Partial<RunGuidanceEntry>) {
  const previous = props.modelValue[field] || {
    instructions: "",
    look_for: [],
    required: false,
  };
  emit("update:modelValue", {
    ...props.modelValue,
    [field]: { ...previous, ...patch },
  });
}

function setRequired(required: boolean) {
  update(selectedName.value, { required });
}

function addCues(raw: string) {
  const field = selectedName.value;
  const existing = props.modelValue[field]?.look_for || [];
  const seen = new Set(existing.map((term) => term.toLocaleLowerCase()));
  const next = [...existing];
  for (const part of raw.split(/[\n,;]+/)) {
    const term = part.trim();
    if (!term || seen.has(term.toLocaleLowerCase()) || next.length >= MAX_TERMS) continue;
    seen.add(term.toLocaleLowerCase());
    next.push(term);
  }
  if (next.length !== existing.length) update(field, { look_for: next });
  cueDraft.value = "";
}

function removeCue(term: string) {
  update(selectedName.value, { look_for: entry.value.look_for.filter((item) => item !== term) });
  void nextTick(() => cueInput.value?.focus());
}

function onCueKeydown(event: KeyboardEvent) {
  if (event.key === "Enter" || event.key === ",") {
    if (cueDraft.value.trim() || event.key === ",") event.preventDefault();
    addCues(cueDraft.value);
  } else if (event.key === "Backspace" && !cueDraft.value && entry.value.look_for.length) {
    update(selectedName.value, { look_for: entry.value.look_for.slice(0, -1) });
  }
}

function onCuePaste(event: ClipboardEvent) {
  const text = event.clipboardData?.getData("text") || "";
  if (!/[\n,;]/.test(text)) return;
  event.preventDefault();
  addCues(text);
}

function clearField() {
  const next = { ...props.modelValue };
  delete next[selectedName.value];
  emit("update:modelValue", next);
}

function clearAll() {
  emit("update:modelValue", {});
  notice.value = i18n.t("pdf_corpus.run_guidance_cleared", "All field guidance cleared.");
  error.value = "";
}

function openImport() {
  importInput.value?.click();
}

function exportGuidance() {
  const payload = {
    format: "derridai-run-guidance",
    version: 1,
    guidance: props.modelValue,
  };
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "derridai-run-guidance.json";
  link.click();
  URL.revokeObjectURL(url);
  error.value = "";
  notice.value = i18n.t("pdf_corpus.run_guidance_exported");
}

function normaliseImportedGuidance(payload: unknown): Record<string, RunGuidanceEntry> {
  const source =
    payload && typeof payload === "object" && !Array.isArray(payload) && "guidance" in payload
      ? (payload as { guidance?: unknown }).guidance
      : payload;
  if (!source || typeof source !== "object" || Array.isArray(source)) {
    throw new Error(i18n.t("pdf_corpus.run_guidance_import_invalid"));
  }
  const fields = new Map(props.fields.map((field) => [field.name, field]));
  const imported: Record<string, RunGuidanceEntry> = {};
  for (const [field, raw] of Object.entries(source)) {
    if (!fields.has(field) || !raw || typeof raw !== "object" || Array.isArray(raw)) continue;
    const entry = raw as {
      instructions?: unknown;
      look_for?: unknown;
      required?: unknown;
    };
    const instructions = typeof entry.instructions === "string" ? entry.instructions : "";
    const lookFor = Array.isArray(entry.look_for)
      ? entry.look_for
          .filter((term): term is string => typeof term === "string" && term.trim().length > 0)
          .slice(0, 40)
      : [];
    const required = entry.required === true;
    if (instructions.trim() || lookFor.length || required)
      imported[field] = {
        instructions,
        look_for: lookFor,
        required,
      };
  }
  if (!Object.keys(imported).length) {
    throw new Error(i18n.t("pdf_corpus.run_guidance_import_no_fields"));
  }
  return imported;
}

async function importGuidance(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  try {
    const imported = normaliseImportedGuidance(JSON.parse(await file.text()));
    emit("update:modelValue", { ...props.modelValue, ...imported });
    error.value = "";
    notice.value = i18n.t("pdf_corpus.run_guidance_imported");
  } catch (exc) {
    notice.value = "";
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}
</script>

<template>
  <section
    class="rg"
    :aria-label="i18n.t('pdf_corpus.run_guidance_title')"
    aria-describedby="run-guidance-help"
  >
    <p id="run-guidance-help" class="rg-help">
      {{ i18n.t("pdf_corpus.run_guidance_help") }}
    </p>

    <div class="rg-toolbar">
      <label class="rg-search">
        <AppIcon name="search" aria-hidden="true" />
        <input
          v-model="query"
          type="search"
          :placeholder="i18n.t('pdf_corpus.run_guidance_search', 'Search fields')"
          :aria-label="i18n.t('pdf_corpus.run_guidance_search', 'Search fields')"
        />
      </label>
      <div
        class="rg-filters"
        role="group"
        :aria-label="i18n.t('pdf_corpus.run_guidance_filter', 'Show fields')"
      >
        <button
          type="button"
          :aria-pressed="filter === 'all'"
          :class="{ on: filter === 'all' }"
          @click="filter = 'all'"
        >
          {{ i18n.t("pdf_corpus.run_guidance_filter_all", "All") }}
          <span>{{ fields.length }}</span>
        </button>
        <button
          type="button"
          :aria-pressed="filter === 'configured'"
          :class="{ on: filter === 'configured' }"
          @click="filter = 'configured'"
        >
          {{ i18n.t("pdf_corpus.run_guidance_filter_configured", "With guidance") }}
          <span>{{ configuredCount }}</span>
        </button>
        <button
          type="button"
          :aria-pressed="filter === 'required'"
          :class="{ on: filter === 'required' }"
          @click="filter = 'required'"
        >
          {{ i18n.t("pdf_corpus.run_guidance_filter_required", "Required") }}
          <span>{{ requiredCount }}</span>
        </button>
      </div>
      <div class="rg-actions">
        <UiButton
          size="small"
          variant="ghost"
          icon="upload"
          :label="i18n.t('pdf_corpus.run_guidance_import')"
          :disabled="disabled"
          @click="openImport"
        />
        <UiButton
          size="small"
          variant="ghost"
          icon="download"
          :label="i18n.t('pdf_corpus.run_guidance_export')"
          :disabled="disabled || !configuredCount"
          @click="exportGuidance"
        />
        <UiButton
          size="small"
          variant="ghost"
          icon="trash"
          :label="i18n.t('pdf_corpus.run_guidance_clear_all', 'Clear all')"
          :disabled="disabled || !configuredCount"
          @click="clearAll"
        />
        <input
          ref="importInput"
          type="file"
          accept="application/json,.json"
          class="sr-only"
          :aria-label="i18n.t('pdf_corpus.run_guidance_import')"
          :disabled="disabled"
          @change="importGuidance"
        />
      </div>
    </div>

    <p class="rg-status" aria-live="polite">
      {{ i18n.tf("pdf_corpus.run_guidance_count", { count: configuredCount }) }}
      <span aria-hidden="true">·</span>
      {{ i18n.t("pdf_corpus.run_guidance_saved", "Saved in this browser for this schema") }}
    </p>
    <p v-if="notice" class="rg-notice" role="status">{{ notice }}</p>
    <p v-if="error" class="rg-error" role="alert">{{ error }}</p>

    <div class="rg-body">
      <nav class="rg-list" :aria-label="i18n.t('pdf_corpus.run_guidance_fields', 'Fields')">
        <p v-if="!groups.length" class="rg-empty">
          {{ i18n.t("pdf_corpus.run_guidance_no_match", "No fields match.") }}
        </p>
        <div v-for="group in groups" :key="group.label" class="rg-group">
          <h4>{{ group.label }}</h4>
          <button
            v-for="field in group.items"
            :key="field.name"
            type="button"
            class="rg-row"
            :class="{ active: field.name === selectedName }"
            :aria-current="field.name === selectedName ? 'true' : undefined"
            @click="selectedName = field.name"
          >
            <span class="rg-row-label">{{ field.label }}</span>
            <span class="rg-row-meta">
              <span v-if="modelValue[field.name]?.required" class="rg-tag required">
                {{ i18n.t("pdf_corpus.run_guidance_filter_required", "Required") }}
              </span>
              <span v-if="modelValue[field.name]?.instructions.trim()" class="rg-tag">
                {{ i18n.t("pdf_corpus.run_guidance_tag_note", "Note") }}
              </span>
              <span v-if="modelValue[field.name]?.look_for.length" class="rg-tag">
                {{ modelValue[field.name]?.look_for.length }}
                {{ i18n.t("pdf_corpus.run_guidance_tag_cues", "cues") }}
              </span>
            </span>
          </button>
        </div>
      </nav>

      <div v-if="selected" class="rg-editor">
        <header>
          <div>
            <h3>{{ selected.label }}</h3>
            <small>{{ selected.group }}</small>
          </div>
          <UiButton
            size="small"
            variant="ghost"
            :label="i18n.t('pdf_corpus.run_guidance_reset_field', 'Reset field')"
            :disabled="disabled || !isConfigured(modelValue[selected.name])"
            @click="clearField"
          />
        </header>

        <div class="rg-block">
          <label :for="`run-guidance-instructions-${selected.name}`">
            {{ i18n.t("pdf_corpus.run_guidance_instruction_label") }}
          </label>
          <textarea
            :id="`run-guidance-instructions-${selected.name}`"
            class="control"
            rows="4"
            maxlength="1200"
            :disabled="disabled"
            :value="entry.instructions"
            :placeholder="i18n.t('pdf_corpus.run_guidance_instruction_placeholder')"
            @input="
              update(selected.name, { instructions: ($event.target as HTMLTextAreaElement).value })
            "
          />
          <small class="rg-count">{{ entry.instructions.length }} / 1200</small>
        </div>

        <div class="rg-block">
          <label :for="`run-guidance-terms-${selected.name}`">
            {{ i18n.t("pdf_corpus.run_guidance_terms_label") }}
          </label>
          <div class="rg-cues" @click="cueInput?.focus()">
            <span v-for="term in entry.look_for" :key="term" class="rg-chip">
              {{ term }}
              <button
                type="button"
                :disabled="disabled"
                :aria-label="
                  i18n.tf('pdf_corpus.run_guidance_remove_cue', 'Remove {term}', { term })
                "
                @click.stop="removeCue(term)"
              >
                <AppIcon name="close" aria-hidden="true" />
              </button>
            </span>
            <input
              :id="`run-guidance-terms-${selected.name}`"
              ref="cueInput"
              v-model="cueDraft"
              :disabled="disabled || entry.look_for.length >= 40"
              :placeholder="
                entry.look_for.length ? '' : i18n.t('pdf_corpus.run_guidance_terms_placeholder')
              "
              @keydown="onCueKeydown"
              @paste="onCuePaste"
              @blur="addCues(cueDraft)"
            />
          </div>
          <small>{{ i18n.t("pdf_corpus.run_guidance_terms_help") }}</small>
        </div>

        <div class="rg-block rg-require">
          <div class="rg-switch-row">
            <span>
              <b id="rg-require-label">{{
                i18n.t("pdf_corpus.run_guidance_require_value", "Require a value for this run")
              }}</b>
              <small>{{
                i18n.t(
                  "pdf_corpus.run_guidance_placeholder_help",
                  "If the source supports no value, DerridAI records that as a no-value suggestion and keeps the field in review. It never inserts placeholder text into the metadata field.",
                )
              }}</small>
            </span>
            <button
              type="button"
              role="switch"
              class="rg-switch"
              aria-labelledby="rg-require-label"
              :aria-checked="entry.required === true"
              :disabled="disabled"
              @click="setRequired(entry.required !== true)"
            >
              <span aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
      <p v-else class="rg-empty">
        {{ i18n.t("pdf_corpus.run_guidance_no_fields", "This schema has no fields to guide.") }}
      </p>
    </div>
  </section>
</template>

<style scoped>
.rg {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
}
.rg-help,
.rg-status {
  margin: 0;
  color: var(--text-2);
  font-size: 0.8125rem;
  line-height: 1.5;
}
.rg-status {
  font-size: 0.75rem;
}
.rg-notice,
.rg-error {
  margin: 0;
  font-size: 0.8125rem;
}
.rg-notice {
  color: var(--success);
}
.rg-error {
  color: var(--danger);
}
.rg-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-3);
}
.rg-search {
  flex: 1 1 200px;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--control-height);
  padding: 0 var(--space-3);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-2);
}
.rg-search:focus-within {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.rg-search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text);
  font: inherit;
  padding: 0;
  height: auto;
  box-shadow: none;
}
.rg-filters {
  display: inline-flex;
  padding: 2px;
  gap: 2px;
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.rg-filters button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-2);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
}
.rg-filters button span {
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  opacity: 0.85;
}
.rg-filters button.on {
  background: var(--surface-card);
  color: var(--text);
  box-shadow: 0 1px 2px color-mix(in srgb, var(--text) 18%, transparent);
}
.rg-filters button:focus-visible,
.rg-row:focus-visible,
.rg-chip button:focus-visible,
.rg-switch:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.rg-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-left: auto;
}
.rg-body {
  display: grid;
  grid-template-columns: minmax(220px, 300px) minmax(0, 1fr);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  overflow: hidden;
  min-height: 340px;
}
.rg-list {
  max-height: 520px;
  overflow-y: auto;
  padding: var(--space-2);
  border-right: 1px solid var(--border-subtle);
  background: var(--surface-inset);
}
.rg-group h4 {
  margin: var(--space-3) var(--space-2) var(--space-1);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-2);
}
.rg-group:first-child h4 {
  margin-top: var(--space-1);
}
.rg-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-height: 36px;
  padding: 6px var(--space-2);
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 0.875rem;
  text-align: left;
  cursor: pointer;
}
.rg-row:hover {
  background: var(--surface-hover);
}
.rg-row.active {
  background: var(--surface-selected);
  font-weight: 700;
}
.rg-row-label {
  min-width: 0;
  overflow-wrap: anywhere;
}
.rg-row-meta {
  display: inline-flex;
  flex-shrink: 0;
  gap: 4px;
}
.rg-tag {
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-2);
  font-size: 0.75rem;
  font-weight: 600;
}
.rg-tag.required {
  color: var(--accent-fg);
  border-color: var(--accent-border);
}
.rg-editor {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  padding: var(--space-4);
  min-width: 0;
}
.rg-editor header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}
.rg-editor h3 {
  margin: 0;
  font-size: 1.0625rem;
}
.rg-editor header small {
  color: var(--text-2);
  font-size: 0.75rem;
  text-transform: capitalize;
}
.rg-block {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.rg-block > label,
.rg-block b {
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--text);
}
.rg-block small {
  color: var(--text-2);
  font-size: 0.75rem;
  line-height: 1.4;
}
.rg-block textarea {
  width: 100%;
  resize: vertical;
  min-height: 88px;
}
.rg-count {
  justify-self: end;
  font-variant-numeric: tabular-nums;
}
.rg-cues {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-height: 44px;
  padding: 6px 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  cursor: text;
}
.rg-cues:focus-within {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.rg-cues input {
  flex: 1 1 140px;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text);
  font: inherit;
  padding: 4px;
  height: auto;
  box-shadow: none;
}
.rg-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px 2px 10px;
  border-radius: var(--radius-pill);
  background: var(--surface-selected);
  color: var(--text);
  font-size: 0.8125rem;
}
.rg-chip button {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
}
.rg-chip button:hover {
  background: var(--surface-hover);
  color: var(--text);
}
.rg-chip button :deep(svg) {
  width: 12px;
  height: 12px;
}
.rg-require {
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.rg-switch-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.rg-switch-row > span {
  display: grid;
  gap: 2px;
}
.rg-switch {
  flex-shrink: 0;
  position: relative;
  width: 40px;
  height: 24px;
  padding: 0;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  cursor: pointer;
  transition: background 0.15s;
}
.rg-switch span {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--text-2);
  transition: transform 0.15s;
}
.rg-switch[aria-checked="true"] {
  background: var(--accent-fg);
  border-color: var(--accent-fg);
}
.rg-switch[aria-checked="true"] span {
  background: var(--accent-on);
  transform: translateX(16px);
}
.rg-switch:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.rg-empty {
  margin: var(--space-4);
  color: var(--text-2);
  font-size: 0.8125rem;
}
@media (prefers-reduced-motion: reduce) {
  .rg-switch,
  .rg-switch span {
    transition: none;
  }
}
@media (max-width: 720px) {
  .rg-body {
    grid-template-columns: 1fr;
  }
  .rg-list {
    max-height: 220px;
    border-right: 0;
    border-bottom: 1px solid var(--border-subtle);
  }
  .rg-actions {
    margin-left: 0;
  }
}
</style>
