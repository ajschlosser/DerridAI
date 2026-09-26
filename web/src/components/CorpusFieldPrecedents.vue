<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import { corpusBuilderApi, type MetadataPrecedent, type MetadataPrecedents } from "../api/corpus";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";

// "Similar reviewed precedents" for one field: the same selection metadata enrichment
// uses, shown beside the source evidence. Read-only; loaded only when opened, and it
// can never set a value.
const props = withDefaults(
  defineProps<{
    buildId: string;
    recordId: string;
    field: string;
    fieldLabel: string;
    /** Injected for Storybook and tests; defaults to the corpus API. */
    load?: (buildId: string, recordId: string, field: string) => Promise<MetadataPrecedents>;
  }>(),
  { load: undefined },
);

const i18n = useI18nStore();
const panelId = useId();
const open = ref(false);
const loading = ref(false);
const error = ref("");
const result = ref<MetadataPrecedents | null>(null);

watch(
  () => [props.buildId, props.recordId, props.field],
  () => {
    result.value = null;
    error.value = "";
    if (open.value) void fetchPrecedents();
  },
);

async function fetchPrecedents() {
  loading.value = true;
  error.value = "";
  try {
    const load = props.load ?? corpusBuilderApi.precedents;
    result.value = await load(props.buildId, props.recordId, props.field);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

function toggle() {
  open.value = !open.value;
  if (open.value && !result.value && !loading.value) void fetchPrecedents();
}

const modeNote = computed(() => {
  const mode = result.value?.mode;
  if (mode === "semantic") return i18n.t("pdf_corpus.precedents_mode_semantic");
  if (mode === "lexical") return i18n.t("pdf_corpus.precedents_mode_lexical");
  return "";
});

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map(display).join(", ");
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function kindLabel(item: MetadataPrecedent): {
  label: string;
  tone: "info" | "warning" | "neutral";
} {
  if (item.kind === "correction")
    return { label: i18n.t("pdf_corpus.precedent_kind_correction"), tone: "warning" };
  if (item.kind === "absence")
    return { label: i18n.t("pdf_corpus.precedent_kind_absence"), tone: "neutral" };
  return { label: i18n.t("pdf_corpus.precedent_kind_positive"), tone: "info" };
}
</script>

<template>
  <section class="field-precedents">
    <button
      type="button"
      class="btn small field-precedents-toggle"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="toggle"
    >
      {{ i18n.tf("pdf_corpus.precedents_toggle", { field: fieldLabel }) }}
    </button>
    <div v-if="open" :id="panelId" class="field-precedents-panel">
      <p class="field-precedents-note">{{ i18n.t("pdf_corpus.precedents_advisory") }}</p>
      <p v-if="loading" role="status">{{ i18n.t("pdf_corpus.precedents_loading") }}</p>
      <p v-else-if="error" role="alert" class="field-precedents-error">
        {{ i18n.tf("pdf_corpus.precedents_error", { detail: error }) }}
      </p>
      <template v-else-if="result">
        <p v-if="result.fallback_reason" role="status" class="field-precedents-note">
          {{ i18n.tf("pdf_corpus.precedents_fallback", { detail: result.fallback_reason }) }}
        </p>
        <p v-else-if="modeNote" class="field-precedents-note">{{ modeNote }}</p>
        <p v-if="!result.items.length" role="status">{{ i18n.t("pdf_corpus.precedents_empty") }}</p>
        <ol v-else class="field-precedents-list">
          <li
            v-for="item in result.items"
            :key="item.exemplar_id || `${item.record_id}:${display(item.value)}`"
          >
            <div class="field-precedents-head">
              <UiStatusBadge :label="kindLabel(item).label" :tone="kindLabel(item).tone" />
              <strong v-if="item.kind === 'correction'">
                {{
                  i18n.tf("pdf_corpus.precedent_correction", {
                    rejected: display(item.rejected_value),
                    value: display(item.value),
                  })
                }}
              </strong>
              <strong v-else-if="item.kind !== 'absence'">{{ display(item.value) }}</strong>
              <span v-if="typeof item.similarity === 'number'" class="field-precedents-meta">
                {{
                  i18n.tf("pdf_corpus.precedent_similarity", {
                    percent: Math.round(item.similarity * 100),
                  })
                }}
              </span>
            </div>
            <p v-if="item.match" class="field-precedents-meta">
              {{ i18n.tf("pdf_corpus.precedent_match", { fields: item.match.fields.join(", ") }) }}
            </p>
            <blockquote class="field-precedents-evidence">
              {{ item.evidence || item.excerpt }}
            </blockquote>
            <p class="field-precedents-meta">
              {{
                i18n.tf("pdf_corpus.precedent_source", {
                  record: item.record_id,
                  revision: item.record_revision ?? "—",
                })
              }}
              <span v-if="!item.evidence_bound">
                · {{ i18n.t("pdf_corpus.precedent_not_evidence_bound") }}</span
              >
            </p>
          </li>
        </ol>
      </template>
    </div>
  </section>
</template>

<style scoped>
.field-precedents {
  display: grid;
  gap: 6px;
}
.field-precedents-toggle {
  justify-self: start;
}
.field-precedents-panel {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
}
.field-precedents-note,
.field-precedents-meta {
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
}
.field-precedents-error {
  margin: 0;
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
}
.field-precedents-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.field-precedents-head {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
  font-size: 0.8125rem;
}
.field-precedents-evidence {
  margin: 4px 0;
  padding: 4px 0 4px 10px;
  border-inline-start: 3px solid var(--line);
  font-size: 0.8125rem;
  overflow-wrap: anywhere;
}
</style>
