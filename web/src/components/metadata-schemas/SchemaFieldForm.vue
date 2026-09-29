<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
/* eslint-disable vue/no-mutating-props -- the parent hands over its draft on purpose; these components edit it in place and the parent tracks dirtiness by comparing the whole draft. */
import { computed, useId } from "vue";
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import { NER_TAG_OPTIONS, UNIVERSAL_POS_TAG_OPTIONS } from "../../domain/nlpTags";
import type { SchemaField } from "../../api/metadataSchemas";
import UiButton from "../ui/UiButton.vue";
import UiTagPicker from "../ui/UiTagPicker.vue";
import UiTooltip from "../ui/UiTooltip.vue";

// Everything one metadata field can say: identity, how it is reviewed, how the model is told to fill it, and
// whether reviewed precedents are retrieved for it. The parent owns the draft; this edits the field in place.
const props = defineProps<{
  field: SchemaField;
  groupKeys: string[];
  /** Other fields this field's retrieval policy may require precedents to agree on. */
  matchOptions?: { fieldId: string; label: string }[];
}>();
const { t } = useSchemaCopy();
const matchTitleId = useId();

const posTagOptions = computed(() =>
  UNIVERSAL_POS_TAG_OPTIONS.map((o) => ({
    ...o,
    label: t(`pos_tag.${o.value.toLowerCase()}`, o.label),
  })),
);
const nerTagOptions = computed(() =>
  NER_TAG_OPTIONS.map((o) => ({ ...o, label: t(`ner_tag.${o.value.toLowerCase()}`, o.label) })),
);
function toggleMatch(fieldId: string, checked: boolean) {
  const current = new Set(props.field.retrieval_profile.match_field_ids || []);
  if (checked) current.add(fieldId);
  else current.delete(fieldId);
  props.field.retrieval_profile.match_field_ids = [...current];
}
const addValue = () => props.field.values.push({ value: "", definition: "" });
</script>

