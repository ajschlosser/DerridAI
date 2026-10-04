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
import { computed, ref, useId, watch } from "vue";
import { useI18nStore } from "../stores/i18n";
import AppIcon from "./AppIcon.vue";
import CorpusFieldOwnershipBadge from "./CorpusFieldOwnershipBadge.vue";
import CorpusActionMenu, { type CorpusActionMenuItem } from "./CorpusActionMenu.vue";
import UiCombobox from "./ui/UiCombobox.vue";
import UiTooltip from "./ui/UiTooltip.vue";
import { normalizeMetadataFieldValue } from "../domain/metadataFieldRegistry";
import { activeValueEditor } from "../domain/focus";
import {
  groupOptionsBySuggestion,
  matchOption,
  suggestedValues,
} from "../domain/metadataSuggestion";
import { useRecordTextSelection } from "../composables/useRecordTextSelection";
import CorpusFieldSelectionPreview from "./CorpusFieldSelectionPreview.vue";
import {
  isPlaceholderValue,
  metadataValueText,
  unwrapMetadataValue,
  usableListOptions,
  withoutTransportItems,
} from "../domain/metadataValues";
import type { SchemaMember } from "../api/metadataSchemas";

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
  repeatableMembers?: SchemaMember[];
  repeatableMaxItems?: number;
  recheck?: { first: unknown; second: unknown; agreed: boolean };
  constraint?: { value: unknown; reason: string } | null;
  calibratedAcceptance?: { reviewed: number; acceptanceRate: number } | null;
  /** Less certain values earlier reviews attached to matching source spans. */
  hints?: { value: unknown; similarity: number; support: number }[];
  /** The server will not accept the record until this field is decided. */
  requiredToAccept?: boolean;
  /** How many reviewed examples the model's prompt carried for this field (metadata memory), if any. */
  memoryExamples?: number;
  /** A value to put in the draft (a reviewed precedent's); a new `key` applies it again. Never saved by itself. */
  prefill?: { value: unknown; key: number } | null;
}>();
const emit = defineEmits<{
  save: [value: unknown];
  noValue: [];
  source: [];
  saveWithSelectionEvidence: [value: unknown, text: string];
  /** The reviewer's own knowledge is the source; no span is cited. */
  saveWithHumanSource: [value: unknown, note: string];
  /** Open the browser for citing units elsewhere in the source. */
  browseEvidence: [value: unknown];
  dirty: [dirty: boolean];
}>();
const i18n = useI18nStore();
const labelId = `${useId()}-label`;
const root = ref<HTMLElement | null>(null);
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
const usesCombobox = computed(() =>
  ["combobox", "multi-combobox", "text", "number"].includes(String(props.control)),
);
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
  if (Array.isArray(value)) {
    draft.value = isMultiCombobox.value
      ? value.join(", ")
      : value.length === 1
        ? value[0]
        : value.map((item) => metadataValueText(item)).join("\n");
  } else draft.value = value;
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
const modelSuggestion = computed(() => {
  const values = suggestedValues(props.status, props.value, isLlm.value, hasValue);
  return values.filter((value) => !isPlaceholderValue(value));
});
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
const modelPlaceholder = (value: unknown) => {
  const unwrapped = unwrapMetadataValue(value);
  return isLlm.value && typeof unwrapped === "string" && isPlaceholderValue(unwrapped);
};
const resolvedValue = computed(() => {
  const status = props.status || {};
  if (
    status.reason_code === "deterministic_llm_disagreement" &&
    status.prefilled_candidate === "llm" &&
    hasValue(status.llm_value) &&
    !modelPlaceholder(status.llm_value)
  )
    return normalizeMetadataFieldValue(props.field, status.llm_value);
  if (status.reason_code === "human_llm_disagreement" && hasValue(status.prefilled_value))
    return normalizeMetadataFieldValue(props.field, status.prefilled_value);
  if (
    hasValue(props.value) &&
    !(props.control === "multi-combobox" && leakedAssessment(props.value)) &&
    !modelPlaceholder(props.value)
  )
    return normalizeMetadataFieldValue(props.field, withoutTransportItems(props.value));
  // Backward compatibility for records created before populated-but-unverified
  // proposals were written into the record itself. Confidence affects review
  // state, not whether the reviewer may see the proposed value.
  if (!status.blind && hasValue(status.proposed_value) && !modelPlaceholder(status.proposed_value))
    return normalizeMetadataFieldValue(props.field, status.proposed_value);
  if (hasValue(props.constraint?.value))
    return normalizeMetadataFieldValue(props.field, props.constraint?.value);
  return normalizeMetadataFieldValue(
    props.field,
    modelPlaceholder(props.value)
      ? ""
      : props.control === "multi-combobox" && leakedAssessment(props.value)
        ? []
        : (props.value ?? ""),
  );
});
/**
 * Historical records may carry an array for a field whose current contract is
 * scalar. One-item arrays are losslessly compatible; multiple values require an
 * explicit reviewer decision instead of being silently joined into one string.
 */
