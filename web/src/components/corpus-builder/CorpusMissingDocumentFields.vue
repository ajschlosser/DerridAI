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
import { useId } from "vue";
import type { MissingDocumentField } from "../../domain/documentFields";
import { useI18nStore } from "../../stores/i18n";
import UiField from "../ui/UiField.vue";
import UiInput from "../ui/UiInput.vue";
import UiSelect from "../ui/UiSelect.vue";

// Shown only when detection on source load could not fill a document field the schema requires. The values apply
// to every record of the corpus; leaving one empty does not block the build, the gap stays visible in review.
const props = defineProps<{ fields: MissingDocumentField[]; disabled?: boolean }>();
const values = defineModel<Record<string, string>>({ required: true });
const i18n = useI18nStore();
const controlIdPrefix = useId();

const label = (name: string) => i18n.t(`schemas.document_field.${name}`, name);
const controlId = (name: string) =>
  `${controlIdPrefix}-${name.replace(/[^A-Za-z0-9_-]/g, "-")}`;
const requirement = (field: MissingDocumentField) =>
  field.requiredFor.map((r) => i18n.t(`schemas.required_for_${r}`)).join(" · ");
function update(name: string, value: string) {
  values.value = { ...values.value, [name]: value };
}
</script>

<template>
  <section
    v-if="props.fields.length"
    class="missing-document-fields"
    aria-labelledby="missing-document-fields-title"
  >
    <h3 id="missing-document-fields-title">
      {{ i18n.t("pdf_corpus.missing_document_fields_title") }}
    </h3>
    <p class="help">{{ i18n.t("pdf_corpus.missing_document_fields_help") }}</p>
    <div class="fields">
      <UiField
        v-for="field in props.fields"
        :key="field.name"
        class="field"
        :label="label(field.name)"
        :hint="requirement(field)"
        :control-id="controlId(field.name)"
      >
        <UiSelect
          v-if="field.name === 'document_is_translation'"
          :id="controlId(field.name)"
          :model-value="values[field.name] ?? ''"
          :disabled="props.disabled"
          @update:model-value="update(field.name, String($event))"
        >
          <option value="">{{ i18n.t("pdf_corpus.missing_document_field_unknown") }}</option>
          <option value="true">{{ i18n.t("common.yes") }}</option>
          <option value="false">{{ i18n.t("common.no") }}</option>
        </UiSelect>
        <UiInput
          v-else
          :id="controlId(field.name)"
          :model-value="values[field.name] ?? ''"
          :disabled="props.disabled"
          :inputmode="field.name === 'publication_year' ? 'numeric' : undefined"
          @update:model-value="update(field.name, String($event ?? ''))"
        />
      </UiField>
    </div>
  </section>
</template>

<style scoped>
.missing-document-fields {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: var(--radius-overlay);
  background: var(--tone-warn-bg);
}
h3 {
  margin: 0;
  font-size: var(--fs-md);
}
.help {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 10px 14px;
}
.field {
  min-width: 0;
}
</style>
