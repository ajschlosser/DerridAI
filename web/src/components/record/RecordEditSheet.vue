<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import AppIcon from "../AppIcon.vue";
import { useI18nStore } from "../../stores/i18n";

const props = withDefaults(defineProps<{ open: boolean; record: Record<string, unknown> }>(), {
  open: false,
  record: () => ({}),
});
const emit = defineEmits<{ close: []; save: [changes: Record<string, unknown>] }>();
const i18n = useI18nStore();
const dialog = ref<HTMLDialogElement | null>(null);
const draft = ref<Record<string, unknown>>({});
const original = ref<Record<string, unknown>>({});
const groups = [
  {
    key: "source",
    label: "record.group_source",
    fallback: "Source",
    fields: [
      "record_id",
      "work",
      "document_title",
      "document_author",
      "edition",
      "year",
      "publication_year",
      "publisher",
      "publication_place",
      "page_start",
      "page_end",
      "region_type",
      "region_author",
      "primary_text",
      "canonical_work_id",
    ],
  },
  {
    key: "discourse",
    label: "record.group_discourse",
    fallback: "Discourse",
    fields: [
      "speaker",
      "position_holder",
      "target",
      "discourse_role",
      "proposition_status",
      "semantic_function",
      "stance",
      "claim_scope",
      "is_direct_quote",
    ],
  },
  {
    key: "quotation",
    label: "record.group_quotation",
    fallback: "Quotation provenance",
    fields: [
      "quoted_speaker",
      "quoted_author",
      "quoted_work",
      "quoted_position_holder",
      "quoted_addressee",
      "quoted_referent",
      "quotation_chain",
    ],
  },
  {
    key: "indexing",
    label: "record.group_indexing",
    fallback: "Indexing",
    fields: [
      "topics",
      "concepts",
      "persons",
      "works_referenced",
      "institutions_referenced",
      "locations_referenced",
      "events_referenced",
      "groups_referenced",
      "languages_referenced",
    ],
  },
  {
    key: "quality",
    label: "record.group_quality",
    fallback: "Quality & review",
    fields: [
      "attribution_confidence",
      "semantic_classification_confidence",
      "extraction_quality",
      "needs_review",
      "review_reason",
    ],
  },
  {
    key: "language",
    label: "record.group_language",
    fallback: "Language & translation",
    fields: ["document_language", "original_language", "document_is_translation", "translator"],
  },
  {
    key: "citation",
    label: "record.group_citation",
    fallback: "Citation",
    fields: ["inline_citation", "full_citation"],
  },
  { key: "text", label: "record.group_text", fallback: "Text", fields: ["text"] },
];
const knownFields = new Set(groups.flatMap((group) => group.fields));
const additionalFields = computed(() =>
  Object.keys(draft.value)
    .filter(
      (key) =>
        !knownFields.has(key) &&
        !key.startsWith("_") &&
        !["updates", "annotations", "text_length", "pdf_pages", "pdf_links"].includes(key),
    )
    .sort(),
);
const visibleGroups = computed(() =>
  groups
    .map((group) => ({
      ...group,
      fields: group.fields.filter((field) =>
        Object.prototype.hasOwnProperty.call(draft.value, field),
      ),
    }))
    .filter((group) => group.fields.length),
);
function clone<T>(value: T): T {
  try {
    return structuredClone(value);
  } catch {
    return JSON.parse(JSON.stringify(value)) as T;
  }
}
function normalizeValue(value: unknown) {
  return value === undefined ? null : value;
}
function equal(a: unknown, b: unknown) {
  try {
    return JSON.stringify(normalizeValue(a)) === JSON.stringify(normalizeValue(b));
  } catch {
    return Object.is(a, b);
  }
}
const changes = computed(() => {
  const out: Record<string, unknown> = {};
  for (const key of Object.keys(draft.value)) {
    if (key === "updates" || key.startsWith("_")) continue;
    if (!equal(draft.value[key], original.value[key])) out[key] = draft.value[key];
  }
  return out;
});
const dirtyCount = computed(() => Object.keys(changes.value).length);
function fieldLabel(key: string) {
  return i18n.t(
    `field.${key}`,
    key.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()),
  );
}
function isArrayField(key: string) {
  return (
    Array.isArray(original.value[key]) ||
    [
      "topics",
      "concepts",
      "persons",
      "works_referenced",
      "institutions_referenced",
      "locations_referenced",
      "events_referenced",
      "groups_referenced",
      "languages_referenced",
      "quotation_chain",
    ].includes(key)
  );
}
function isBooleanField(key: string) {
  return (
    typeof original.value[key] === "boolean" ||
    ["primary_text", "is_direct_quote", "needs_review", "document_is_translation"].includes(key)
  );
}
function isNumberField(key: string) {
  return (
    typeof original.value[key] === "number" ||
    [
      "year",
      "publication_year",
      "page_start",
      "page_end",
      "attribution_confidence",
      "semantic_classification_confidence",
      "extraction_quality",
    ].includes(key)
  );
}
function isLongField(key: string) {
  return ["text", "full_citation", "review_reason", "quotation_chain"].includes(key);
}
function displayInputValue(key: string) {
  const value = draft.value[key];
  if (isArrayField(key)) return Array.isArray(value) ? value.join(", ") : String(value ?? "");
  return String(value ?? "");
}
function updateField(key: string, value: string) {
  if (isArrayField(key)) {
    draft.value[key] = value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    return;
  }
  if (isBooleanField(key)) {
    draft.value[key] = value === "" ? null : value === "true";
    return;
  }
  if (isNumberField(key)) {
    draft.value[key] = value.trim() === "" ? null : Number(value);
    return;
  }
  draft.value[key] = value;
}
function reset() {
  draft.value = clone(original.value);
}
function save() {
  if (!dirtyCount.value) return;
  emit("save", clone(changes.value));
}
watch(
  () => props.open,
  async (open) => {
    if (open) {
      original.value = clone(props.record || {});
      draft.value = clone(props.record || {});
      await nextTick();
      if (dialog.value && !dialog.value.open) dialog.value.showModal();
    } else if (dialog.value?.open) dialog.value.close();
  },
  { immediate: true },
);
watch(
  () => props.record,
  (record) => {
    if (!props.open) {
      original.value = clone(record || {});
      draft.value = clone(record || {});
    }
  },
  { deep: false },
);
function close() {
  emit("close");
}
</script>

