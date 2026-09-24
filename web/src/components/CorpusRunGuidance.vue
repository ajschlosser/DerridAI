<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";

export interface RunGuidanceEntry {
  instructions: string;
  look_for: string[];
}

export interface RunGuidanceField {
  name: string;
  label: string;
  group: string;
}

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
const notice = ref("");
const error = ref("");
const termBuffers = ref<Record<string, string>>({});
const populated = computed(
  () =>
    Object.values(props.modelValue).filter(
      (item) => item.instructions.trim() || item.look_for.length,
    ).length,
);

function update(field: string, patch: Partial<RunGuidanceEntry>) {
  const previous = props.modelValue[field] || { instructions: "", look_for: [] };
  emit("update:modelValue", {
    ...props.modelValue,
    [field]: { ...previous, ...patch },
  });
}

function updateTerms(field: string, value: string) {
  const terms = value
    .split("\n")
    // Keep the edit buffer lossless so a trailing space does not disappear
    // while a multi-word phrase is being typed. Submission trims each term.
    .filter((item) => item.trim())
    .slice(0, 40);
  update(field, { look_for: terms });
}

function editTerms(field: string, value: string) {
  termBuffers.value = { ...termBuffers.value, [field]: value };
  updateTerms(field, value);
}

function commitTerms(field: string) {
  const value = termBuffers.value[field];
  if (value !== undefined) updateTerms(field, value);
}

function termText(field: string) {
  return termBuffers.value[field] ?? (props.modelValue[field]?.look_for || []).join("\n");
}

watch(
  () => props.modelValue,
  (value) => {
    const next = { ...termBuffers.value };
    for (const field of props.fields) {
      if (document.activeElement !== document.getElementById(`run-guidance-terms-${field.name}`)) {
        next[field.name] = (value[field.name]?.look_for || []).join("\n");
      }
    }
    termBuffers.value = next;
  },
  { immediate: true, deep: true },
);

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
    throw new Error(
      i18n.t("pdf_corpus.run_guidance_import_invalid"),
    );
  }
  const fields = new Map(props.fields.map((field) => [field.name, field]));
  const imported: Record<string, RunGuidanceEntry> = {};
  for (const [field, raw] of Object.entries(source)) {
    if (!fields.has(field) || !raw || typeof raw !== "object" || Array.isArray(raw)) continue;
    const entry = raw as { instructions?: unknown; look_for?: unknown };
    const instructions = typeof entry.instructions === "string" ? entry.instructions : "";
    const lookFor = Array.isArray(entry.look_for)
      ? entry.look_for
          .filter((term): term is string => typeof term === "string" && term.trim().length > 0)
          .slice(0, 40)
      : [];
    if (instructions.trim() || lookFor.length)
      imported[field] = { instructions, look_for: lookFor };
  }
  if (!Object.keys(imported).length) {
    throw new Error(
      i18n.t("pdf_corpus.run_guidance_import_no_fields"),
    );
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
    class="run-guidance"
    :aria-label="i18n.t('pdf_corpus.run_guidance_title')"
    aria-describedby="run-guidance-help"
  >
    <p id="run-guidance-help" class="run-guidance-help">
      {{
        i18n.t("pdf_corpus.run_guidance_help")
      }}
    </p>
    <p class="run-guidance-count" aria-live="polite">
      {{
        i18n.tf("pdf_corpus.run_guidance_count", {
          count: populated,
        })
      }}
    </p>
    <p class="run-guidance-file-help">
      {{
        i18n.t("pdf_corpus.run_guidance_file_help")
      }}
    </p>
    <div class="run-guidance-actions">
      <UiButton
        size="small"
        icon="download"
        :label="i18n.t('pdf_corpus.run_guidance_export')"
        :disabled="disabled"
        @click="exportGuidance"
      />
      <UiButton
        size="small"
        icon="upload"
        :label="i18n.t('pdf_corpus.run_guidance_import')"
        :disabled="disabled"
        @click="openImport"
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
    <p v-if="notice" class="run-guidance-notice" role="status">{{ notice }}</p>
    <p v-if="error" class="run-guidance-error" role="alert">{{ error }}</p>
    <details v-for="field in fields" :key="field.name" class="run-guidance-field">
      <summary>
        <span>{{ field.label }}</span>
        <small>{{ field.group }}</small>
      </summary>
      <div class="run-guidance-controls">
        <label :for="`run-guidance-instructions-${field.name}`">
          <span>{{
            i18n.t("pdf_corpus.run_guidance_instruction_label")
          }}</span>
          <textarea
            :id="`run-guidance-instructions-${field.name}`"
            class="control"
            rows="2"
            maxlength="1200"
            :disabled="disabled"
            :value="modelValue[field.name]?.instructions || ''"
            :placeholder="
              i18n.t('pdf_corpus.run_guidance_instruction_placeholder')
            "
            @input="
              update(field.name, { instructions: ($event.target as HTMLTextAreaElement).value })
            "
          />
        </label>
        <label :for="`run-guidance-terms-${field.name}`">
          <span>{{
            i18n.t("pdf_corpus.run_guidance_terms_label")
          }}</span>
          <textarea
            :id="`run-guidance-terms-${field.name}`"
            class="control"
            rows="3"
            :disabled="disabled"
            :value="termText(field.name)"
            :placeholder="
              i18n.t('pdf_corpus.run_guidance_terms_placeholder')
            "
            @input="editTerms(field.name, ($event.target as HTMLTextAreaElement).value)"
            @blur="commitTerms(field.name)"
          />
          <small>{{
            i18n.t("pdf_corpus.run_guidance_terms_help")
          }}</small>
        </label>
      </div>
    </details>
  </section>
</template>

<style scoped>
.run-guidance {
  display: grid;
  gap: 8px;
  min-width: 0;
}
.run-guidance-help,
.run-guidance-count,
.run-guidance-file-help {
  margin: 0;
  color: var(--text-2);
  font-size: 0.8125rem;
  line-height: 1.5;
}
.run-guidance-file-help {
  margin-top: -4px;
  font-size: 0.75rem;
}
.run-guidance-count {
  font-weight: 700;
}
.run-guidance-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.run-guidance-notice,
.run-guidance-error {
  margin: 0;
  font-size: 0.8125rem;
}
.run-guidance-notice {
  color: var(--success);
}
.run-guidance-error {
  color: var(--danger);
}
.run-guidance-field {
  min-width: 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.run-guidance-field > summary {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 11px;
  cursor: pointer;
  font-weight: 700;
  color: var(--text);
}
.run-guidance-field > summary:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 2px;
  border-radius: var(--radius-control);
}
.run-guidance-field > summary small {
  color: var(--text-2);
  font-size: 0.75rem;
  text-transform: capitalize;
}
.run-guidance-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 0 11px 11px;
}
.run-guidance-controls label {
  display: grid;
  align-content: start;
  gap: 5px;
  min-width: 0;
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 700;
}
.run-guidance-controls textarea {
  width: 100%;
  min-height: 74px;
  resize: vertical;
}
.run-guidance-controls small {
  font-size: 0.75rem;
  font-weight: 400;
  line-height: 1.4;
}
@media (max-width: 640px) {
  .run-guidance-controls {
    grid-template-columns: 1fr;
  }
}
</style>