const suggestedAbsence = computed(() => {
  const status = props.status || {};
  const placeholderReturned = [props.value, status.proposed_value, status.llm_value].some(
    modelPlaceholder,
  );
  return (
    !hasValue(resolvedValue.value) &&
    (placeholderReturned ||
      status.suggested_absence === true ||
      status.evaluation_status === "no_supported_value" ||
      status.reason_code === "no_supported_value" ||
      status.reason_code === "required_no_supported_value")
  );
});

const scalarCardinalityConflict = computed(() => {
  const value = unwrapMetadataValue(resolvedValue.value);
  return !isMultiCombobox.value && Array.isArray(value) && value.length > 1;
});
function editableValue() {
  if (props.repeatableMembers?.length)
    return Array.isArray(resolvedValue.value) ? structuredClone(resolvedValue.value) : [];
  const value = unwrapMetadataValue(resolvedValue.value);
  let text = metadataValueText(value);
  if (Array.isArray(value)) {
    if (isMultiCombobox.value) text = value.map((item) => metadataValueText(item)).join(", ");
    else if (value.length === 1) text = metadataValueText(value[0]);
    else text = value.map((item) => metadataValueText(item)).join("\n");
  }
  if (props.control !== "enum") return text;
  // A <select> only shows a draft that is exactly one of its options. Map the value onto
  // its option, and with no value preselect the model's suggestion (never a sealed one).
  const options = props.options || [];
  if (text) return matchOption(options, text) ?? text;
  return props.status?.blind ? "" : (suggestedOptions.value[0] ?? "");
}
function activeEditorInside() {
  const active = activeValueEditor();
  return Boolean(active && root.value?.contains(active));
}
watch(
  () => [
    props.field,
    props.value,
    props.status?.proposed_value,
    props.status?.llm_value,
    props.status?.prefilled_candidate,
    props.constraint?.value,
    props.options,
  ],
  () => {
    if (!dirty.value && !activeEditorInside()) draft.value = editableValue();
  },
  { immediate: true, deep: true },
);
watch(
  () => props.open,
  (value) => {
    if (value) {
      editing.value = true;
      if (!activeEditorInside()) {
        dirty.value = false;
        draft.value = editableValue();
      }
    } else if (!dirty.value && !activeEditorInside()) {
      // A pending field that has just been decided folds back into its one-line summary.
      editing.value = false;
    }
  },
);
function onFocusout(event: FocusEvent) {
  const next = event.relatedTarget;
  if (next instanceof Node && root.value?.contains(next)) return;
  if (!props.open && !dirty.value) editing.value = false;
}

watch(
  () => props.prefill?.key,
  (key) => {
    if (key !== undefined && props.prefill) useHint(props.prefill.value);
  },
);

