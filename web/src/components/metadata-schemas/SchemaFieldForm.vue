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
/* eslint-disable vue/no-mutating-props -- the parent hands over its draft on purpose; these components edit it in place and the parent tracks dirtiness by comparing the whole draft. */
import { computed, useId } from "vue";
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import { NER_TAG_OPTIONS, UNIVERSAL_POS_TAG_OPTIONS } from "../../domain/nlpTags";
import type {
  EquivalenceMode,
  SchemaField,
  SchemaFieldRole,
  SchemaFieldScope,
  SchemaMember,
  SchemaReviewVisibility,
} from "../../api/metadataSchemas";
import UiButton from "../ui/UiButton.vue";
import UiCheckbox from "../ui/UiCheckbox.vue";
import UiField from "../ui/UiField.vue";
import UiInput from "../ui/UiInput.vue";
import UiSelect from "../ui/UiSelect.vue";
import UiTagPicker from "../ui/UiTagPicker.vue";
import UiTextarea from "../ui/UiTextarea.vue";

// Everything one metadata field can say: identity, how it is reviewed, how the model is told to fill it,
// and whether reviewed precedents are retrieved for it. The parent owns the draft; this edits it in place.
const props = defineProps<{
  field: SchemaField;
  groupKeys: string[];
  /** Other fields this field's retrieval policy may require precedents to agree on. */
  matchOptions?: { fieldId: string; label: string }[];
}>();
const { t } = useSchemaCopy();
const baseId = useId();
const matchTitleId = `${baseId}-match-fields`;
const matchingNoteId = `${baseId}-matching-note`;
const kindHelpId = `${baseId}-kind-help`;
const id = (suffix: string) => `${baseId}-${suffix}`;

const MATCHING_MODES: EquivalenceMode[] = [
  "exact",
  "text",
  "entity_name",
  "lexical_phrase",
  "controlled",
];

/** "" means the field has no policy of its own and follows DerridAI's default for it. */
const matchingMode = computed(() => props.field.equivalence_profile?.mode ?? "");

function setMatchingMode(mode: string) {
  if (!mode) {
    props.field.equivalence_profile = null;
    return;
  }
  props.field.equivalence_profile = {
    collection_semantics: "set",
    identity_kind: null,
    ...props.field.equivalence_profile,
    mode: mode as EquivalenceMode,
  };
}
function setMatchingOrder(order: string) {
  if (props.field.equivalence_profile)
    props.field.equivalence_profile.collection_semantics = order === "ordered" ? "ordered" : "set";
}
function setIdentityKind(kind: string) {
  if (props.field.equivalence_profile)
    props.field.equivalence_profile.identity_kind = kind.trim() || null;
}
function setFieldRole(role: string) {
  props.field.role = role as SchemaFieldRole;
}
function setFieldScope(scope: string) {
  props.field.scope = scope as SchemaFieldScope;
}
function setReviewVisibility(visibility: string) {
  props.field.review_visibility = visibility as SchemaReviewVisibility;
}
function setMemberType(member: SchemaMember, type: string) {
  member.type = type as SchemaMember["type"];
}

const posTagOptions = computed(() =>
  UNIVERSAL_POS_TAG_OPTIONS.map((option) => ({
    ...option,
    label: t(`pos_tag.${option.value.toLowerCase()}`, option.label),
  })),
);
const nerTagOptions = computed(() =>
  NER_TAG_OPTIONS.map((option) => ({
    ...option,
    label: t(`ner_tag.${option.value.toLowerCase()}`, option.label),
  })),
);

function toggleMatch(fieldId: string, checked: boolean) {
  const current = new Set(props.field.retrieval_profile.match_field_ids || []);
  if (checked) current.add(fieldId);
  else current.delete(fieldId);
  props.field.retrieval_profile.match_field_ids = [...current];
}

const addValue = () => props.field.values.push({ value: "", definition: "" });

function addMember() {
  props.field.members ||= [];
  props.field.members.push({
    field_id: `member-${crypto.randomUUID()}`,
    name: "",
    label: "",
    type: "text",
    values: [],
    strict: false,
    instruction: "",
    evidence: false,
    assess: false,
    review: false,
    pos_tags: [],
    ner_tags: [],
  });
}

function setFieldType(type: string) {
  props.field.type = type as SchemaField["type"];
  if (type === "repeatable") {
    props.field.members ||= [];
    props.field.max_items ||= 8;
    props.field.instance_label ||= "{label} {number}";
  } else {
    props.field.members = [];
    props.field.max_items = null;
  }
}

const memberValuesText = (member: SchemaMember) =>
  member.values.map((value) => value.value).join(", ");

