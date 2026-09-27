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

function percent(item: MetadataPrecedent): number | null {
  return typeof item.similarity === "number"
    ? Math.max(0, Math.min(100, Math.round(item.similarity * 100)))
    : null;
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
      class="field-precedents-toggle"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="toggle"
    >
      <svg class="chevron" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <path
          d="M6 3.5 10.5 8 6 12.5"
          fill="none"
          stroke="currentColor"
          stroke-width="1.75"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
      <span class="toggle-label">
        {{ i18n.tf("pdf_corpus.precedents_toggle", { field: fieldLabel }) }}
      </span>
      <span v-if="result && result.items.length" class="toggle-count">
        {{ i18n.tf("pdf_corpus.precedents_count", { count: result.items.length }) }}
      </span>
    </button>
    <div v-if="open" :id="panelId" class="field-precedents-panel">
      <p class="field-precedents-note">{{ i18n.t("pdf_corpus.precedents_advisory") }}</p>
      <div v-if="loading" class="field-precedents-skeleton" role="status">
        <span class="sr-only">{{ i18n.t("pdf_corpus.precedents_loading") }}</span>
        <span aria-hidden="true" class="skeleton-card" />
        <span aria-hidden="true" class="skeleton-card" />
      </div>
      <div v-else-if="error" role="alert" class="field-precedents-error">
        <span>{{ i18n.tf("pdf_corpus.precedents_error", { detail: error }) }}</span>
        <button type="button" class="btn small" @click="fetchPrecedents">
          {{ i18n.t("pdf_corpus.precedents_retry") }}
        </button>
      </div>
      <template v-else-if="result">
        <p v-if="result.fallback_reason" role="status" class="field-precedents-callout">
          {{ i18n.tf("pdf_corpus.precedents_fallback", { detail: result.fallback_reason }) }}
        </p>
        <p v-else-if="modeNote" class="field-precedents-note field-precedents-mode">
          {{ modeNote }}
        </p>
        <p v-if="!result.items.length" role="status" class="field-precedents-empty">
          {{ i18n.t("pdf_corpus.precedents_empty") }}
        </p>
        <ol v-else class="field-precedents-list">
          <li
            v-for="item in result.items"
            :key="item.exemplar_id || `${item.record_id}:${display(item.value)}`"
            class="precedent-card"
            :data-kind="item.kind || 'positive'"
          >
            <div class="precedent-head">
              <UiStatusBadge :label="kindLabel(item).label" :tone="kindLabel(item).tone" />
              <span
                v-if="percent(item) !== null"
                class="precedent-similarity"
                :title="i18n.tf('pdf_corpus.precedent_similarity', { percent: percent(item) })"
              >
                <span class="meter" aria-hidden="true">
                  <span class="meter-fill" :style="{ width: `${percent(item)}%` }" />
                </span>
                <span>{{
                  i18n.tf("pdf_corpus.precedent_similarity", { percent: percent(item) })
                }}</span>
              </span>
            </div>
            <div v-if="item.kind === 'correction'" class="precedent-correction">
              <span class="precedent-label">{{ i18n.t("pdf_corpus.precedent_model_said") }}</span>
              <s class="precedent-rejected">{{ display(item.rejected_value) }}</s>
              <span class="precedent-label">
                {{ i18n.t("pdf_corpus.precedent_reviewer_chose") }}
              </span>
              <strong class="precedent-value">{{ display(item.value) }}</strong>
            </div>
            <strong v-else-if="item.kind === 'absence'" class="precedent-value is-absence">
              {{ i18n.t("pdf_corpus.precedent_no_value_label") }}
            </strong>
            <strong v-else class="precedent-value">{{ display(item.value) }}</strong>
            <p v-if="item.match" class="precedent-match">
              {{ i18n.tf("pdf_corpus.precedent_match", { fields: item.match.fields.join(", ") }) }}
            </p>
            <blockquote v-if="item.evidence || item.excerpt" class="precedent-evidence">
              {{ item.evidence || item.excerpt }}
            </blockquote>
            <p class="precedent-source">
              {{
                i18n.tf("pdf_corpus.precedent_source", {
                  record: item.record_id,
                  revision: item.record_revision ?? "—",
                })
              }}
              <span v-if="!item.evidence_bound" class="precedent-unbound">
                {{ i18n.t("pdf_corpus.precedent_not_evidence_bound") }}
              </span>
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
  display: inline-flex;
  gap: 6px;
  align-items: center;
  justify-self: start;
  padding: 4px 8px 4px 4px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--accent-fg);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
}
.field-precedents-toggle:hover {
  background: var(--surface-hover);
}
.field-precedents-toggle:focus-visible {
  outline: 2px solid var(--accent-fg);
  outline-offset: 2px;
}
.chevron {
  flex: none;
  transition: transform 0.15s ease;
}
.field-precedents-toggle[aria-expanded="true"] .chevron {
  transform: rotate(90deg);
}
.toggle-count {
  padding: 0 7px;
  border-radius: 999px;
  background: var(--surface-selected);
  color: var(--accent-fg);
  font-size: 0.75rem;
  font-weight: 600;
}
.field-precedents-panel {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-inset);
}
.field-precedents-note {
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
  line-height: 1.45;
}
.field-precedents-mode {
  font-style: italic;
}
.field-precedents-callout {
  margin: 0;
  padding: 6px 10px;
  border: 1px solid var(--tone-warn-border);
  border-radius: 6px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
}
.field-precedents-empty {
  margin: 0;
  padding: 12px;
  border: 1px dashed var(--line);
  border-radius: 8px;
  color: var(--muted);
  font-size: 0.8125rem;
  text-align: center;
}
.field-precedents-error {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid var(--tone-danger-border);
  border-radius: 6px;
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
}
.field-precedents-skeleton {
  display: grid;
  gap: 8px;
}
.skeleton-card {
  display: block;
  height: 64px;
  border-radius: 8px;
  background: linear-gradient(
    90deg,
    var(--surface-disabled),
    var(--surface-hover),
    var(--surface-disabled)
  );
  background-size: 200% 100%;
  animation: precedent-shimmer 1.4s ease-in-out infinite;
}
@keyframes precedent-shimmer {
  to {
    background-position: -200% 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton-card {
    animation: none;
  }
  .chevron {
    transition: none;
  }
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.field-precedents-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.precedent-card {
  display: grid;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-inline-start: 3px solid var(--tone-info-border);
  border-radius: 8px;
  background: var(--surface-card);
}
.precedent-card[data-kind="correction"] {
  border-inline-start-color: var(--tone-warn-border);
}
.precedent-card[data-kind="absence"] {
  border-inline-start-color: var(--muted);
}
.precedent-head {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  align-items: center;
  justify-content: space-between;
}
.precedent-similarity {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  color: var(--muted);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
}
.meter {
  width: 48px;
  height: 4px;
  border-radius: 999px;
  background: var(--line);
  overflow: hidden;
}
.meter-fill {
  display: block;
  height: 100%;
  background: var(--accent-fg);
}
.precedent-value {
  font-size: 1rem;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.precedent-value.is-absence {
  color: var(--muted);
  font-style: italic;
  font-weight: 600;
}
.precedent-correction {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 8px;
  align-items: baseline;
}
.precedent-label {
  color: var(--muted);
  font-size: 0.75rem;
}
.precedent-rejected {
  color: var(--muted);
  font-size: 0.875rem;
}
.precedent-match,
.precedent-source {
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
}
.precedent-unbound {
  margin-inline-start: 6px;
  padding: 0 6px;
  border: 1px solid var(--tone-warn-border);
  border-radius: 999px;
  color: var(--tone-warn-fg);
}
.precedent-evidence {
  margin: 0;
  padding: 2px 0 2px 10px;
  border-inline-start: 2px solid var(--line);
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
</style>