<template>
  <dialog
    ref="dialog"
    class="record-edit-sheet"
    aria-labelledby="recordEditTitle"
    @cancel.prevent="close"
    @close="props.open && close()"
  >
    <form method="dialog" @submit.prevent="save">
      <header class="record-edit-head">
        <div>
          <p>{{ i18n.t("record.edit_kicker") }}</p>
          <h2 id="recordEditTitle">{{ i18n.t("record.edit") }}</h2>
          <span>{{
            dirtyCount
              ? i18n.tf("record.unsaved_fields", { count: dirtyCount })
              : i18n.t("record.no_unsaved_changes")
          }}</span>
        </div>
        <button
          type="button"
          class="record-sheet-close"
          :aria-label="i18n.t('ui.close')"
          @click="close"
        >
          ×
        </button>
      </header>
      <div class="record-edit-body">
        <fieldset v-for="group in visibleGroups" :key="group.key" class="record-edit-group">
          <legend>{{ i18n.t(group.label, group.fallback) }}</legend>
          <div class="record-edit-grid">
            <label
              v-for="field in group.fields"
              :key="field"
              :class="{ 'record-edit-wide': isLongField(field) }"
              ><span>{{ fieldLabel(field) }}</span
              ><select
                v-if="isBooleanField(field)"
                :value="
                  draft[field] === null || draft[field] === undefined
                    ? ''
                    : String(Boolean(draft[field]))
                "
                @change="updateField(field, ($event.target as HTMLSelectElement).value)"
              >
                <option value="">{{ i18n.t("ui.not_set") }}</option>
                <option value="true">{{ i18n.t("runtime.yes") }}</option>
                <option value="false">{{ i18n.t("runtime.no") }}</option></select
              ><textarea
                v-else-if="isLongField(field)"
                :value="displayInputValue(field)"
                :rows="field === 'text' ? 12 : 4"
                @input="updateField(field, ($event.target as HTMLTextAreaElement).value)"
              ></textarea
              ><input
                v-else
                :type="isNumberField(field) ? 'number' : 'text'"
                :step="
                  [
                    'attribution_confidence',
                    'semantic_classification_confidence',
                    'extraction_quality',
                  ].includes(field)
                    ? '0.01'
                    : undefined
                "
                :value="displayInputValue(field)"
                @input="updateField(field, ($event.target as HTMLInputElement).value)"
              /><small v-if="isArrayField(field)">{{
                i18n.t("record.comma_separated")
              }}</small></label
            >
          </div>
        </fieldset>
        <fieldset v-if="additionalFields.length" class="record-edit-group">
          <legend>{{ i18n.t("record.group_other") }}</legend>
          <div class="record-edit-grid">
            <label v-for="field in additionalFields" :key="field"
              ><span>{{ fieldLabel(field) }}</span
              ><input
                :value="displayInputValue(field)"
                @input="updateField(field, ($event.target as HTMLInputElement).value)"
            /></label>
          </div>
        </fieldset>
      </div>
      <footer class="record-edit-actions">
        <div>
          <button type="button" class="record-reset" :disabled="!dirtyCount" @click="reset">
            <AppIcon name="refresh" />{{ i18n.t("ui.reset") }}</button
          ><span>{{
            i18n.t("record.sparse_save_help")
          }}</span>
        </div>
        <div>
          <button type="button" class="record-cancel" @click="close">
            {{ i18n.t("ui.cancel") }}</button
          ><button type="submit" class="record-save" :disabled="!dirtyCount">
            <AppIcon name="edit" />{{ i18n.t("ui.save") }}
          </button>
        </div>
      </footer>
    </form>
  </dialog>
