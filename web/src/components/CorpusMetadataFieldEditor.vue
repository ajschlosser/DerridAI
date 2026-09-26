<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import AppIcon from "./AppIcon.vue";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";
import UiCombobox from "./ui/UiCombobox.vue";
import { normalizeMetadataFieldValue } from "../domain/metadataFieldRegistry";
import { groupOptionsBySuggestion, suggestedValues } from "../domain/metadataSuggestion";
import { useRecordTextSelection } from "../composables/useRecordTextSelection";
import CorpusFieldSelectionPreview from "./CorpusFieldSelectionPreview.vue";
import {
  metadataValueText,
  unwrapMetadataValue,
  usableListOptions,
  withoutTransportItems,
} from "../domain/metadataValues";

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
  /** Less certain values earlier reviews attached to matching source spans. */
  hints?: { value: unknown; similarity: number; support: number }[];
  /** The server will not accept the record until this field is decided. */
  requiredToAccept?: boolean;
}>();
const emit = defineEmits<{
  save: [value: unknown];
  noValue: [];
  source: [];
  saveWithSelectionEvidence: [value: unknown, text: string];
  dirty: [dirty: boolean];
}>();
const i18n = useI18nStore();
const labelId = `${useId()}-label`;
const editing = ref(Boolean(props.open));
const dirty = ref(false);
const draft = ref<unknown>("");
const confidence = computed(() =>
  typeof props.status?.confidence === "number" && Number.isFinite(props.status.confidence)
    ? Number(props.status.confidence)
    : null,
);
const isLlm = computed(
  () =>
    String(props.status?.method || "").includes("llm") ||
    String(props.status?.derivation_method || "") === "model",
);
const isMultiCombobox = computed(() => props.control === "multi-combobox");
const assertionAlternatives = computed<Record<string, unknown>[]>(() =>
  Array.isArray(props.status?.conflicting_assertions)
    ? (props.status?.conflicting_assertions as Record<string, unknown>[])
    : [],
);
const DERIVATION_LABELS: Record<string, string> = {
  "derridai:memory": "pdf_corpus.derivation_memory",
  "derridai:nlp": "pdf_corpus.derivation_nlp",
  "derridai:computed": "pdf_corpus.derivation_computed",
};
/** Namespaced derivations get a plain label ("Metadata memory"); the rest read as before. */
function derivationLabel(value: unknown) {
  const key = DERIVATION_LABELS[String(value || "")];
  return key ? i18n.t(key) : humanizeToken(value);
}
function useHint(value: unknown) {
  draft.value = Array.isArray(value) ? value.join(", ") : value;
  editing.value = true;
  markDirty();
}
function humanizeToken(value: unknown) {
  return String(value || "")
    .replaceAll("_", " ")
    .trim();
}
function displayTimestamp(value: unknown) {
  if (!value) return "";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}