<template>
  <!-- eslint-disable vue/no-mutating-props -->
  <div class="field-form">
    <section class="form-block" :aria-label="t('block_identity', 'Identity')">
      <label class="schema-field"
        ><span>{{ t("field_name", "Field name") }}</span
        ><input v-model="field.name" class="control" maxlength="40" spellcheck="false"
      /></label>
      <label class="schema-field"
        ><span>{{ t("field_label", "Label") }}</span
        ><input v-model="field.label" class="control" maxlength="80"
      /></label>
      <label class="schema-field"
        ><span>{{ t("field_type", "Type") }}</span>
        <select v-model="field.type" class="control">
          <option value="text">{{ t("type_text", "Text") }}</option>
          <option value="number">{{ t("type_number", "Number") }}</option>
          <option value="boolean">{{ t("type_boolean", "Yes / no") }}</option>
          <option value="choice">{{ t("type_choice", "One of a list") }}</option>
          <option value="list">{{ t("type_list", "List of texts") }}</option>
        </select></label
      >
      <label class="schema-field"
        ><span>{{ t("field_group", "Group") }}</span
        ><select v-model="field.group" class="control">
          <option v-for="key in groupKeys" :key="key" :value="key">{{ key }}</option>
        </select></label
      >
      <label class="schema-field"
        ><span>{{ t("field_role", "Role") }} <UiTooltip :text="t('field_role_help')" /></span
        ><select v-model="field.role" class="control">
          <option value="scholarly">{{ t("role_scholarly", "Scholarly metadata") }}</option>
          <option value="structural">{{ t("role_structural", "Structural metadata") }}</option>
          <option value="document">{{ t("role_document", "Document metadata") }}</option>
          <option value="operational">{{ t("role_operational", "Operational / utility") }}</option>
        </select></label
      >
      <label class="schema-field"
        ><span
          >{{ t("field_scope", "Where the value lives") }}
          <UiTooltip :text="t('field_scope_help')" /></span
        ><select v-model="field.scope" class="control">
          <option value="record">{{ t("scope_record", "On each record") }}</option>
          <option value="corpus">{{ t("scope_corpus", "Once for the corpus") }}</option>
        </select></label
      >
      <label class="schema-field"
        ><span
          >{{ t("review_visibility", "Record review visibility") }}
          <UiTooltip :text="t('review_visibility_help')" /></span
        ><select v-model="field.review_visibility" class="control">
          <option value="primary">{{ t("visibility_primary", "Show in review") }}</option>
          <option value="details">{{ t("visibility_details", "Show in details") }}</option>
          <option value="hidden">{{ t("visibility_hidden", "Hidden") }}</option>
        </select></label
      >
    </section>

    <label class="schema-field"
      ><span>{{ t("instruction", "What the model should look for") }}</span
      ><textarea v-model="field.instruction" class="control" rows="2"></textarea
      ><small class="hint">{{ t("instruction_help") }}</small></label
    >

    <div v-if="field.type === 'choice'" class="values">
      <h5>{{ t("allowed_values", "Allowed values") }}</h5>
      <div v-for="(value, vi) in field.values" :key="vi" class="value-row">
        <input
          v-model="value.value"
          class="control"
          :aria-label="t('value', 'Allowed value')"
          maxlength="80"
        />
        <input
          v-model="value.definition"
          class="control"
          :aria-label="t('definition', 'What it means (optional)')"
          :placeholder="t('definition', 'What it means (optional)')"
        />
        <UiButton
          icon-only
          icon="trash"
          size="small"
          :label="t('remove', 'Remove')"
          @click="field.values.splice(vi, 1)"
        />
      </div>
      <div class="values-foot">
        <UiButton
          size="small"
          icon="plus"
          :label="t('add_value', 'Add a value')"
          @click="addValue"
        />
        <label class="check"
          ><input v-model="field.strict" type="checkbox" /><span>
            {{ t("strict", "The model may only return these values") }}
            <UiTooltip :text="t('strict_help')" /> </span
        ></label>
      </div>
    </div>

    <fieldset class="form-block policy" :aria-label="t('field_policy', 'Field policy')">
      <label class="option"
        ><input v-model="field.evidence" type="checkbox" /><span class="option-copy"
          ><b>{{ t("evidence", "Must cite the source") }}</b
          ><small>{{ t("evidence_help") }}</small></span
        ></label
      >
      <label class="option"
        ><input v-model="field.assess" type="checkbox" /><span class="option-copy"
          ><b>{{ t("assess", "Report its confidence") }}</b
          ><small>{{ t("assess_help") }}</small></span
        ></label
      >
      <label class="option"
        ><input v-model="field.review" type="checkbox" /><span class="option-copy"
          ><b>{{ t("review", "A person must settle it before accepting") }}</b
          ><small>{{ t("review_help") }}</small></span
        ></label
      >
    </fieldset>

    <div class="nlp-hints">
      <label class="schema-field"
        ><span
          >{{ t("pos_tags", "POS tags (optional)") }} <UiTooltip :text="t('pos_tags_help')" /></span
        ><UiTagPicker
          v-model="field.pos_tags"
          :options="posTagOptions"
          :label="t('pos_tags', 'POS tags (optional)')"
          :placeholder="t('pos_tags_placeholder', 'Search POS tags…')"
          :remove-label="t('remove_tag', 'Remove {value}')"
        />
      </label>
      <label class="schema-field"
        ><span
          >{{ t("ner_tags", "NER tags (optional)") }} <UiTooltip :text="t('ner_tags_help')" /></span
        ><UiTagPicker
          v-model="field.ner_tags"
          :options="nerTagOptions"
          :label="t('ner_tags', 'NER tags (optional)')"
          :placeholder="t('ner_tags_placeholder', 'Search NER tags…')"
          :remove-label="t('remove_tag', 'Remove {value}')"
        />
      </label>
    </div>

    <fieldset class="schema-memory">
      <legend>
        {{ t("memory", "Memory & retrieval") }} <UiTooltip :text="t('memory_help')" />
      </legend>
      <p class="memory-intro">{{ t("memory_intro") }}</p>
      <label class="option">
        <input v-model="field.retrieval_profile.enabled" type="checkbox" />
        <span class="option-copy"
          ><b>{{ t("memory_enabled", "Show the model past reviewed examples") }}</b
          ><small>{{ t("memory_enabled_help") }}</small></span
        >
      </label>
      <div class="memory-details" :data-off="!field.retrieval_profile.enabled">
        <label class="option">
          <input
            v-model="field.retrieval_profile.include_corrections"
            type="checkbox"
            :disabled="!field.retrieval_profile.enabled"
          />
          <span class="option-copy"
            ><b>{{ t("memory_corrections", "Learn from corrections") }}</b
            ><small>{{ t("memory_corrections_help") }}</small></span
          >
        </label>
        <label class="option">
          <input
            v-model="field.retrieval_profile.include_confirmed_absence"
            type="checkbox"
            :disabled="!field.retrieval_profile.enabled"
          />
          <span class="option-copy"
            ><b>{{ t("memory_absence", "Learn from “no value” decisions") }}</b
            ><small>{{ t("memory_absence_help") }}</small></span
          >
        </label>
        <label class="num-field">
          <span>{{ t("memory_limit", "Most examples to show") }}</span>
          <input
            v-model.number="field.retrieval_profile.max_items"
            class="control"
            type="number"
            min="0"
            max="50"
            :disabled="!field.retrieval_profile.enabled"
          />
          <small class="hint">{{ t("memory_limit_help") }}</small>
        </label>
        <label class="num-field">
          <span>{{ t("memory_similarity", "How alike an example must be") }}</span>
          <input
            v-model.number="field.retrieval_profile.min_similarity"
            class="control"
            type="number"
            min="0"
            max="1"
            step="0.05"
            :disabled="!field.retrieval_profile.enabled"
          />
          <small class="hint">{{ t("memory_similarity_help") }}</small>
        </label>
        <label class="num-field">
          <span>{{ t("memory_max_corrections", "Maximum corrections") }}</span>
          <input
            v-model.number="field.retrieval_profile.max_corrections"
            class="control"
            type="number"
            min="0"
            max="20"
            :disabled="
              !field.retrieval_profile.enabled || !field.retrieval_profile.include_corrections
            "
          />
          <small class="hint">{{ t("memory_max_corrections_help") }}</small>
        </label>
      </div>
      <div class="match-fields" role="group" :aria-labelledby="matchTitleId">
        <span :id="matchTitleId" class="num-field"
          >{{ t("memory_match_fields", "Prefer precedents that agree on") }}
          <UiTooltip :text="t('memory_match_fields_help')"
        /></span>
        <p v-if="!matchOptions?.length" class="hint">
          {{ t("memory_match_none", "No other fields are available to compare.") }}
        </p>
        <label v-for="option in matchOptions" :key="option.fieldId" class="check">
          <input
            type="checkbox"
            :checked="(field.retrieval_profile.match_field_ids || []).includes(option.fieldId)"
            :disabled="!field.retrieval_profile.enabled"
            @change="toggleMatch(option.fieldId, ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ option.label }}</span>
        </label>
      </div>
    </fieldset>
  </div>
