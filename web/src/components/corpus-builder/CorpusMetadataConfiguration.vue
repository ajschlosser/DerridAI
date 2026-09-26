<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import type { SchemaSummary } from "../../api/metadataSchemas";
import type {
  RunGuidanceEntry,
  RunGuidanceField,
} from "../CorpusRunGuidance.vue";
import { useI18nStore } from "../../stores/i18n";
import CorpusRunGuidance from "../CorpusRunGuidance.vue";

const props = defineProps<{
  schemaChoices: SchemaSummary[];
  chosenSchema?: SchemaSummary | null;
  runGuidanceFields: RunGuidanceField[];
  disabled?: boolean;
}>();

const emit = defineEmits<{ manageSchemas: [] }>();
const schemaId = defineModel<string>("schemaId", { required: true });
const runGuidance = defineModel<Record<string, RunGuidanceEntry>>("runGuidance", {
  required: true,
});
const i18n = useI18nStore();

const schemaSummary = computed(() => {
  const schema = props.chosenSchema;
  if (!schema) return i18n.t("schemas.builtin");
  return `${schema.name} · ${i18n.tf("schemas.field_count", {
    count: schema.field_count,
  })}`;
});
</script>

<template>
  <section
    id="corpus-config-panel-metadata"
    class="metadata-configuration-workspace"
    role="tabpanel"
    aria-labelledby="corpus-config-tab-metadata"
  >
    <details class="setup-section setup-disclosure" open>
      <summary>
        <span>
          <b>{{ i18n.t("schemas.title") }}</b>
          <small>{{ schemaSummary }}</small>
        </span>
      </summary>
      <div class="setup-disclosure-body schema-choice">
        <label class="schema-choice-field">
          <span>{{ i18n.t("schemas.choose") }}</span>
          <select v-model="schemaId" class="control" :disabled="props.disabled">
            <option v-for="item in props.schemaChoices" :key="item.id" :value="item.id">
              {{ item.name }}{{ item.builtin ? ` (${i18n.t("schemas.builtin")})` : "" }}
            </option>
          </select>
          <small>{{ i18n.t("schemas.choose_help") }}</small>
        </label>
        <button type="button" class="btn small" @click="emit('manageSchemas')">
          {{ i18n.t("schemas.manage") }}
        </button>
      </div>
    </details>

    <details class="setup-section setup-disclosure" open>
      <summary>
        <span>
          <b>{{ i18n.t("pdf_corpus.run_guidance_title") }}</b>
          <small>{{ i18n.t("pdf_corpus.run_guidance_summary") }}</small>
        </span>
      </summary>
      <div class="setup-disclosure-body">
        <CorpusRunGuidance
          v-model="runGuidance"
          :fields="props.runGuidanceFields"
          :disabled="props.disabled"
        />
      </div>
    </details>
  </section>
</template>

<style scoped>
.metadata-configuration-workspace {
  display: grid;
}
.setup-disclosure {
  overflow: visible;
  border-top: 1px solid var(--border-subtle);
}
.setup-disclosure > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 54px;
  padding: var(--space-3) 0;
}
.setup-disclosure > summary::-webkit-details-marker {
  display: none;
}
.setup-disclosure > summary > span:last-child {
  display: grid;
  gap: 2px;
}
.setup-disclosure > summary b {
  font-size: 0.9375rem;
}
.setup-disclosure > summary small {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 500;
}
.setup-disclosure[open] > summary {
  border-bottom: 1px solid var(--border-subtle);
}
.setup-disclosure-body {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4) 0 var(--space-5);
}
.schema-choice {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
}
.schema-choice-field {
  display: grid;
  gap: 4px;
  flex: 1 1 16rem;
  font-size: 0.8125rem;
  font-weight: 700;
}
.schema-choice-field small {
  color: var(--muted);
  font-weight: 500;
}
@media (max-width: 620px) {
  .setup-disclosure-body {
    padding: 13px;
  }
  .setup-disclosure > summary {
    padding: 11px 13px;
  }
}
</style>