/** The ★ that marks a suggested or auto-filled option is decoration; it must never reach a saved value. */
const stripStar = (value: string) => value.replace(/^\s*★\s*/u, "").trim();
function normalized() {
  if (props.repeatableMembers?.length) return draft.value;
  if (props.control === "multi-combobox")
    return [
      ...new Set(
        String(draft.value || "")
          .split(/[\n,]/)
          .map((v) => stripStar(v))
          .filter(Boolean),
      ),
    ];
  if (props.control === "number" && draft.value !== "") return Number(draft.value);
  const raw = typeof draft.value === "string" ? stripStar(draft.value) : draft.value;
  return normalizeMetadataFieldValue(props.field, raw);
}
function repeatableRows(): Array<Record<string, unknown>> {
  return Array.isArray(draft.value) ? (draft.value as Array<Record<string, unknown>>) : [];
}
function addRepeatableRow() {
  const row: Record<string, unknown> = { instance_id: `instance:${crypto.randomUUID()}` };
  for (const member of props.repeatableMembers || [])
    row[member.name] = member.type === "list" ? [] : null;
  draft.value = [...repeatableRows(), row];
  markDirty();
}
function removeRepeatableRow(index: number) {
  draft.value = repeatableRows().filter((_row, rowIndex) => rowIndex !== index);
  markDirty();
}
function setRepeatableValue(index: number, member: SchemaMember, value: string | boolean) {
  const rows = structuredClone(repeatableRows());
  rows[index][member.name] =
    member.type === "boolean"
      ? value
      : member.type === "number"
        ? value === ""
          ? null
          : Number(value)
        : member.type === "list"
          ? String(value)
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean)
          : value || null;
  draft.value = rows;
  markDirty();
}
const selectionMissing = ref(false);
const scalarCardinalityResolved = computed(
  () =>
    !scalarCardinalityConflict.value || (dirty.value && !String(draft.value ?? "").includes("\n")),
);
const canSave = computed(
  () =>
    !props.busy &&
    !props.saving &&
    scalarCardinalityResolved.value &&
    draft.value !== "" &&
    draft.value !== undefined &&
    !(props.required && draft.value === null),
);
const hasDraftValue = computed(() => hasValue(normalized()));
/** One confirm action: it cites the reviewer's own knowledge, the selected text, or nothing extra, in that order. */
function save() {
  if (!canSave.value) return;
  if (citeSelf.value) {
    emit("saveWithHumanSource", normalized(), selfNote.value.trim());
    citeSelf.value = false;
    selfNote.value = "";
  } else if (liveSelection.value) {
    saveWithSelection();
    return;
  } else emit("save", normalized());
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
  if (hasDraftValue.value) save();
  else if (!props.busy && !props.saving) emit("noValue");
}
function saveWithSelection() {
  if (!canSave.value) return;
  const selected = liveSelection.value || selectedRecordText();
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
const {
  selection: liveSelection,
  capture: selectedRecordText,
  clear: clearSelection,
  selectAll: selectWholeRecord,
} = useRecordTextSelection(editing);
const citeSelf = ref(false);
const selfNote = ref("");
const evidenceItems = computed<CorpusActionMenuItem[]>(() => [
  ...(textSelectable.value
    ? [{ id: "select-text", label: i18n.t("pdf_corpus.select_from_text") }]
    : []),
  { id: "select-all", label: i18n.t("pdf_corpus.select_all_evidence") },
  {
    id: "own-knowledge",
    label: citeSelf.value
      ? i18n.t("pdf_corpus.own_knowledge_cancel")
      : i18n.t("pdf_corpus.own_knowledge_toggle"),
  },
  {
    id: "browse",
    label: i18n.t("pdf_corpus.browse_evidence"),
    reason: canSave.value ? undefined : i18n.t("pdf_corpus.browse_evidence_needs_value"),
  },
  { id: "view", label: i18n.t("pdf_corpus.view_evidence") },
]);
function evidenceAction(id: string) {
  if (id === "select-text") selectFromText();
  else if (id === "select-all") selectWholeRecord();
  else if (id === "own-knowledge") citeSelf.value = !citeSelf.value;
  else if (id === "browse") browseOtherRecords();
  else emit("source");
}
function browseOtherRecords() {
  if (canSave.value) emit("browseEvidence", normalized());
}
const confirmLabelKey = computed(() =>
  citeSelf.value
    ? "pdf_corpus.confirm_own_knowledge"
    : liveSelection.value
      ? "pdf_corpus.confirm_with_evidence"
      : dirty.value || !hasValue(resolvedValue.value)
        ? "pdf_corpus.save_field_value"
        : "pdf_corpus.confirm_field_value",
);
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
/** Who or what proposed the current value, in words, including whether metadata memory shaped the model's answer. */
const sourceLabel = computed(() => {
  const status = props.status || {};
  if (String(status.derivation_method || "") === "derridai:memory")
    return i18n.t("pdf_corpus.derivation_memory");
  if (status.method === "human" || status.value_source === "human")
    return i18n.t("pdf_corpus.source_reviewer");
  if (!isLlm.value) return "";
  const examples = Number(props.memoryExamples || 0);
  return examples > 0
    ? i18n.tf("pdf_corpus.source_llm_memory", { count: examples })
    : i18n.t("pdf_corpus.source_llm_only");
});
const evidenceSummary = computed(() => {
  const evidence = (props.status as { evidence?: unknown } | undefined)?.evidence;
  return Array.isArray(evidence) ? evidence.length : 0;
});
/** The traceability matrix: every signal behind the value, each row shown only when it exists. */
const traceRows = computed(() => {
  const status = props.status || {};
  const rows: { label: string; value: string }[] = [];
  const add = (labelKey: string, value: unknown) => {
    const text = metadataValueText(value);
    if (text) rows.push({ label: i18n.t(labelKey), value: text });
  };
  add("pdf_corpus.trace_source", sourceLabel.value);
  if (hasValue(status.deterministic_value))
    add("pdf_corpus.trace_deterministic", display(status.deterministic_value));
  add("pdf_corpus.trace_deterministic_reason", status.deterministic_reason);
  if (hasValue(status.llm_value ?? (isLlm.value ? props.value : undefined)))
    add("pdf_corpus.trace_llm", display(status.llm_value ?? props.value));
  if (typeof status.llm_confidence === "number")
    add("pdf_corpus.trace_llm_confidence", `${Math.round(Number(status.llm_confidence) * 100)}%`);
  add("pdf_corpus.trace_llm_reason", status.llm_reason);
  if (props.memoryExamples)
    add(
      "pdf_corpus.trace_memory",
      i18n.tf("pdf_corpus.trace_memory_count", { count: props.memoryExamples }),
    );
  if (props.hints?.length)
    add("pdf_corpus.trace_memory_hint", props.hints.map((hint) => display(hint.value)).join(", "));
  add("pdf_corpus.trace_confidence", confidence.value === null ? "" : confidenceLabel.value);
  add("pdf_corpus.trace_verification", humanizeToken(verificationStatus.value));
  add("pdf_corpus.trace_status", humanizeToken(status.status));
  add("pdf_corpus.trace_reason", status.reason);
  if (status.autofilled === true) add("pdf_corpus.trace_autofilled", i18n.t("ui.yes"));
  if (evidenceSummary.value)
    add(
      "pdf_corpus.trace_evidence",
      i18n.tf("pdf_corpus.assertion_evidence_count", { count: evidenceSummary.value }),
    );
  add(
    "pdf_corpus.trace_checked",
    status.llm_checked === false ? String(status.llm_skip_reason || i18n.t("ui.no")) : "",
  );
  return rows;
});
</script>

<template>
  <article
    ref="root"
    class="metadata-field"
    :data-field="field"
    :data-mode="editing ? 'edit' : 'view'"
    :data-attention="
      status?.status === 'unresolved' || status?.status === 'invalid' ? 'true' : 'false'
    "
    :data-unresolved-field="open ? 'true' : undefined"
    :data-review-state="open ? 'pending' : 'settled'"
    :aria-labelledby="labelId"
    @keydown="onKeydown"
    @focusout="onFocusout"
  >
    <!-- A decided field is one line: what it is, its value, where the value came from. -->
    <div v-if="!editing" class="field-row">
      <span :id="labelId" class="field-label">{{ fieldLabel }}</span>
      <span class="field-current"
        >{{ suggestedAbsence ? i18n.t("pdf_corpus.no_value_short") : display(resolvedValue) }}
        <template v-if="autoResolved || suggestedAbsence"
          ><span class="auto-star" aria-hidden="true">★</span
          ><span class="sr-only">{{
            suggestedAbsence
              ? i18n.t("pdf_corpus.model_suggested_short")
              : i18n.t("pdf_corpus.auto_filled_marker")
          }}</span></template
        ></span
      >
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
        ><span v-if="open" class="field-review-state">{{
          i18n.t("pdf_corpus.verification.pending")
        }}</span
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
      <p v-if="scalarCardinalityConflict" class="field-reason" role="alert">
        {{ i18n.t("pdf_corpus.scalar_cardinality_conflict") }}
      </p>
      <div class="value-control">
        <div v-if="repeatableMembers?.length" class="repeatable-editor">
          <fieldset v-for="(row, index) in repeatableRows()" :key="String(row.instance_id)">
            <legend>{{ fieldLabel }} {{ index + 1 }}</legend>
            <label v-for="member in repeatableMembers" :key="member.field_id">
              <span>{{ member.name.toUpperCase() }}_{{ index + 1 }}</span>
              <input
                v-if="member.type !== 'boolean'"
                :type="member.type === 'number' ? 'number' : 'text'"
                :value="
                  member.type === 'list'
                    ? (row[member.name] as unknown[] | undefined)?.join(', ') || ''
                    : String(row[member.name] ?? '')
                "
                @input="
                  setRepeatableValue(index, member, ($event.target as HTMLInputElement).value)
                "
              />
              <select
                v-else
                :value="String(row[member.name] ?? '')"
                @change="
                  setRepeatableValue(
                    index,
                    member,
                    ($event.target as HTMLSelectElement).value === 'true',
                  )
                "
              >
                <option value=""></option>
                <option value="true">{{ i18n.t("ui.yes") }}</option>
                <option value="false">{{ i18n.t("ui.no") }}</option>
              </select>
            </label>
            <button type="button" class="btn small" @click="removeRepeatableRow(index)">
              {{ i18n.t("ui.remove") }}
            </button>
          </fieldset>
          <button
            type="button"
            class="btn small"
            :disabled="repeatableRows().length >= (repeatableMaxItems || 24)"
            @click="addRepeatableRow"
          >
            {{ i18n.t("pdf_corpus.add_metadata_instance") }}
          </button>
        </div>
        <select
          v-else-if="control === 'enum'"
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
        <!-- One combobox serves every free-value role: it wraps and grows for text and lists, and stays a
             one-line numeric input for numbers. Closed vocabularies keep the select above. -->
        <UiCombobox
          v-else-if="usesCombobox"
          :model-value="String(draft ?? '')"
          :options="autocompleteOptions"
          :recommended="modelSuggestion"
          :recommended-label="i18n.t('pdf_corpus.model_suggested_short')"
          :type="control === 'number' ? 'number' : 'text'"
          :label="fieldLabel"
          :multiple="isMultiCombobox"
          :multiline="control !== 'number'"
          :selected-label="i18n.t('pdf_corpus.combo_selected')"
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
          :data-primary-action="hasDraftValue ? '' : undefined"
          :disabled="!canSave"
          aria-keyshortcuts="Control+Enter Meta+Enter"
          @click="save"
        >
          {{ saving ? i18n.t("pdf_corpus.saving_decision") : i18n.t(confirmLabelKey)
          }}<kbd aria-hidden="true">{{ i18n.t("pdf_corpus.shortcut.confirm_field") }}</kbd>
        </button>
        <UiTooltip
          :text="i18n.t('pdf_corpus.confirm_no_value')"
          trigger-mode="content"
          :content-focusable="Boolean(busy)"
          placement="bottom"
        >
          <button
            type="button"
            class="btn small"
            data-no-value-action
            :data-primary-action="!hasDraftValue ? '' : undefined"
            :disabled="busy || saving"
            @keydown.enter.prevent.stop="emit('noValue')"
            @click="emit('noValue')"
          >
            {{ i18n.t("pdf_corpus.no_value_short") }}
          </button>
        </UiTooltip>
        <button v-if="!open" type="button" class="btn small quiet" @click="cancelEdit">
          {{ i18n.t("ui.cancel") }}
        </button>
      </div>
      <CorpusFieldSelectionPreview :selection="liveSelection" @clear="clearSelection" />
      <div v-if="citeSelf" class="cite-self">
        <label>
          <span>{{ i18n.t("pdf_corpus.own_knowledge_note") }}</span>
          <input
            v-model="selfNote"
            class="control"
            type="text"
            maxlength="500"
            :placeholder="i18n.t('pdf_corpus.own_knowledge_placeholder')"
          />
        </label>
        <small>{{ i18n.t("pdf_corpus.own_knowledge_help") }}</small>
      </div>
      <div class="field-tools">
        <CorpusActionMenu
          :label="i18n.t('pdf_corpus.cite_evidence_menu')"
          :menu-label="i18n.t('pdf_corpus.evidence_tools')"
          :items="evidenceItems"
          :disabled="busy"
          placement="bottom"
          @select="evidenceAction"
        />
      </div>
      <p v-if="selectionMissing" class="selection-help" role="alert">
        {{ i18n.t("pdf_corpus.select_text_first") }}
      </p>
      <div class="field-meta">
        <span v-if="suggestedAbsence" class="proposal">
          <span class="auto-star" aria-hidden="true">★</span>
          {{ i18n.t("pdf_corpus.no_value_short") }} ·
          {{ i18n.t("pdf_corpus.model_suggested_short") }}
        </span>
        <span v-else-if="isLlm && hasValue(resolvedValue)" class="proposal">{{
          autoResolved
            ? i18n.t("pdf_corpus.llm_value_auto_resolved")
            : i18n.t("pdf_corpus.llm_suggestion_prefilled")
        }}</span>
        <span
          v-if="status?.llm_assessed === true || status?.llm_checked === true"
          class="field-meta-help"
        >
          {{ i18n.t("pdf_corpus.llm_field_assessed") }}
          <UiTooltip :text="i18n.t('pdf_corpus.llm_field_assessed_help')" placement="bottom" />
        </span>
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
        <span class="field-meta-help">
          {{ confidenceLabel }}
          <UiTooltip :text="i18n.t('pdf_corpus.confidence_help')" placement="bottom" />
        </span>
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
            <dt class="assertion-term">
              <span>{{ i18n.t("pdf_corpus.assertion_derivation", "Derivation") }}</span>
              <UiTooltip
                :text="i18n.t('pdf_corpus.assertion_derivation_help')"
                placement="bottom"
              />
            </dt>
            <dd>{{ derivationLabel(status.derivation_method) }}</dd>
          </div>
          <div v-if="status?.evaluation_status">
            <dt class="assertion-term">
              <span>{{ i18n.t("pdf_corpus.assertion_evaluation", "Evaluation") }}</span>
              <UiTooltip
                :text="i18n.t('pdf_corpus.assertion_evaluation_help')"
                placement="bottom"
              />
            </dt>
            <dd>{{ humanizeToken(status.evaluation_status) }}</dd>
          </div>
          <div v-if="status?.authority_status">
            <dt class="assertion-term">
              <span>{{ i18n.t("pdf_corpus.assertion_authority", "Authority") }}</span>
              <UiTooltip :text="i18n.t('pdf_corpus.assertion_authority_help')" placement="bottom" />
            </dt>
            <dd>{{ humanizeToken(status.authority_status) }}</dd>
          </div>
          <div v-if="status?.value_status">
            <dt class="assertion-term">
              <span>{{ i18n.t("pdf_corpus.assertion_value_state", "Value state") }}</span>
              <UiTooltip
                :text="i18n.t('pdf_corpus.assertion_value_state_help')"
                placement="bottom"
              />
            </dt>
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
            <dt class="assertion-term">
              <span>{{ i18n.t("pdf_corpus.assertion_revision", "Record revision") }}</span>
              <UiTooltip :text="i18n.t('pdf_corpus.assertion_revision_help')" placement="bottom" />
            </dt>
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
    <!-- Available on every field, decided or not: why this value was suggested, by whom, and on what evidence. -->
    <details v-if="traceRows.length" class="trace-matrix">
      <summary>
        {{ i18n.t("pdf_corpus.trace_title") }}
        <span v-if="sourceLabel" class="trace-source">{{ sourceLabel }}</span>
      </summary>
      <dl class="trace-grid">
        <div v-for="row in traceRows" :key="row.label">
          <dt>{{ row.label }}</dt>
          <dd>{{ row.value }}</dd>
        </div>
      </dl>
    </details>
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
.metadata-field[data-mode="edit"][data-review-state="pending"],
.metadata-field[data-mode="edit"][data-attention="true"] {
  border-inline-start: 3px solid var(--tone-warn-border);
}
.metadata-field[data-mode="edit"][data-review-state="pending"] {
  background:
    linear-gradient(
      90deg,
      color-mix(in srgb, var(--tone-warn-bg) 38%, transparent),
      transparent 28%
    ),
    var(--surface-card);
}
.metadata-field[data-mode="edit"]:focus-within {
  border-color: var(--ui-accent, var(--accent));
  box-shadow: 0 0 0 1px var(--ui-accent, var(--accent));
}
.auto-star {
  color: var(--tone-info-fg);
  font-size: 0.9em;
}
.cite-self {
  display: grid;
  gap: 4px;
  padding: 8px 10px;
  border: 1px solid var(--tone-info-edge);
  border-radius: var(--radius-control);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: var(--fs-sm);
}
.cite-self label {
  display: grid;
  gap: 4px;
  font-weight: 700;
}
.trace-matrix {
  font-size: var(--fs-sm);
}
.trace-matrix summary {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  align-items: baseline;
  color: var(--text-secondary);
  cursor: pointer;
  font-weight: 700;
}
.trace-source {
  color: var(--tone-info-fg);
}
.trace-grid {
  display: grid;
  gap: 2px;
  margin: 6px 0 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
}
.trace-grid > div {
  display: grid;
  grid-template-columns: minmax(7rem, 0.5fr) minmax(0, 1fr);
  gap: 8px;
  padding: 4px 8px;
}
.trace-grid > div:nth-child(odd) {
  background: var(--surface-hover);
}
.trace-grid dt {
  color: var(--text-secondary);
  font-weight: 700;
}
.trace-grid dd {
  margin: 0;
  overflow-wrap: anywhere;
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
.field-review-state,
.field-required {
  font-size: var(--fs-xs);
  font-weight: 700;
}
.field-review-state {
  padding: 2px 7px;
  border: 1px solid var(--tone-warn-border);
  border-radius: 999px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.field-required {
  color: var(--tone-warn-fg);
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
.repeatable-editor,
.repeatable-editor fieldset,
.repeatable-editor label {
  display: grid;
  gap: 8px;
}
.repeatable-editor fieldset {
  margin: 0;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
}
.repeatable-editor label {
  grid-template-columns: minmax(10rem, auto) 1fr;
  align-items: center;
}
.repeatable-editor :is(input, select) {
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  color: var(--text);
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
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
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
.field-meta-help,
.assertion-term {
  display: inline-flex;
  align-items: center;
  gap: 4px;
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