function setMemberValues(member: SchemaMember, text: string) {
  member.values = text
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .map((value) => ({ value, definition: "" }));
}
</script>

<template>
  <!-- eslint-disable vue/no-mutating-props -->
  <div class="field-form">
    <section class="config-section" :aria-labelledby="id('basics-heading')">
      <header class="section-heading">
        <h4 :id="id('basics-heading')">{{ t("block_identity", "Identity") }}</h4>
        <p>{{ t("field_identity_help", "Define what the field is, where its value lives, and how it appears during review.") }}</p>
      </header>

      <div class="form-grid">
        <UiField :label="t('field_name', 'Field name')" :control-id="id('name')">
          <UiInput
            :id="id('name')"
            v-model="field.name"
            maxlength="40"
            spellcheck="false"
            autocomplete="off"
          />
        </UiField>
        <UiField :label="t('field_label', 'Label')" :control-id="id('label')">
          <UiInput :id="id('label')" v-model="field.label" maxlength="80" />
        </UiField>
        <UiField :label="t('field_type', 'Type')" :control-id="id('type')">
          <UiSelect
            :id="id('type')"
            :model-value="field.type"
            @update:model-value="setFieldType"
          >
            <option value="text">{{ t("type_text", "Text") }}</option>
            <option value="number">{{ t("type_number", "Number") }}</option>
            <option value="boolean">{{ t("type_boolean", "Yes / no") }}</option>
            <option value="choice">{{ t("type_choice", "One of a list") }}</option>
            <option value="list">{{ t("type_list", "List of texts") }}</option>
            <option value="repeatable">{{ t("type_repeatable", "Repeatable structured field") }}</option>
          </UiSelect>
        </UiField>
        <UiField :label="t('field_group', 'Group')" :control-id="id('group')">
          <UiSelect :id="id('group')" v-model="field.group">
            <option v-for="key in groupKeys" :key="key" :value="key">{{ key }}</option>
          </UiSelect>
        </UiField>
        <UiField
          :label="t('field_role', 'Role')"
          :hint="t('field_role_summary')"
          :tooltip="t('field_role_help')"
          :control-id="id('role')"
        >
          <UiSelect
            :id="id('role')"
            :model-value="field.role || 'scholarly'"
            @update:model-value="setFieldRole"
          >
            <option value="scholarly">{{ t("role_scholarly", "Scholarly metadata") }}</option>
            <option value="structural">{{ t("role_structural", "Structural metadata") }}</option>
            <option value="document">{{ t("role_document", "Document metadata") }}</option>
            <option value="operational">{{ t("role_operational", "Operational / utility") }}</option>
          </UiSelect>
        </UiField>
        <UiField
          :label="t('field_scope', 'Where the value lives')"
          :hint="t('field_scope_summary')"
          :tooltip="t('field_scope_help')"
          :control-id="id('scope')"
        >
          <UiSelect
            :id="id('scope')"
            :model-value="field.scope || 'record'"
            @update:model-value="setFieldScope"
          >
            <option value="record">{{ t("scope_record", "On each record") }}</option>
            <option value="corpus">{{ t("scope_corpus", "Once for the corpus") }}</option>
          </UiSelect>
        </UiField>
        <UiField
          :label="t('review_visibility', 'Record review visibility')"
          :hint="t('review_visibility_summary')"
          :tooltip="t('review_visibility_help')"
          :control-id="id('visibility')"
        >
          <UiSelect
            :id="id('visibility')"
            :model-value="field.review_visibility || 'primary'"
            @update:model-value="setReviewVisibility"
          >
            <option value="primary">{{ t("visibility_primary", "Show in review") }}</option>
            <option value="details">{{ t("visibility_details", "Show in details") }}</option>
            <option value="hidden">{{ t("visibility_hidden", "Hidden") }}</option>
          </UiSelect>
        </UiField>
      </div>
    </section>

    <section class="config-section" :aria-labelledby="id('extraction-heading')">
      <header class="section-heading">
        <h4 :id="id('extraction-heading')">{{ t("instruction", "What the model should look for") }}</h4>
        <p>{{ t("instruction_help") }}</p>
      </header>

      <UiField :label="t('instruction', 'What the model should look for')" :control-id="id('instruction')" wide>
        <UiTextarea :id="id('instruction')" v-model="field.instruction" rows="3" />
      </UiField>

      <div v-if="field.type === 'choice'" class="values">
        <h5>{{ t("allowed_values", "Allowed values") }}</h5>
        <div v-for="(value, valueIndex) in field.values" :key="valueIndex" class="value-row">
          <UiInput
            v-model="value.value"
            :aria-label="t('value', 'Allowed value')"
            maxlength="80"
          />
          <UiInput
            v-model="value.definition"
            :aria-label="t('definition', 'What it means (optional)')"
            :placeholder="t('definition', 'What it means (optional)')"
          />
          <UiButton
            icon-only
            icon="trash"
            size="small"
            :label="t('remove', 'Remove')"
            @click="field.values.splice(valueIndex, 1)"
          />
        </div>
        <div class="values-foot">
          <UiButton size="small" icon="plus" :label="t('add_value', 'Add a value')" @click="addValue" />
          <UiCheckbox
            v-model="field.strict"
            :label="t('strict', 'The model may only return these values')"
            :description="t('strict_help')"
          />
        </div>
      </div>

      <div v-if="field.type === 'repeatable'" class="repeatable-editor">
        <div class="form-grid">
          <UiField :label="t('repeatable_max_items', 'Maximum instances')" :control-id="id('max-items')">
            <UiInput
              :id="id('max-items')"
              :model-value="field.max_items ?? 8"
              type="number"
              min="1"
              max="24"
              @update:model-value="field.max_items = Number($event ?? 8)"
            />
          </UiField>
          <UiField :label="t('repeatable_instance_label', 'Instance label pattern')" :control-id="id('instance-label')">
            <UiInput :id="id('instance-label')" v-model="field.instance_label" maxlength="120" />
          </UiField>
        </div>

        <div v-for="(member, memberIndex) in field.members" :key="member.field_id" class="member-card">
          <div class="member-grid">
            <UiInput v-model="member.name" :aria-label="t('field_name', 'Field name')" />
            <UiInput v-model="member.label" :aria-label="t('field_label', 'Label')" />
            <UiSelect
              :model-value="member.type"
              :aria-label="t('field_type', 'Type')"
              @update:model-value="setMemberType(member, $event)"
            >
              <option value="text">{{ t("type_text", "Text") }}</option>
              <option value="number">{{ t("type_number", "Number") }}</option>
              <option value="boolean">{{ t("type_boolean", "Yes / no") }}</option>
              <option value="choice">{{ t("type_choice", "One of a list") }}</option>
              <option value="list">{{ t("type_list", "List of texts") }}</option>
            </UiSelect>
            <UiInput
              v-if="member.type === 'choice'"
              :model-value="memberValuesText(member)"
              :aria-label="t('allowed_values', 'Allowed values')"
              :placeholder="t('allowed_values', 'Allowed values')"
              @update:model-value="setMemberValues(member, String($event ?? ''))"
            />
            <UiInput
              v-model="member.instruction"
              :aria-label="t('instruction', 'What the model should look for')"
              :placeholder="t('instruction', 'What the model should look for')"
            />
          </div>
          <div class="member-options">
            <UiCheckbox
              v-if="member.type === 'choice'"
              v-model="member.strict"
              :label="t('strict', 'The model may only return these values')"
            />
            <UiCheckbox v-model="member.evidence" :label="t('evidence', 'Must cite the source')" />
            <UiCheckbox v-model="member.assess" :label="t('assess', 'Report its confidence')" />
            <UiCheckbox
              v-model="member.review"
              :label="t('review', 'A person must settle it before accepting')"
            />
            <UiButton
              icon-only
              icon="trash"
              size="small"
              :label="t('remove', 'Remove')"
              @click="field.members?.splice(memberIndex, 1)"
            />
          </div>
        </div>
        <UiButton
          size="small"
          icon="plus"
          :label="t('add_repeatable_member', 'Add member field')"
          @click="addMember"
        />
      </div>
    </section>

    <section class="config-section" :aria-labelledby="id('policy-heading')">
      <header class="section-heading">
        <h4 :id="id('policy-heading')">{{ t("field_policy", "Field policy") }}</h4>
        <p>{{ t("field_policy_help", "Choose the evidence, confidence, and human-review requirements for this field.") }}</p>
      </header>
      <div class="policy-grid">
        <UiCheckbox
          v-model="field.evidence"
          :label="t('evidence', 'Must cite the source')"
          :description="t('evidence_help')"
        />
        <UiCheckbox
          v-model="field.assess"
          :label="t('assess', 'Report its confidence')"
          :description="t('assess_help')"
        />
        <UiCheckbox
          v-model="field.review"
          :label="t('review', 'A person must settle it before accepting')"
          :description="t('review_help')"
        />
      </div>
    </section>

    <details class="advanced-section">
      <summary>{{ t("linguistic_guidance", "Linguistic guidance") }}</summary>
      <p class="section-note">{{ t("linguistic_guidance_help", "Optional POS and named-entity hints narrow which spans DerridAI should consider for this field.") }}</p>
      <div class="nlp-hints">
        <UiField
          :label="t('pos_tags', 'POS tags (optional)')"
          :tooltip="t('pos_tags_help')"
          :control-id="id('pos-tags')"
        >
          <template #default="{ describedby, invalid }">
            <UiTagPicker
              v-model="field.pos_tags"
              :options="posTagOptions"
              :label="t('pos_tags', 'POS tags (optional)')"
              :input-id="id('pos-tags')"
              :describedby="describedby"
              :invalid="invalid"
              :placeholder="t('pos_tags_placeholder', 'Search POS tags…')"
              :remove-label="t('remove_tag', 'Remove {value}')"
            />
          </template>
        </UiField>
        <UiField
          :label="t('ner_tags', 'NER tags (optional)')"
          :tooltip="t('ner_tags_help')"
          :control-id="id('ner-tags')"
        >
          <template #default="{ describedby, invalid }">
            <UiTagPicker
              v-model="field.ner_tags"
              :options="nerTagOptions"
              :label="t('ner_tags', 'NER tags (optional)')"
              :input-id="id('ner-tags')"
              :describedby="describedby"
              :invalid="invalid"
              :placeholder="t('ner_tags_placeholder', 'Search NER tags…')"
              :remove-label="t('remove_tag', 'Remove {value}')"
            />
          </template>
        </UiField>
      </div>
    </details>

    <details class="advanced-section">
      <summary>{{ t("value_matching", "Value matching") }}</summary>
      <p :id="matchingNoteId" class="section-note">
        {{ t(`value_matching_${matchingMode || "default"}_note`) }}
      </p>
      <div class="matching-controls">
        <UiField
          :label="t('value_matching_mode', 'Treat two values as the same when they match as')"
          :control-id="id('matching-mode')"
        >
          <UiSelect
            :id="id('matching-mode')"
            :model-value="matchingMode"
            :aria-describedby="matchingNoteId"
            @update:model-value="setMatchingMode"
          >
            <option value="">{{ t("value_matching_default", "DerridAI default for this field") }}</option>
            <option v-for="mode in MATCHING_MODES" :key="mode" :value="mode">
              {{ t(`value_matching_${mode}`) }}
            </option>
          </UiSelect>
        </UiField>
        <UiField
          v-if="field.equivalence_profile && field.type === 'list'"
          :label="t('value_matching_order', 'List order')"
          :control-id="id('matching-order')"
        >
          <UiSelect
            :id="id('matching-order')"
            :model-value="field.equivalence_profile.collection_semantics ?? 'set'"
            @update:model-value="setMatchingOrder"
          >
            <option value="set">{{ t("value_matching_order_set", "Order does not matter") }}</option>
            <option value="ordered">{{ t("value_matching_order_ordered", "Order matters") }}</option>
          </UiSelect>
        </UiField>
        <UiField
          v-if="field.equivalence_profile"
          :label="t('value_matching_kind', 'Identity kind (optional)')"
          :hint="t('value_matching_kind_help')"
          :control-id="id('identity-kind')"
        >
          <UiInput
            :id="id('identity-kind')"
            type="text"
            maxlength="120"
            pattern="[a-z][a-z0-9_.\-]*"
            spellcheck="false"
            autocomplete="off"
            :model-value="field.equivalence_profile.identity_kind ?? ''"
            :aria-describedby="kindHelpId"
            @update:model-value="setIdentityKind(String($event ?? ''))"
          />
        </UiField>
      </div>
    </details>

    <details class="advanced-section">
      <summary>{{ t("memory", "Memory & retrieval") }}</summary>
      <p class="section-note">{{ t("memory_intro") }}</p>
      <UiCheckbox
        v-model="field.retrieval_profile.enabled"
        :label="t('memory_enabled', 'Show the model past reviewed examples')"
        :description="t('memory_enabled_help')"
      />
      <div class="memory-details">
        <UiCheckbox
          v-model="field.retrieval_profile.include_corrections"
          :disabled="!field.retrieval_profile.enabled"
          :label="t('memory_corrections', 'Learn from corrections')"
          :description="t('memory_corrections_help')"
        />
        <UiCheckbox
          v-model="field.retrieval_profile.include_confirmed_absence"
          :disabled="!field.retrieval_profile.enabled"
          :label="t('memory_absence', 'Learn from “no value” decisions')"
          :description="t('memory_absence_help')"
        />
        <UiField
          :label="t('memory_limit', 'Most examples to show')"
          :tooltip="t('memory_limit_help')"
          :control-id="id('memory-limit')"
        >
          <UiInput
            :id="id('memory-limit')"
            :model-value="field.retrieval_profile.max_items"
            type="number"
            min="0"
            max="50"
            :disabled="!field.retrieval_profile.enabled"
            @update:model-value="field.retrieval_profile.max_items = Number($event ?? 0)"
          />
        </UiField>
        <UiField
          :label="t('memory_similarity', 'How alike an example must be')"
          :tooltip="t('memory_similarity_help')"
          :control-id="id('memory-similarity')"
        >
          <UiInput
            :id="id('memory-similarity')"
            :model-value="field.retrieval_profile.min_similarity"
            type="number"
            min="0"
            max="1"
            step="0.05"
            :disabled="!field.retrieval_profile.enabled"
            @update:model-value="field.retrieval_profile.min_similarity = Number($event ?? 0)"
          />
        </UiField>
        <UiField
          :label="t('memory_max_corrections', 'Maximum corrections')"
          :tooltip="t('memory_max_corrections_help')"
          :control-id="id('memory-corrections-limit')"
        >
          <UiInput
            :id="id('memory-corrections-limit')"
            :model-value="field.retrieval_profile.max_corrections ?? 0"
            type="number"
            min="0"
            max="20"
            :disabled="!field.retrieval_profile.enabled || !field.retrieval_profile.include_corrections"
            @update:model-value="field.retrieval_profile.max_corrections = Number($event ?? 0)"
          />
        </UiField>
      </div>

      <div class="match-fields" role="group" :aria-labelledby="matchTitleId">
        <h5 :id="matchTitleId">{{ t("memory_match_fields", "Prefer precedents that agree on") }}</h5>
        <p class="section-note">{{ t("memory_match_fields_help") }}</p>
        <p v-if="!matchOptions?.length" class="section-note">
          {{ t("memory_match_none", "No other fields are available to compare.") }}
        </p>
        <div v-else class="match-fields-grid">
          <UiCheckbox
            v-for="option in matchOptions"
            :key="option.fieldId"
            :model-value="(field.retrieval_profile.match_field_ids || []).includes(option.fieldId)"
            :disabled="!field.retrieval_profile.enabled"
            :label="option.label"
            @update:model-value="toggleMatch(option.fieldId, $event)"
          />
        </div>
      </div>
    </details>
  </div>
