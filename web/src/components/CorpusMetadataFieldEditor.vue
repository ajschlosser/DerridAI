<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";
import UiCombobox from "./ui/UiCombobox.vue";
import { normalizeMetadataFieldValue } from "../domain/metadataFieldRegistry";
import { usableListOptions } from "../domain/metadataValues";

const props = defineProps<{
  field: string;
  value: unknown;
  status?: Record<string, unknown>;
  options?: string[];
  required?: boolean;
  control?: "enum" | "combobox" | "multi-combobox" | "boolean" | "number" | "text";
  allowCustom?: boolean;
  busy?: boolean;
  saving?: boolean;
  saved?: boolean;
  open?: boolean;
  revealed?: unknown;
  label?: string;
  recheck?: { first: unknown; second: unknown; agreed: boolean };
  constraint?: { value: unknown; reason: string } | null;
  calibratedAcceptance?: { reviewed: number; acceptanceRate: number } | null;
}>();
const emit = defineEmits<{
  save: [value: unknown];
  noValue: [];
  source: [];
  dirty: [dirty: boolean];
}>();
const i18n = useI18nStore();
const editing = ref(Boolean(props.open));
const dirty = ref(false);
const draft = ref<unknown>("");
const confidence = computed(() =>
  typeof props.status?.confidence === "number" && Number.isFinite(props.status.confidence)
    ? Number(props.status.confidence)
    : null,
);
const isLlm = computed(() => String(props.status?.method || "").includes("llm"));
const isMultiCombobox = computed(() => props.control === "multi-combobox");
const autocompleteOptions = computed(() =>
  isMultiCombobox.value ? usableListOptions(props.options || []) : props.options || [],
);
const hasValue = (value: unknown) =>
  !(
    value === undefined ||
    value === null ||
    value === "" ||
    (Array.isArray(value) && !value.length)
  );
const leakedAssessment = (value: unknown) =>
  typeof value === "string" &&
  /^\s*confidence\s*:\s*(?:null|[\d.]+)\s*,\s*needs_review\s*:/i.test(value);
const resolvedValue = computed(() => {
  const status = props.status || {};
  if (
    status.reason_code === "deterministic_llm_disagreement" &&
    status.prefilled_candidate === "llm" &&
    hasValue(status.llm_value)
  )
    return normalizeMetadataFieldValue(props.field, status.llm_value);
  if (status.reason_code === "human_llm_disagreement" && hasValue(status.prefilled_value))
    return normalizeMetadataFieldValue(props.field, status.prefilled_value);
  if (
    hasValue(props.value) &&
    !(props.control === "multi-combobox" && leakedAssessment(props.value))
  )
    return normalizeMetadataFieldValue(props.field, props.value);
  // Backward compatibility for records created before populated-but-unverified
  // proposals were written into the record itself. Confidence affects review
  // state, not whether the reviewer may see the proposed value.
  if (!status.blind && hasValue(status.proposed_value))
    return normalizeMetadataFieldValue(props.field, status.proposed_value);
  if (hasValue(props.constraint?.value))
    return normalizeMetadataFieldValue(props.field, props.constraint?.value);
  return normalizeMetadataFieldValue(
    props.field,
    props.control === "multi-combobox" && leakedAssessment(props.value) ? [] : (props.value ?? ""),
  );
});
function editableValue() {
  const value = resolvedValue.value;
  return Array.isArray(value) ? value.join(", ") : (value ?? "");
}
watch(
  () => [
    props.field,
    props.value,
    props.status?.proposed_value,
    props.status?.llm_value,
    props.status?.prefilled_candidate,
    props.constraint?.value,
  ],
  () => {
    if (!dirty.value) draft.value = editableValue();
  },
  { immediate: true, deep: true },
);
watch(
  () => props.open,
  (value) => {
    if (value) {
      editing.value = true;
      dirty.value = false;
      draft.value = editableValue();
    }
  },
);

