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
import type { MissingDocumentField } from "../../domain/documentFields";
import { useI18nStore } from "../../stores/i18n";

// Shown only when detection on source load could not fill a document field the schema requires. The values apply
// to every record of the corpus; leaving one empty does not block the build, the gap stays visible in review.
const props = defineProps<{ fields: MissingDocumentField[]; disabled?: boolean }>();
const values = defineModel<Record<string, string>>({ required: true });
const i18n = useI18nStore();

const label = (name: string) => i18n.t(`schemas.document_field.${name}`, name);
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
      <label v-for="field in props.fields" :key="field.name" class="field">
        <span class="field-label">{{ label(field.name) }}</span>
        <select
          v-if="field.name === 'document_is_translation'"
          class="control"
          :value="values[field.name] ?? ''"
          :disabled="props.disabled"
          @change="update(field.name, ($event.target as HTMLSelectElement).value)"
        >
          <option value="">{{ i18n.t("pdf_corpus.missing_document_field_unknown") }}</option>
          <option value="true">{{ i18n.t("common.yes") }}</option>
          <option value="false">{{ i18n.t("common.no") }}</option>
        </select>
        <input
          v-else
          class="control"
          :value="values[field.name] ?? ''"
          :disabled="props.disabled"
          :inputmode="field.name === 'publication_year' ? 'numeric' : undefined"
          @input="update(field.name, ($event.target as HTMLInputElement).value)"
        />
        <small class="requirement">{{ requirement(field) }}</small>
      </label>
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
  display: grid;
  gap: 4px;
}
.field-label {
  font-weight: 600;
  font-size: var(--fs-sm);
}
.requirement {
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
}
</style>
