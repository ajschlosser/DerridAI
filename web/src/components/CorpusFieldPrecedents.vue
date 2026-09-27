<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import {
  corpusBuilderApi,
  type MetadataPrecedent,
  type MetadataPrecedents,
  type PrecedentCandidateUnit,
} from "../api/corpus";
import { candidateLocation } from "../domain/metadataPrecedents";
import { timeLabel } from "../domain/sourceMedia";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";

// "Similar reviewed precedents" for one field: how reviewers decided it on similar evidence in other records, as
// metadata enrichment saw them. Kept precedents arrive with the record (`preloaded`), so the count shows without
// opening; otherwise they load when opened. Nothing here saves anything: "Use this value" only fills in the
// field, and the candidate passages are this record's own blocks for the reviewer to check.
const props = withDefaults(
  defineProps<{
    buildId: string;
    recordId: string;
    field: string;
    fieldLabel: string;
    /** This field's precedents kept from the last enrichment, when the record has them. */
    preloaded?: MetadataPrecedents | null;
    /** The record's block ids in reading order, for locating candidates that have no page or time. */
    sourceBlockIds?: string[];
    /** Offer "Use this value"; off where the field cannot be edited. */
    canUse?: boolean;
    /** Injected for Storybook and tests; defaults to the corpus API. */
    load?: (
      buildId: string,
      recordId: string,
      field: string,
      refresh?: boolean,
    ) => Promise<MetadataPrecedents>;
  }>(),
  { preloaded: null, sourceBlockIds: () => [], canUse: true, load: undefined },
);
const emit = defineEmits<{ use: [value: unknown] }>();

const i18n = useI18nStore();
const panelId = useId();
const open = ref(false);
const loading = ref(false);
const error = ref("");
const fetched = ref<MetadataPrecedents | null>(null);
const usedKey = ref("");
const result = computed(() => fetched.value ?? props.preloaded ?? null);

watch(
  () => [props.buildId, props.recordId, props.field],
  () => {
    fetched.value = null;
    error.value = "";
    usedKey.value = "";
    if (open.value && !props.preloaded) void fetchPrecedents(false);
  },
);

async function fetchPrecedents(refresh: boolean) {
  loading.value = true;
  error.value = "";
  try {
    const load = props.load ?? corpusBuilderApi.precedents;
    fetched.value = await load(props.buildId, props.recordId, props.field, refresh);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

function toggle() {
  open.value = !open.value;
  if (open.value && !result.value && !loading.value) void fetchPrecedents(false);
}

const toggleLabel = computed(() =>
  result.value
    ? i18n.tf("pdf_corpus.precedents_toggle_count", {
        field: props.fieldLabel,
        count: result.value.items.length,
      })
    : i18n.tf("pdf_corpus.precedents_toggle", { field: props.fieldLabel }),
);

// One status line: where the list came from, how it was matched, and what is hidden.
const statusParts = computed(() => {
  const current = result.value;
  if (!current) return [];
  const parts: string[] = [];
  if (current.source === "enrichment") {
    const when = current.computed_at ? new Date(current.computed_at) : null;
    parts.push(
      i18n.tf("pdf_corpus.precedents_kept", {
        time: when && !Number.isNaN(when.getTime()) ? when.toLocaleString() : "—",
      }),
    );
  }
  if (current.fallback_reason)
    parts.push(i18n.tf("pdf_corpus.precedents_fallback", { detail: current.fallback_reason }));
  else if (current.mode === "semantic") parts.push(i18n.t("pdf_corpus.precedents_mode_semantic"));
  else if (current.mode === "lexical") parts.push(i18n.t("pdf_corpus.precedents_mode_lexical"));
  if (current.stale_count)
    parts.push(i18n.tf("pdf_corpus.precedents_stale", { count: current.stale_count }));
  return parts;
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

const itemKey = (item: MetadataPrecedent) =>
  item.exemplar_id || `${item.record_id}:${display(item.value)}`;

function candidateLabel(unit: PrecedentCandidateUnit) {
  const percent = Math.round(unit.score * 100);
  const where = candidateLocation(unit, props.sourceBlockIds);
  if (where.kind === "page")
    return i18n.tf("pdf_corpus.precedent_candidate_page", { page: where.page, percent });
  if (where.kind === "time")
    return i18n.tf("pdf_corpus.precedent_candidate_time", {
      time: timeLabel(where.start, where.end),
      percent,
    });
  return i18n.tf("pdf_corpus.precedent_candidate_passage", { index: where.index, percent });
}

function useValue(item: MetadataPrecedent) {
  usedKey.value = itemKey(item);
  emit("use", item.value);
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
      {{ toggleLabel }}
    </button>
    <div v-if="open" :id="panelId" class="field-precedents-panel">
      <p class="field-precedents-note">{{ i18n.t("pdf_corpus.precedents_advisory") }}</p>
      <p v-if="loading" role="status">{{ i18n.t("pdf_corpus.precedents_loading") }}</p>
      <p v-else-if="error" role="alert" class="field-precedents-error">
        {{ i18n.tf("pdf_corpus.precedents_error", { detail: error }) }}
      </p>
      <template v-else-if="result">
        <div class="field-precedents-status">
          <p role="status" class="field-precedents-note">
            <template v-if="!result.items.length"
              >{{ i18n.t("pdf_corpus.precedents_empty") }}
            </template>
            {{ statusParts.join(" · ") }}
          </p>
          <button type="button" class="btn tiny" :disabled="loading" @click="fetchPrecedents(true)">
            {{ i18n.t("pdf_corpus.precedents_refresh") }}
          </button>
        </div>
        <ol v-if="result.items.length" class="field-precedents-list">
          <li v-for="item in result.items" :key="itemKey(item)">
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
              <button
                v-if="canUse && item.kind !== 'absence'"
                type="button"
                class="btn small field-precedents-use"
                @click="useValue(item)"
              >
                {{ i18n.t("pdf_corpus.precedent_use") }}
              </button>
            </div>
            <p v-if="usedKey === itemKey(item)" role="status" class="field-precedents-meta">
              {{ i18n.t("pdf_corpus.precedent_used") }}
            </p>
            <p v-if="item.match" class="field-precedents-meta">
              {{ i18n.tf("pdf_corpus.precedent_match", { fields: item.match.fields.join(", ") }) }}
            </p>
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
            <blockquote class="field-precedents-evidence">
              {{ item.evidence || item.excerpt }}
            </blockquote>
            <p v-if="item.candidate_source_units?.length" class="field-precedents-meta">
              {{ i18n.t("pdf_corpus.precedent_candidates") }}
              {{ item.candidate_source_units.map(candidateLabel).join(", ") }}
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
.field-precedents-status {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
  justify-content: space-between;
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
.field-precedents-use {
  margin-inline-start: auto;
}
.field-precedents-evidence {
  margin: 4px 0;
  padding: 4px 0 4px 10px;
  border-inline-start: 3px solid var(--line);
  font-size: 0.8125rem;
  overflow-wrap: anywhere;
}
</style>