function normalized() {
  if (props.control === "multi-combobox")
    return [
      ...new Set(
        String(draft.value || "")
          .split(/[\n,]/)
          .map((v) => v.trim())
          .filter(Boolean),
      ),
    ];
  if (props.control === "number" && draft.value !== "") return Number(draft.value);
  return normalizeMetadataFieldValue(props.field, draft.value);
}
function save() {
  emit("save", normalized());
  dirty.value = false;
  emit("dirty", false);
  editing.value = true;
}
function markDirty() {
  dirty.value = true;
  emit("dirty", true);
}
function selectFromText() {
  const selected = String(window.getSelection()?.toString() || "").trim();
  if (!selected) return;
  if (props.control === "multi-combobox") {
    const current = String(draft.value || "")
      .split(/[,\n]/)
      .map((v) => v.trim())
      .filter(Boolean);
    if (!current.includes(selected)) current.push(selected);
    draft.value = current.join(", ");
  } else {
    draft.value = selected;
  }
  editing.value = true;
  markDirty();
}
function display(value: unknown) {
  if (value === true) return i18n.t("ui.yes");
  if (value === false) return i18n.t("ui.no");
  if (Array.isArray(value)) return value.join(", ") || "—";
  return value === null || value === undefined || value === "" ? "—" : String(value);
}
const confidenceLabel = computed(() =>
  confidence.value === null
    ? i18n.t("pdf_corpus.confidence_not_reported")
    : i18n.tf("pdf_corpus.confidence_percent", {
        percent: Math.round(confidence.value * 100),
      }),
);
const verificationStatus = computed(() => String(props.status?.verification_status || ""));
const autoResolved = computed(
  () => verificationStatus.value === "auto_resolved" || props.status?.autofilled === true,
);
</script>

