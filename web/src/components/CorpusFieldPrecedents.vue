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
import { computed, onBeforeUnmount, ref, useId, watch } from "vue";
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
// metadata enrichment saw them. Kept precedents arrive with the record (`preloaded`), so their count is available
// before opening; otherwise they load on demand. "Use this value" fills a draft only, and candidate passages are
// always blocks from the record under review.
const props = withDefaults(
  defineProps<{
    buildId: string;
    recordId: string;
    recordRevision?: number;
    active?: boolean;
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
  { preloaded: null, sourceBlockIds: () => [], canUse: true, load: undefined, active: true },
);
const emit = defineEmits<{ use: [value: unknown] }>();

const i18n = useI18nStore();
const panelId = useId();
const open = ref(false);
const loading = ref(false);
const error = ref("");
const fetched = ref<MetadataPrecedents | null>(null);
const usedKey = ref("");
let requestVersion = 0;
const result = computed(() => fetched.value ?? props.preloaded ?? null);
// A closed disclosure whose known result (kept or fetched) has no precedents offers nothing; an open one keeps
// showing the reviewer's empty result instead of vanishing under them.
const isEmpty = computed(
  () => !open.value && Boolean(result.value && !result.value.items.length && !error.value),
);
const canRefresh = computed(() => result.value?.source !== "enrichment");

watch(
  // A primitive key so a poll re-rendering the same record does not discard loaded precedents.
  () => JSON.stringify([props.buildId, props.recordId, props.recordRevision, props.field]),
  () => {
    requestVersion += 1;
    loading.value = false;
    fetched.value = null;
    error.value = "";
    usedKey.value = "";
    if (props.active !== false && open.value && !props.preloaded) void fetchPrecedents(false);
  },
);
watch(
  () => props.active !== false,
  (active) => {
    if (!active) {
      requestVersion += 1;
      loading.value = false;
    } else if (open.value && !result.value && !loading.value) {
      void fetchPrecedents(false);
    }
  },
);

async function fetchPrecedents(refresh: boolean) {
  if (props.active === false) return;
  const version = ++requestVersion;
  loading.value = true;
  error.value = "";
  try {
    const load = props.load ?? corpusBuilderApi.precedents;
    const result = await load(props.buildId, props.recordId, props.field, refresh);
    if (version === requestVersion) fetched.value = result;
  } catch (exc) {
    if (version === requestVersion) error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    if (version === requestVersion) loading.value = false;
  }
}
onBeforeUnmount(() => (requestVersion += 1));

function toggle() {
  open.value = !open.value;
  if (open.value && !result.value && !loading.value) void fetchPrecedents(false);
}

// One compact status line: where the list came from, matching mode, and anything now stale.
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

const itemKey = (item: MetadataPrecedent) =>
  item.exemplar_id || `${item.record_id}:${display(item.value)}`;

function candidateLabel(unit: PrecedentCandidateUnit) {
  const score = Math.max(0, Math.min(100, Math.round(unit.score * 100)));
  const where = candidateLocation(unit, props.sourceBlockIds);
  if (where.kind === "page")
    return i18n.tf("pdf_corpus.precedent_candidate_page", { page: where.page, percent: score });
  if (where.kind === "time")
    return i18n.tf("pdf_corpus.precedent_candidate_time", {
      time: timeLabel(where.start, where.end),
      percent: score,
    });
  return i18n.tf("pdf_corpus.precedent_candidate_passage", { index: where.index, percent: score });
}

function useValue(item: MetadataPrecedent) {
  usedKey.value = itemKey(item);
  emit("use", item.value);
}
</script>

<template>
  <section v-if="!isEmpty" class="field-precedents">
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
      <span v-if="result" class="toggle-count">
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
        <button type="button" class="btn small" @click="fetchPrecedents(false)">
          {{ i18n.t("pdf_corpus.precedents_retry") }}
        </button>
      </div>
      <template v-else-if="result">
        <div class="field-precedents-status">
          <p
            v-if="statusParts.length || !result.items.length"
            role="status"
            :class="[
              'field-precedents-note',
              { 'field-precedents-callout': Boolean(result.fallback_reason) },
            ]"
          >
            <template v-if="!result.items.length">
              {{ i18n.t("pdf_corpus.precedents_empty") }}
              <span v-if="statusParts.length"> · </span>
            </template>
            {{ statusParts.join(" · ") }}
          </p>
          <button
            v-if="canRefresh"
            type="button"
            class="btn tiny"
            :disabled="loading"
            @click="fetchPrecedents(true)"
          >
            {{ i18n.t("pdf_corpus.precedents_refresh") }}
          </button>
        </div>
        <ol v-if="result.items.length" class="field-precedents-list">
          <li
            v-for="item in result.items"
            :key="itemKey(item)"
            class="precedent-card"
            :data-kind="item.kind || 'positive'"
          >
            <div class="precedent-head">
              <UiStatusBadge :label="kindLabel(item).label" :tone="kindLabel(item).tone" />
              <span
                v-if="percent(item) !== null"
                class="precedent-similarity"
                :title="i18n.tf('pdf_corpus.precedent_similarity', { percent: percent(item) ?? 0 })"
              >
                <span class="meter" aria-hidden="true">
                  <span class="meter-fill" :style="{ width: `${percent(item)}%` }" />
                </span>
                <span>{{
                  i18n.tf("pdf_corpus.precedent_similarity", { percent: percent(item) ?? 0 })
                }}</span>
              </span>
              <button
                v-if="canUse && item.kind !== 'absence'"
                type="button"
                class="btn small precedent-use"
                @click="useValue(item)"
              >
                {{ i18n.t("pdf_corpus.precedent_use") }}
              </button>
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
            <p v-if="usedKey === itemKey(item)" role="status" class="precedent-used">
              {{ i18n.t("pdf_corpus.precedent_used") }}
            </p>
            <p v-if="item.match" class="precedent-match">
              {{ i18n.tf("pdf_corpus.precedent_match", { fields: item.match.fields.join(", ") }) }}
            </p>
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
            <blockquote v-if="item.evidence || item.excerpt" class="precedent-evidence">
              {{ item.evidence || item.excerpt }}
            </blockquote>
            <p v-if="item.candidate_source_units?.length" class="precedent-candidates">
              <strong>{{ i18n.t("pdf_corpus.precedent_candidates") }}</strong>
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
.field-precedents-status {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
  justify-content: space-between;
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
.precedent-use {
  margin-inline-start: auto;
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
.precedent-source,
.precedent-used,
.precedent-candidates {
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
}
.precedent-used {
  color: var(--accent-fg);
}
.precedent-candidates strong {
  color: var(--text);
  font-weight: 600;
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