</template>

<style scoped>
.field-form {
  display: grid;
  gap: var(--space-4);
}
.config-section,
.advanced-section {
  min-inline-size: 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.config-section {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
}
.section-heading {
  display: grid;
  gap: var(--space-1);
}
.section-heading h4,
.section-heading p,
.section-note,
.match-fields h5 {
  margin: 0;
}
.section-heading h4,
.match-fields h5 {
  font-size: var(--fs-base);
}
.section-heading p,
.section-note {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.form-grid,
.matching-controls,
.nlp-hints,
.memory-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(15rem, 100%), 1fr));
  gap: var(--space-4);
}
.policy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(14rem, 100%), 1fr));
  gap: var(--space-3) var(--space-5);
}
.values,
.repeatable-editor {
  display: grid;
  gap: var(--space-3);
}
.values h5 {
  margin: 0;
  font-size: var(--fs-sm);
}
.value-row {
  display: grid;
  grid-template-columns: minmax(7rem, 0.65fr) minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: center;
}
.values-foot {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-5);
  align-items: flex-start;
}
.member-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.member-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(11rem, 100%), 1fr));
  gap: var(--space-2);
}
.member-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  align-items: flex-start;
}
.advanced-section {
  overflow: clip;
}
.advanced-section > summary {
  min-block-size: var(--control-height);
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
  font-size: var(--fs-base);
  font-weight: var(--fw-bold);
  cursor: pointer;
}
.advanced-section > summary:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: calc(var(--focus-ring-offset) * -1);
}
.advanced-section[open] > summary {
  border-block-end: 1px solid var(--border-subtle);
  background: var(--surface-inset);
}
.advanced-section > :not(summary) {
  margin-inline: var(--space-4);
}
.advanced-section > :last-child {
  margin-block-end: var(--space-4);
}
.advanced-section > .section-note {
  margin-block: var(--space-4) var(--space-3);
}
.matching-controls,
.nlp-hints,
.memory-details,
.match-fields {
  margin-block-start: var(--space-4);
}
.match-fields {
  display: grid;
  gap: var(--space-2);
}
.match-fields-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(13rem, 100%), 1fr));
  gap: var(--space-2) var(--space-4);
}
@media (max-width: 620px) {
  .value-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