<template>
  <article
    class="metadata-field"
    :data-attention="
      status?.status === 'unresolved' || status?.status === 'invalid' ? 'true' : 'false'
    "
  >
    <div class="field-topline">
      <div class="field-name">
        <b>{{ i18n.t(`record.${field}`, label || field.replaceAll("_", " ")) }}</b
        ><CorpusFieldOwnershipBadge
          :status="String(status?.status || '')"
          :method="String(status?.method || '')"
          :source="String(status?.value_source || '')"
          :verification="String(status?.verification_status || '')"
          :audit="Boolean(status?.audit_sample)"
        />
      </div>
      <div class="field-actions">
        <button type="button" class="link-button" @click="emit('source')">
          {{ i18n.t("pdf_corpus.view_evidence") }}</button
        ><button
          type="button"
          class="btn small"
          :disabled="busy"
          @click="
            editing = !editing;
            if (!editing) emit('dirty', false);
          "
        >
          {{ editing ? i18n.t("ui.done") : i18n.t("ui.edit") }}
        </button>
      </div>
    </div>
    <p v-if="status?.recheck" class="blind-note" role="status">
      {{
        i18n.t("pdf_corpus.recheck_prompt")
      }}
    </p>
    <p v-else-if="recheck" class="blind-note" role="status">
      {{
        recheck.agreed
          ? i18n.t("pdf_corpus.recheck_same")
          : i18n.tf("pdf_corpus.recheck_changed", { value: display(recheck.first) })
      }}
    </p>
    <p v-if="status?.blind" class="blind-note" role="status">
      {{
        i18n.t("pdf_corpus.blind_review")
      }}
    </p>
    <p v-else-if="hasValue(revealed)" class="blind-note" role="status">
      {{
        i18n.tf("pdf_corpus.blind_revealed", {
          value: display(revealed),
        })
      }}
    </p>
    <div v-if="!editing" class="field-current">{{ display(resolvedValue) }}</div>
    <div v-else class="field-editor">
      <div
        v-if="['deterministic_llm_disagreement', 'human_llm_disagreement'].includes(String(status?.reason_code || ''))"
        class="disagreement"
        role="status"
      >
        <b>{{
          i18n.t("pdf_corpus.metadata_disagreement")
        }}</b
        ><span>{{
          i18n.tf("pdf_corpus.deterministic_value", {
            value: String(status?.deterministic_value ?? "—"),
          })
        }}</span
        ><span
          >{{
            i18n.tf("pdf_corpus.llm_value", {
              value: String(status?.llm_value ?? value ?? "—"),
            })
          }}<template v-if="typeof status?.llm_confidence === 'number'">
            · {{ Math.round(Number(status.llm_confidence) * 100) }}%</template
          ></span
        ><small v-if="status?.deterministic_reason">{{ status.deterministic_reason }}</small
        ><small v-if="status?.llm_reason">{{ status.llm_reason }}</small>
      </div>
      <p v-else-if="status?.reason" class="field-reason">{{ status.reason }}</p>
      <div v-if="constraint" class="constraint" role="status">
        <b>{{ i18n.t("pdf_corpus.deterministic_suggestion") }}</b
        ><span>{{ constraint.reason }}</span>
      </div>
      <div class="value-control">
        <select
          v-if="control === 'enum'"
          v-model="draft"
          class="control"
          :aria-label="i18n.t(`record.${field}`, label || field.replaceAll('_', ' '))"
          @change="markDirty"
        >
          <option value="" disabled>
            {{ i18n.t("pdf_corpus.choose_value") }}
          </option>
          <option v-for="option in options || []" :key="option" :value="option">
            {{ i18n.t(`record.enum.${field}.${option}`, option.replaceAll("_", " ")) }}
          </option>
        </select>
        <fieldset v-else-if="control === 'boolean'" class="boolean-choice">
          <legend class="sr-only">{{ i18n.t(`record.${field}`, field) }}</legend>
          <label
            ><input
              v-model="draft"
              type="radio"
              :name="`${field}-value`"
              :value="true"
              @change="markDirty"
            /><span>{{ i18n.t("ui.yes") }}</span></label
          ><label
            ><input
              v-model="draft"
              type="radio"
              :name="`${field}-value`"
              :value="false"
              @change="markDirty"
            /><span>{{ i18n.t("ui.no") }}</span></label
          >
        </fieldset>
        <UiCombobox
          v-else-if="control === 'combobox'"
          :model-value="String(draft ?? '')"
          :options="autocompleteOptions"
          :label="i18n.t(`record.${field}`, field)"
          @update:model-value="
            (value) => {
              draft = value;
              markDirty();
            }
          "
        />
        <UiCombobox
          v-else-if="isMultiCombobox"
          :model-value="String(draft ?? '')"
          :options="autocompleteOptions"
          :label="i18n.t(`record.${field}`, field)"
          :multiple="true"
          @update:model-value="
            (value) => {
              draft = value;
              markDirty();
            }
          "
        />
        <UiCombobox
          v-else-if="control === 'text' || control === 'number'"
          :model-value="String(draft ?? '')"
          :options="autocompleteOptions"
          :type="control === 'number' ? 'number' : 'text'"
          :label="i18n.t(`record.${field}`, field)"
          @update:model-value="
            (value) => {
              draft = value;
              markDirty();
            }
          "
        />
      </div>
      <div class="editor-actions">
        <button
          type="button"
          class="btn primary"
          :disabled="
            busy || saving || draft === '' || draft === undefined || (required && draft === null)
          "
          @click="save"
        >
          {{
            saving
              ? i18n.t("pdf_corpus.saving_decision")
              : i18n.t("pdf_corpus.save_field_value")
          }}
        </button>
        <button type="button" class="btn" :disabled="busy" @click="emit('noValue')">
          {{ i18n.t("pdf_corpus.confirm_no_value") }}
        </button>
        <button
          v-if="control === 'combobox' || control === 'multi-combobox' || control === 'text'"
          type="button"
          class="btn subtle"
          :disabled="busy"
          @click="selectFromText"
        >
          {{ i18n.t("pdf_corpus.select_from_text") }}
        </button>
      </div>
      <p
        v-if="control === 'combobox' || control === 'multi-combobox' || control === 'text'"
        class="selection-help"
      >
        {{
          i18n.t("pdf_corpus.select_from_text_help")
        }}
      </p>
      <div class="field-meta">
        <span v-if="isLlm && hasValue(resolvedValue)" class="proposal">{{
          autoResolved
            ? i18n.t("pdf_corpus.llm_value_auto_resolved")
            : i18n.t("pdf_corpus.llm_suggestion_prefilled")
        }}</span>
        <span v-if="status?.llm_assessed === true || status?.llm_checked === true">{{
          i18n.t("pdf_corpus.llm_field_assessed")
        }}</span>
        <span v-else-if="status?.llm_value_returned === true">{{
          i18n.t("pdf_corpus.llm_value_without_assessment")
        }}</span>
        <span v-else-if="status?.llm_checked === false && status?.llm_skip_reason">{{
          i18n.tf("pdf_corpus.llm_field_not_checked", {
            reason: String(status?.llm_skip_reason),
          })
        }}</span>
        <span v-if="status?.raw_llm_value && status?.raw_llm_value !== resolvedValue">{{
          i18n.tf("pdf_corpus.llm_value_normalized", { raw: String(status?.raw_llm_value), value: String(resolvedValue) })
        }}</span>
        <span>{{ confidenceLabel }}</span>
        <span v-if="calibratedAcceptance && calibratedAcceptance.reviewed >= 3">{{
          i18n.tf("pdf_corpus.calibrated_acceptance", {
              percent: Math.round(calibratedAcceptance.acceptanceRate * 100),
              count: calibratedAcceptance.reviewed,
            })
        }}</span>
        <span v-if="saved" class="saved" role="status">{{
          i18n.t("pdf_corpus.decision_saved_editable")
        }}</span>
      </div>
    </div>
  </article>
