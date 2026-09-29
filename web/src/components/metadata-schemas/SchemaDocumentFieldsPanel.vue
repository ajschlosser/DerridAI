<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import {
  completeDocumentFields,
  type DocumentFieldPolicy,
  type DocumentRequirement,
  type MetadataSchema,
} from "../../api/metadataSchemas";

// Policy for the bibliographic fields DerridAI owns: what a missing value blocks. Each holds one value for the
// whole corpus; values are detected on source load, and a person is asked only for required ones detection missed. The fields themselves cannot be added or renamed.
const props = defineProps<{ draft: MetadataSchema; readonly: boolean }>();
const { t } = useSchemaCopy();

// The editor completes drafts when it loads them; this only guards a draft handed over directly.
const policies = computed<DocumentFieldPolicy[]>(
  () => props.draft.document_fields ?? completeDocumentFields(),
);
const requirements: DocumentRequirement[] = ["evidence", "publication"];
function toggleRequirement(
  policy: DocumentFieldPolicy,
  requirement: DocumentRequirement,
  on: boolean,
) {
  const current = new Set(policy.required_for);
  if (on) current.add(requirement);
  else current.delete(requirement);
  policy.required_for = requirements.filter((r) => current.has(r));
}
</script>

<template>
  <!-- eslint-disable vue/no-mutating-props -->
  <div class="document-fields-panel">
    <p class="intro">{{ t("document_fields_intro") }}</p>
    <div class="table-frame">
      <table class="document-fields-table">
        <thead>
          <tr>
            <th scope="col">{{ t("document_field", "Field") }}</th>
            <th v-for="r in requirements" :key="r" scope="col">
              {{ t(`required_for_${r}`) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="policy in policies" :key="policy.name">
            <th scope="row">
              {{ t(`document_field.${policy.name}`, policy.name) }} <code>{{ policy.name }}</code>
            </th>
            <td v-for="r in requirements" :key="r">
              <input
                type="checkbox"
                :checked="policy.required_for.includes(r)"
                :disabled="readonly"
                :aria-label="`${t(`document_field.${policy.name}`, policy.name)}: ${t(`required_for_${r}`)}`"
                @change="toggleRequirement(policy, r, ($event.target as HTMLInputElement).checked)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.document-fields-panel {
  display: grid;
  gap: 10px;
}
.intro {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.table-frame {
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-overlay);
  background: var(--surface-card);
}
.document-fields-table {
  inline-size: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--fs-sm);
}
.document-fields-table th,
.document-fields-table td {
  padding: 8px 10px;
  border-block-end: 1px solid var(--border-subtle);
  text-align: start;
  vertical-align: middle;
}
.document-fields-table tbody tr:last-child > * {
  border-block-end: 0;
}
.document-fields-table thead th {
  color: var(--text-secondary);
  font-weight: 600;
}
.document-fields-table tbody th {
  font-weight: 500;
}
code {
  padding: 1px 6px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--surface-inset);
  font-size: var(--fs-xs);
}
</style>