</template>

<style scoped>
.field-form {
  display: grid;
  gap: 14px;
  padding: 4px 0;
}
.form-block {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 10px 12px;
  margin: 0;
  padding: 0;
  border: 0;
}
.form-block.policy {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 10px 20px;
}
.schema-field {
  display: grid;
  gap: 4px;
  min-inline-size: 0;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.schema-field :is(input:not([type="checkbox"], [type="radio"]), select, textarea) {
  inline-size: 100%;
  font-weight: 500;
}
.hint {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  font-weight: 500;
}
.check {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: var(--fs-sm);
  font-weight: 500;
}
/* A checkbox stays checkbox-sized; the text beside it says what it does, so no tooltip is needed to decide. */
.option {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: var(--fs-sm);
  font-weight: 500;
}
.option input[type="checkbox"] {
  flex: none;
  inline-size: 1.125rem;
  block-size: 1.125rem;
  margin: 0.15rem 0 0;
  accent-color: var(--ui-accent, var(--accent));
}
.option-copy {
  display: grid;
  gap: 2px;
  min-inline-size: 0;
}
.option-copy b {
  font-weight: var(--fw-semibold);
}
.option-copy small {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.values {
  display: grid;
  gap: 6px;
}
.values h5 {
  margin: 0;
  font-size: var(--fs-sm);
}
.value-row {
  display: grid;
  grid-template-columns: minmax(6rem, 0.5fr) minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
}
.values-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  align-items: center;
}
.nlp-hints {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 10px 12px;
}
.schema-memory {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.schema-memory legend {
  padding: 0 4px;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.memory-intro {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}
.memory-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: 12px 20px;
  padding-inline-start: 28px;
}
.memory-details[data-off="true"] {
  opacity: 0.55;
}
.match-fields {
  display: flex;
  flex-wrap: wrap;
  grid-column: 1 / -1;
  gap: 6px 14px;
  align-items: center;
}
.match-fields > .num-field {
  flex-basis: 100%;
}
.num-field {
  display: grid;
  gap: 4px;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.control {
  min-block-size: 40px;
}
@media (max-width: 820px) {
  .value-row {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