</template>

<style scoped>
.metadata-field {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  padding: 14px;
  display: grid;
  gap: 10px;
}
.metadata-field[data-attention="true"] {
  border-inline-start: 4px solid var(--warning, #a16207);
}
.field-topline {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.field-name {
  min-width: 0;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.field-actions,
.field-meta,
.editor-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.field-current {
  font-size: 0.9375rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.field-editor {
  min-width: 0;
  display: grid;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}
.value-control {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
}
.value-control > * {
  min-width: 0;
  max-width: 100%;
}
.editor-actions {
  align-items: stretch;
}
.editor-actions .btn {
  min-height: 40px;
}
.editor-actions .subtle {
  order: 3;
}
.selection-help {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.4;
}
.field-reason {
  margin: 0;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.5;
}
.disagreement {
  display: grid;
  gap: 3px;
  padding: 10px;
  border: 1px solid var(--warning, #a16207);
  border-radius: 9px;
  background: var(--soft);
  font-size: 0.875rem;
}
.disagreement small {
  color: var(--muted);
  line-height: 1.4;
}
.constraint {
  display: grid;
  gap: 2px;
  padding: 9px 10px;
  border-radius: 9px;
  background: var(--soft);
  font-size: 0.875rem;
}
.constraint b {
  font-size: 0.8125rem;
}
.control {
  width: 100%;
  min-width: 0;
  min-height: 42px;
}
.boolean-choice {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  border: 0;
  padding: 0;
  margin: 0;
}
.boolean-choice label {
  display: flex;
  gap: 6px;
  align-items: center;
  min-height: 40px;
}
.field-meta {
  font-size: 0.8125rem;
  color: var(--muted);
}
.proposal {
  font-weight: 750;
  color: var(--text);
}
.saved {
  color: var(--success, #166534);
  font-weight: 700;
}
.link-button {
  border: 0;
  background: none;
  color: var(--accent-fg);
  font: inherit;
  font-weight: 700;
  min-height: 36px;
  cursor: pointer;
}
:is(button, input, select):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
@media (max-width: 520px) {
  .field-topline {
    flex-direction: column;
  }
  .field-actions,
  .editor-actions {
    width: 100%;
  }
  .editor-actions .btn {
    flex: 1 1 100%;
  }
}
.blind-note {
  margin: 0.25rem 0;
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--tone-info-border);
  border-radius: 8px;
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: 0.8125rem;
}
</style>
