<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
/* eslint-disable vue/no-mutating-props -- the parent hands over its draft on purpose; these components edit it in place and the parent tracks dirtiness by comparing the whole draft. */
import { computed } from "vue";
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import { NER_TAG_OPTIONS, UNIVERSAL_POS_TAG_OPTIONS } from "../../domain/nlpTags";
import type { SchemaField } from "../../api/metadataSchemas";
import UiButton from "../ui/UiButton.vue";
import UiTagPicker from "../ui/UiTagPicker.vue";
import UiTooltip from "../ui/UiTooltip.vue";

// Everything one metadata field can say: identity, how it is reviewed, how the model is told to fill it, and
// whether reviewed precedents are retrieved for it. The parent owns the draft; this edits the field in place.
const props = defineProps<{ field: SchemaField; groupKeys: string[] }>();
const { t } = useSchemaCopy();

const posTagOptions = computed(() =>
  UNIVERSAL_POS_TAG_OPTIONS.map((o) => ({
    ...o,
    label: t(`pos_tag.${o.value.toLowerCase()}`, o.label),
  })),
);
const nerTagOptions = computed(() =>
  NER_TAG_OPTIONS.map((o) => ({ ...o, label: t(`ner_tag.${o.value.toLowerCase()}`, o.label) })),
);
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
      <label class="check"
        ><input v-model="field.evidence" type="checkbox" /><span>
          {{ t("evidence", "Must cite the source") }}
          <UiTooltip :text="t('evidence_help')" /> </span
      ></label>
      <label class="check"
        ><input v-model="field.assess" type="checkbox" /><span>
          {{ t("assess", "Report its confidence") }} <UiTooltip :text="t('assess_help')" /> </span
      ></label>
      <label class="check"
        ><input v-model="field.review" type="checkbox" /><span>
          {{ t("review", "A person must settle it before accepting") }}
          <UiTooltip :text="t('review_help')" /> </span
      ></label>
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

    <fieldset class="schema-field schema-memory">
      <legend>
        {{ t("memory", "Memory & retrieval") }} <UiTooltip :text="t('memory_help')" />
      </legend>
      <label class="check">
        <input v-model="field.retrieval_profile.enabled" type="checkbox" />
        <span
          >{{ t("memory_enabled", "Use reviewed precedents") }}
          <UiTooltip :text="t('memory_enabled_help')"
        /></span>
      </label>
      <label class="check">
        <input v-model="field.retrieval_profile.include_corrections" type="checkbox" />
        <span
          >{{ t("memory_corrections", "Include corrections") }}
          <UiTooltip :text="t('memory_corrections_help')"
        /></span>
      </label>
      <label class="check">
        <input v-model="field.retrieval_profile.include_confirmed_absence" type="checkbox" />
        <span
          >{{ t("memory_absence", "Include confirmed absence") }}
          <UiTooltip :text="t('memory_absence_help')"
        /></span>
      </label>
      <label class="num-field">
        <span
          >{{ t("memory_limit", "Maximum precedents") }} <UiTooltip :text="t('memory_limit_help')"
        /></span>
        <input
          v-model.number="field.retrieval_profile.max_items"
          class="control"
          type="number"
          min="0"
          max="50"
        />
      </label>
      <label class="num-field">
        <span
          >{{ t("memory_similarity", "Minimum similarity") }}
          <UiTooltip :text="t('memory_similarity_help')"
        /></span>
        <input
          v-model.number="field.retrieval_profile.min_similarity"
          class="control"
          type="number"
          min="0"
          max="1"
          step="0.05"
        />
      </label>
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
  display: flex;
  flex-wrap: wrap;
  gap: 6px 20px;
}
.schema-field {
  display: grid;
  gap: 4px;
  min-inline-size: 0;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.schema-field :is(input, select, textarea) {
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
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: 10px 16px;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
}
.schema-memory legend {
  padding: 0 4px;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
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