</template>

<style scoped>
.record-edit-sheet {
  position: fixed;
  inset: 0 0 0 auto;
  width: min(720px, 94vw);
  max-width: none;
  height: 100dvh;
  max-height: none;
  margin: 0;
  border: 0;
  border-left: 1px solid var(--line);
  padding: 0;
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
}
.record-edit-sheet::backdrop {
  background: rgba(15, 23, 42, 0.38);
  backdrop-filter: blur(2px);
}
.record-edit-sheet form {
  height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
}
.record-edit-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: start;
  padding: 20px 22px;
  border-bottom: 1px solid var(--line);
  background: var(--surface-raised);
}
.record-edit-head p {
  margin: 0;
  color: var(--accent-fg);
  font-size: 0.8125rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}
.record-edit-head h2 {
  margin: 3px 0 4px;
  font:
    600 24px/1.15 Georgia,
    "Times New Roman",
    serif;
}
.record-edit-head span {
  color: var(--muted);
  font-size: 0.8125rem;
}
.record-sheet-close {
  width: 38px;
  height: 38px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
  color: var(--text-2);
  font-size: 1.3125rem;
  cursor: pointer;
}
.record-edit-body {
  overflow: auto;
  padding: 20px 22px 32px;
  display: grid;
  gap: 24px;
}
.record-edit-group {
  min-width: 0;
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  border: 0;
}
.record-edit-group legend {
  width: 100%;
  margin: 0;
  padding: 0 0 8px;
  border-bottom: 1px solid var(--line);
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 800;
}
.record-edit-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 13px;
}
.record-edit-grid label {
  display: grid;
  gap: 6px;
  align-content: start;
}
.record-edit-grid label > span {
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 800;
}
.record-edit-grid input,
.record-edit-grid select,
.record-edit-grid textarea {
  width: 100%;
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
  padding: 8px 10px;
  color: var(--text);
  font:
    13px/1.45 system-ui,
    sans-serif;
}
.record-edit-grid textarea {
  resize: vertical;
}
.record-edit-grid small {
  color: var(--muted);
  font-size: 0.8125rem;
}
.record-edit-wide {
  grid-column: 1/-1;
}
.record-edit-actions {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 14px 22px;
  border-top: 1px solid var(--line);
  background: var(--surface-raised);
}
.record-edit-actions > div {
  display: flex;
  gap: 8px;
  align-items: center;
}
.record-edit-actions > div:first-child span {
  max-width: 330px;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.4;
}
.record-edit-actions button {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  background: var(--surface-raised);
  padding: 0 12px;
  color: var(--text-2);
  font-weight: 800;
  cursor: pointer;
}
.record-edit-actions button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.record-edit-actions .record-save {
  border-color: var(--ui-accent, #3c8d62);
  background: var(--ui-accent, #3c8d62);
  color: var(--accent-on);
}
.record-edit-actions :deep(svg) {
  width: 15px;
  height: 15px;
}
button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 2px;
}
@media (max-width: 620px) {
  .record-edit-sheet {
    width: 100vw;
  }
  .record-edit-grid {
    grid-template-columns: 1fr;
  }
  .record-edit-wide {
    grid-column: auto;
  }
  .record-edit-actions {
    align-items: stretch;
    flex-direction: column;
  }
  .record-edit-actions > div {
    justify-content: flex-end;
    width: 100%;
  }
  .record-edit-actions > div:first-child {
    justify-content: space-between;
  }
}
@media (prefers-reduced-motion: no-preference) {
  .record-edit-sheet[open] {
    animation: record-sheet-in 0.18s ease-out;
  }
  @keyframes record-sheet-in {
    from {
      transform: translateX(18px);
      opacity: 0.85;
    }
    to {
      transform: none;
      opacity: 1;
    }
  }
}
</style>