const modelSuggestion = computed(() =>
  suggestedValues(props.status, props.value, isLlm.value, hasValue),
);
const optionGroups = computed(() =>
  groupOptionsBySuggestion(props.options || [], modelSuggestion.value),
);
const suggestedOptions = computed(() => optionGroups.value.suggested);
const otherOptions = computed(() => optionGroups.value.others);
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
    return normalizeMetadataFieldValue(props.field, withoutTransportItems(props.value));
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
  const value = unwrapMetadataValue(resolvedValue.value);
  return Array.isArray(value) ? value.join(", ") : metadataValueText(value);
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
    } else if (!dirty.value) {
      // A pending field that has just been decided folds back into its one-line summary.
      editing.value = false;
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
const selectionMissing = ref(false);
const canSave = computed(
  () =>
    !props.busy &&
    !props.saving &&
    draft.value !== "" &&
    draft.value !== undefined &&
    !(props.required && draft.value === null),
);
function save() {
  if (!canSave.value) return;
  emit("save", normalized());
  dirty.value = false;
  emit("dirty", false);
  // A pending field stays open until the saved record says it is decided; an optional edit closes at once.
  editing.value = Boolean(props.open);
}
function startEdit() {
  editing.value = true;
  dirty.value = false;
  draft.value = editableValue();
}
function cancelEdit() {
  dirty.value = false;
  draft.value = editableValue();
  editing.value = false;
  emit("dirty", false);
}
/** Ctrl/Cmd+Enter confirms from anywhere in the field, including inside its value control. */
function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey) || !editing.value) return;
  event.preventDefault();
  save();
}
function saveWithSelection() {
  if (!canSave.value) return;
  const selected = selectedRecordText();
  if (!selected) {
    selectionMissing.value = true;
    return;
  }
  selectionMissing.value = false;
  emit("saveWithSelectionEvidence", normalized(), selected);
  liveSelection.value = "";
  dirty.value = false;
  emit("dirty", false);
  editing.value = Boolean(props.open);
}
function markDirty() {
  dirty.value = true;
  emit("dirty", true);
}
const { selection: liveSelection, capture: selectedRecordText } = useRecordTextSelection(editing);
function selectFromText() {
  const selected = selectedRecordText();
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
  const unwrapped = unwrapMetadataValue(value);
  if (unwrapped === true) return i18n.t("ui.yes");
  if (unwrapped === false) return i18n.t("ui.no");
  return metadataValueText(unwrapped) || "—";
}
const fieldLabel = computed(() =>
  i18n.t(`record.${props.field}`, props.label || props.field.replaceAll("_", " ")),
);
const textSelectable = computed(
  () =>
    props.control === "combobox" || props.control === "multi-combobox" || props.control === "text",
);
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
    :data-field="field"
    :data-mode="editing ? 'edit' : 'view'"
    :data-attention="
      status?.status === 'unresolved' || status?.status === 'invalid' ? 'true' : 'false'
    "
    :data-unresolved-field="open ? 'true' : undefined"
    :aria-labelledby="labelId"
    @keydown="onKeydown"
  >
    <!-- A decided field is one line: what it is, its value, where the value came from. -->
    <div v-if="!editing" class="field-row">
      <span :id="labelId" class="field-label">{{ fieldLabel }}</span>
      <span class="field-current">{{ display(resolvedValue) }}</span>
      <span class="field-row-aside">
        <span v-if="saved" class="saved" role="status"
          ><AppIcon name="check" />{{ i18n.t("pdf_corpus.field_saved_short") }}</span
        ><CorpusFieldOwnershipBadge
          :status="String(status?.status || '')"
          :method="String(status?.method || '')"
          :derivation="String(status?.derivation_method || '')"
          :source="String(status?.value_source || '')"
          :verification="String(status?.verification_status || '')"
          :audit="Boolean(status?.audit_sample)"
        /><button
          type="button"
          class="btn small quiet field-edit"
          :disabled="busy"
          :aria-label="i18n.tf('pdf_corpus.edit_field', { field: fieldLabel })"
          @click="startEdit"
        >
          {{ i18n.t("ui.edit") }}
        </button>
      </span>
    </div>
    <header v-else class="field-head">
      <div class="field-title">
        <b :id="labelId" class="field-label">{{ fieldLabel }}</b
        ><span v-if="requiredToAccept" class="field-required">{{
          i18n.t("pdf_corpus.required_to_accept")
        }}</span>
      </div>
      <span class="field-head-aside">
        <span v-if="saved" class="saved" role="status"
          ><AppIcon name="check" />{{ i18n.t("pdf_corpus.field_saved_short") }}</span
        ><CorpusFieldOwnershipBadge
          :status="String(status?.status || '')"
          :method="String(status?.method || '')"
          :derivation="String(status?.derivation_method || '')"
          :source="String(status?.value_source || '')"
          :verification="String(status?.verification_status || '')"
          :audit="Boolean(status?.audit_sample)"
        />
      </span>
      <slot name="policy" />
    </header>
    <p v-if="status?.recheck" class="blind-note" role="status">
      {{ i18n.t("pdf_corpus.recheck_prompt") }}
    </p>
    <p v-else-if="recheck" class="blind-note" role="status">
      {{
        recheck.agreed
          ? i18n.t("pdf_corpus.recheck_same")
          : i18n.tf("pdf_corpus.recheck_changed", { value: display(recheck.first) })
      }}
    </p>
    <p v-if="status?.blind" class="blind-note" role="status">
      {{ i18n.t("pdf_corpus.blind_review") }}
    </p>
    <p v-else-if="hasValue(revealed)" class="blind-note" role="status">
      {{
        i18n.tf("pdf_corpus.blind_revealed", {
          value: display(revealed),
        })
      }}
    </p>
    <div v-if="editing" class="field-editor">
      <div
        v-if="
          ['deterministic_llm_disagreement', 'human_llm_disagreement'].includes(
            String(status?.reason_code || ''),
          )
        "
        class="disagreement"
        role="status"
      >
        <b>{{ i18n.t("pdf_corpus.metadata_disagreement") }}</b
        ><span>{{
          i18n.tf("pdf_corpus.deterministic_value", {
            value: display(status?.deterministic_value),
          })
        }}</span
        ><span
          >{{
            i18n.tf("pdf_corpus.llm_value", {
              value: display(status?.llm_value ?? value),
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
          :aria-label="fieldLabel"
          @change="markDirty"
        >
          <option value="" disabled>
            {{ i18n.t("pdf_corpus.choose_value") }}
          </option>
          <optgroup v-if="suggestedOptions.length" :label="i18n.t('pdf_corpus.model_suggested')">
            <option v-for="option in suggestedOptions" :key="option" :value="option">
              ★ {{ i18n.t(`record.enum.${field}.${option}`, option.replaceAll("_", " ")) }} ({{
                i18n.t("pdf_corpus.model_suggested_short")
              }})
            </option>
          </optgroup>
          <optgroup v-if="suggestedOptions.length" :label="i18n.t('pdf_corpus.all_values')">
            <option v-for="option in otherOptions" :key="option" :value="option">
              {{ i18n.t(`record.enum.${field}.${option}`, option.replaceAll("_", " ")) }}
            </option>
          </optgroup>
          <template v-else>
            <option v-for="option in otherOptions" :key="option" :value="option">
              {{ i18n.t(`record.enum.${field}.${option}`, option.replaceAll("_", " ")) }}
            </option>
          </template>
        </select>
        <fieldset v-else-if="control === 'boolean'" class="boolean-choice">
          <legend class="sr-only">{{ fieldLabel }}</legend>
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
          :recommended="modelSuggestion"
          :recommended-label="i18n.t('pdf_corpus.model_suggested_short')"
          :label="fieldLabel"
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
          :recommended="modelSuggestion"
          :recommended-label="i18n.t('pdf_corpus.model_suggested_short')"
          :label="fieldLabel"
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
          :recommended="modelSuggestion"
          :recommended-label="i18n.t('pdf_corpus.model_suggested_short')"
          :type="control === 'number' ? 'number' : 'text'"
          :label="fieldLabel"
          @update:model-value="
            (value) => {
              draft = value;
              markDirty();
            }
          "
        />
      </div>
      <div v-if="hints?.length" class="memory-hints">
        <small>{{ i18n.t("pdf_corpus.memory_hints_title") }}</small>
        <button
          v-for="hint in hints"
          :key="String(hint.value)"
          type="button"
          class="hint-chip"
          :disabled="busy"
          @click="useHint(hint.value)"
        >
          {{ display(hint.value) }}
          <small
            >{{ Math.round(hint.similarity * 100) }}% ·
            {{ i18n.tf("pdf_corpus.memory_hint_support", { count: hint.support }) }}</small
          >
        </button>
      </div>
      <!-- The decision row keeps the same shape in every field: confirm, no value, and (for an optional edit) cancel. -->
      <div class="editor-actions">
        <button
          type="button"
          class="btn small primary"
          data-primary-action
          :disabled="!canSave"
          aria-keyshortcuts="Control+Enter Meta+Enter"
          @click="save"
        >
          {{
            saving
              ? i18n.t("pdf_corpus.saving_decision")
              : dirty || !hasValue(resolvedValue)
                ? i18n.t("pdf_corpus.save_field_value")
                : i18n.t("pdf_corpus.confirm_field_value")
          }}<kbd aria-hidden="true">{{ i18n.t("pdf_corpus.shortcut.confirm_field") }}</kbd>
        </button>
        <button
          type="button"
          class="btn small"
          :disabled="busy"
          :title="i18n.t('pdf_corpus.confirm_no_value')"
          @click="emit('noValue')"
        >
          {{ i18n.t("pdf_corpus.no_value_short") }}
        </button>
        <button v-if="!open" type="button" class="btn small quiet" @click="cancelEdit">
          {{ i18n.t("ui.cancel") }}
        </button>
      </div>
      <CorpusFieldSelectionPreview :selection="liveSelection" @clear="liveSelection = ''" />
      <div class="field-tools">
        <template v-if="textSelectable">
          <button
            type="button"
            class="link-button"
            :disabled="busy"
            :title="i18n.t('pdf_corpus.select_from_text_help')"
            @click="selectFromText"
          >
            {{ i18n.t("pdf_corpus.select_from_text") }}
          </button></template
        >
        <button
          type="button"
          class="link-button"
          :disabled="!canSave"
          :title="i18n.t('pdf_corpus.assign_selected_evidence_help')"
          @click="saveWithSelection"
        >
          {{ i18n.t("pdf_corpus.assign_selected_evidence_short") }}</button
        ><button type="button" class="link-button" @click="emit('source')">
          {{ i18n.t("pdf_corpus.view_evidence") }}
        </button>
      </div>
      <p v-if="selectionMissing" class="selection-help" role="alert">
        {{ i18n.t("pdf_corpus.select_text_first") }}
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
          i18n.tf("pdf_corpus.llm_value_normalized", {
            raw: display(status?.raw_llm_value),
            value: display(resolvedValue),
          })
        }}</span>
        <span>{{ confidenceLabel }}</span>
        <span v-if="calibratedAcceptance && calibratedAcceptance.reviewed >= 3">{{
          i18n.tf("pdf_corpus.calibrated_acceptance", {
            percent: Math.round(calibratedAcceptance.acceptanceRate * 100),
            count: calibratedAcceptance.reviewed,
          })
        }}</span>
      </div>
      <details v-if="status?.assertion_id" class="assertion-provenance">
        <summary>
          <span>{{ i18n.t("pdf_corpus.assertion_details", "Assertion details") }}</span>
          <span v-if="status?.disputed" class="assertion-disputed">{{
            i18n.t("pdf_corpus.assertion_disputed", "Disputed")
          }}</span>
        </summary>
        <dl class="assertion-facts">
          <div v-if="status?.derivation_method">
            <dt>{{ i18n.t("pdf_corpus.assertion_derivation", "Derivation") }}</dt>
            <dd>{{ derivationLabel(status.derivation_method) }}</dd>
          </div>
          <div v-if="status?.evaluation_status">
            <dt>{{ i18n.t("pdf_corpus.assertion_evaluation", "Evaluation") }}</dt>
            <dd>{{ humanizeToken(status.evaluation_status) }}</dd>
          </div>
          <div v-if="status?.authority_status">
            <dt>{{ i18n.t("pdf_corpus.assertion_authority", "Authority") }}</dt>
            <dd>{{ humanizeToken(status.authority_status) }}</dd>
          </div>
          <div v-if="status?.value_status">
            <dt>{{ i18n.t("pdf_corpus.assertion_value_state", "Value state") }}</dt>
            <dd>{{ humanizeToken(status.value_status) }}</dd>
          </div>
          <div v-if="status?.model">
            <dt>{{ i18n.t("pdf_corpus.assertion_model", "Model") }}</dt>
            <dd>{{ status.model }}</dd>
          </div>
          <div v-if="status?.actor">
            <dt>{{ i18n.t("pdf_corpus.assertion_actor", "Actor") }}</dt>
            <dd>{{ status.actor }}</dd>
          </div>
          <div v-if="status?.record_revision">
            <dt>{{ i18n.t("pdf_corpus.assertion_revision", "Record revision") }}</dt>
            <dd>{{ status.record_revision }}</dd>
          </div>
          <div v-if="status?.created_at">
            <dt>{{ i18n.t("pdf_corpus.assertion_created", "Created") }}</dt>
            <dd>{{ displayTimestamp(status.created_at) }}</dd>
          </div>
        </dl>
        <p v-if="status?.reason" class="assertion-reason">{{ status.reason }}</p>
        <p v-if="Array.isArray(status?.evidence)" class="assertion-evidence-count">
          {{
            i18n.tf("pdf_corpus.assertion_evidence_count", {
              count: status.evidence.length,
            })
          }}
        </p>
        <div v-if="assertionAlternatives.length" class="assertion-alternatives">
          <b>{{
            i18n.t("pdf_corpus.assertion_retained_alternatives", "Retained alternative assertions")
          }}</b>
          <ul>
            <li
              v-for="item in assertionAlternatives"
              :key="String(item.assertion_id || item.created_at || item.value)"
            >
              <span>{{ display(item.value) }}</span>
              <small>
                {{ derivationLabel(item.derivation_method) }}
                <template v-if="item.authority_status">
                  · {{ humanizeToken(item.authority_status) }}</template
                >
                <template v-if="item.model"> · {{ item.model }}</template>
                <template v-if="item.actor"> · {{ item.actor }}</template>
              </small>
            </li>
          </ul>
        </div>
      </details>
    </div>
  </article>
</template>

<style scoped>
.metadata-field {
  /* Layout follows the width the field is given (workspace inspector, Focus View, a dialog), not the window. */
  container: metadata-field / inline-size;
  min-width: 0;
  display: grid;
  gap: var(--space-2, 8px);
}
/* An open field is a card; a decided one is a quiet row in a list. */
.metadata-field[data-mode="edit"] {
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.metadata-field[data-mode="edit"][data-attention="true"] {
  border-inline-start: 3px solid var(--tone-warn-border);
}
.metadata-field[data-mode="edit"]:focus-within {
  border-color: var(--ui-accent, var(--accent));
  box-shadow: 0 0 0 1px var(--ui-accent, var(--accent));
}
.field-row {
  display: grid;
  grid-template-columns: minmax(7rem, 0.8fr) minmax(0, 1.4fr) auto;
  gap: 4px 12px;
  align-items: center;
  min-height: 40px;
  padding: 4px 0;
}
.field-label {
  min-width: 0;
  color: var(--text-secondary, var(--muted));
  font-size: var(--fs-sm);
  font-weight: 700;
  overflow-wrap: anywhere;
}
.field-head .field-label {
  color: var(--text);
  font-size: var(--fs-base);
}
.field-current {
  min-width: 0;
  font-size: var(--fs-base);
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.field-row-aside,
.field-head-aside {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
}
/* Title first on its own terms; the provenance badges sit at the end and drop below it when the card is narrow. */
.field-head {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  align-items: center;
}
.field-head > .field-title {
  flex: 1 1 10rem;
}
.field-head > .field-head-aside {
  margin-inline-start: auto;
}
.field-head > :deep(.field-policy) {
  flex-basis: 100%;
}
.field-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}
.field-required {
  color: var(--tone-warn-fg);
  font-size: var(--fs-xs);
  font-weight: 700;
}
.field-editor {
  min-width: 0;
  display: grid;
  gap: 8px;
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
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}
.editor-actions .btn {
  min-height: 36px;
}
.editor-actions kbd {
  margin-inline-start: 8px;
  padding: 0 4px;
  border: 1px solid color-mix(in srgb, currentColor 35%, transparent);
  border-radius: 4px;
  font: inherit;
  font-size: var(--fs-xs);
  font-weight: 600;
  opacity: 0.85;
}
.field-tools {
  display: flex;
  gap: 0 14px;
  align-items: center;
  flex-wrap: wrap;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
.field-tools .link-button {
  display: inline-flex;
  align-items: center;
  width: auto;
  min-height: 28px;
  padding: 0;
  font-size: var(--fs-sm);
  text-align: start;
}
.field-tools .link-button:disabled {
  color: var(--text-tertiary);
  cursor: default;
}
.selection-help {
  margin: 0;
  color: var(--tone-warn-fg);
  font-size: var(--fs-sm);
  line-height: 1.4;
}
.field-reason {
  margin: 0;
  color: var(--text-secondary, var(--muted));
  font-size: var(--fs-sm);
  line-height: 1.5;
}
.disagreement {
  display: grid;
  gap: 3px;
  padding: 8px 10px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: var(--radius-control);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: var(--fs-sm);
}
.disagreement small {
  line-height: 1.4;
}
.constraint {
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  border-radius: var(--radius-control);
  background: var(--surface-inset, var(--soft));
  font-size: var(--fs-sm);
}
.control {
  width: 100%;
  min-width: 0;
  min-height: 40px;
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
  min-height: 36px;
}
.field-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 10px;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}
.proposal {
  font-weight: 700;
  color: var(--text-secondary, var(--text));
}
.saved {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--tone-ok-fg);
  font-size: var(--fs-xs);
  font-weight: 700;
}
.saved :deep(svg) {
  inline-size: 0.875rem;
  block-size: 0.875rem;
}
.assertion-provenance {
  min-width: 0;
  font-size: var(--fs-sm);
}
.assertion-provenance summary {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  min-height: 28px;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: var(--fs-sm);
  font-weight: 600;
}
.assertion-provenance[open] {
  padding: 4px 10px 10px;
  border-radius: var(--radius-control);
  background: var(--surface-inset, var(--soft));
}
.assertion-disputed {
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: var(--fs-xs);
}
.assertion-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(125px, 1fr));
  gap: 7px 12px;
  margin: 6px 0 0;
}
.assertion-facts div {
  min-width: 0;
}
.assertion-facts dt {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
}
.assertion-facts dd {
  margin: 2px 0 0;
  overflow-wrap: anywhere;
  font-size: var(--fs-sm);
  font-weight: 650;
}
.assertion-reason,
.assertion-evidence-count {
  margin: 8px 0 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: 1.45;
}
.assertion-alternatives {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px solid var(--border-subtle);
  font-size: var(--fs-sm);
}
.assertion-alternatives ul {
  display: grid;
  gap: 5px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.assertion-alternatives li {
  display: grid;
  gap: 1px;
}
.assertion-alternatives small {
  color: var(--text-tertiary);
}
.link-button {
  border: 0;
  background: none;
  color: var(--accent-fg);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.btn.quiet {
  border-color: transparent;
  background: transparent;
}
.btn.quiet:hover:not(:disabled) {
  background: var(--surface-hover);
}
:is(button, input, select, summary):focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.blind-note {
  margin: 0;
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--tone-info-border);
  border-radius: 8px;
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: var(--fs-sm);
}
.memory-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.memory-hints > small {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
}
.hint-chip {
  padding: 1px 10px;
  border: 1px dashed var(--border-interactive);
  border-radius: var(--radius-pill);
  color: var(--text-secondary);
  background: var(--surface-card);
  font-size: var(--fs-sm);
  cursor: pointer;
}
.hint-chip:hover:not(:disabled) {
  color: var(--accent-fg);
  border-style: solid;
}
.hint-chip small {
  color: var(--text-tertiary);
}
@container metadata-field (max-width: 32rem) {
  .field-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .field-row .field-current {
    grid-column: 1 / -1;
    grid-row: 2;
  }
  .editor-actions .btn {
    flex: 1 1 auto;
  }
}
@media (prefers-reduced-motion: no-preference) {
  .metadata-field[data-mode="edit"] {
    transition:
      border-color var(--motion-base, 120ms) var(--ease-standard, ease),
      box-shadow var(--motion-base, 120ms) var(--ease-standard, ease);
  }
}
</style>
