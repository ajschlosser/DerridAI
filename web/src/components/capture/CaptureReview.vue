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
import { computed } from "vue";
import type { CaptureCandidate, CorpusCapture } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { languageName } from "../../domain/languages";
import { enumLabel, enumTone } from "../../domain/sourceLabels";
import { groupCandidates } from "../../domain/captureReview";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

/**
 * Review what discovery found before anything is downloaded: coverage per library, counts, and
 * candidates grouped by work and then by language. Originals and translations stay separate rows;
 * every row keeps its own checkbox.
 */
const props = withDefaults(
  defineProps<{
    capture: CorpusCapture;
    candidates: CaptureCandidate[];
    busy?: boolean;
  }>(),
  { busy: false },
);
const emit = defineEmits<{ select: [ids: string[] | null, selected: boolean] }>();
const i18n = useI18nStore();
const t = (key: string, fallback?: string) => i18n.t(key, fallback);

const groups = computed(() =>
  groupCandidates(props.candidates, i18n.locale, i18n.t("sources.language_unknown")),
);
const selectedCount = computed(
  () => props.candidates.filter((item) => item.selection_status === "selected").length,
);
const summary = computed(() => props.capture.summary);
const counts = computed(() => [
  { key: "sources", value: summary.value.candidates },
  { key: "work_groups", value: summary.value.work_groups },
  { key: "languages", value: Object.keys(summary.value.languages || {}).length },
  { key: "translations", value: summary.value.translations },
  { key: "possible_duplicates", value: summary.value.possible_duplicates },
  { key: "needs_review", value: summary.value.needs_review },
]);
const languageCounts = computed(() =>
  Object.entries(summary.value.languages || {}).map(([code, count]) => ({
    code,
    count,
    label: code === "und" ? i18n.t("sources.language_unknown") : languageName(code, i18n.locale),
  })),
);
const providerCounts = computed(() =>
  Object.entries(summary.value.providers || {}).map(([provider, count]) => ({
    provider,
    count,
  })),
);

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(i18n.locale || undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}
const KNOWN_WARNINGS = [
  "gutenberg_catalogue_not_indexed_used_gutendex",
  "no_wikisource_sitelinks",
  "candidate_limit_reached",
  "non_text_items_skipped",
  "exact_provider_duplicates_removed",
  "wikidata_reconciliation_incomplete",
  "interrupted_by_restart",
];
function warningLabel(warning: string) {
  const [key, detail = ""] = warning.split(":", 2);
  if (!KNOWN_WARNINGS.includes(key)) return i18n.t("capture.warning.other");
  return i18n.tf(`capture.warning.${key}`, { count: detail, detail });
}
function groupSelected(items: CaptureCandidate[]) {
  const selected = items.filter((item) => item.selection_status === "selected").length;
  return { all: selected === items.length, some: selected > 0 && selected < items.length };
}
function setIndeterminate(element: unknown, value: boolean) {
  if (element instanceof HTMLInputElement) element.indeterminate = value;
}
function toggle(candidate: CaptureCandidate, on: boolean) {
  emit("select", [candidate.candidate_id], on);
}
function toggleGroup(items: CaptureCandidate[], on: boolean) {
  emit(
    "select",
    items.map((item) => item.candidate_id),
    on,
  );
}
function projectLabel(candidate: CaptureCandidate) {
  return candidate.provider === "wikisource" && candidate.source_project_language
    ? candidate.source_project_language === "mul"
      ? i18n.t("capture.project_multilingual")
      : i18n.tf("sources.project", {
          project: languageName(candidate.source_project_language, i18n.locale),
        })
    : "";
}
</script>

<template>
  <div class="capture-review">
    <section class="cr-coverage" aria-labelledby="cr-coverage-title">
      <h3 id="cr-coverage-title">{{ i18n.t("capture.review.coverage") }}</h3>
      <ul class="cr-snapshots">
        <li
          v-for="snapshot in capture.provider_snapshots"
          :key="snapshot.provider"
          :data-provider="snapshot.provider"
        >
          <strong
            >{{ enumLabel(t, "provider", snapshot.provider) }} ·
            {{ i18n.t("capture.review.snapshot") }}</strong
          >
          <span>{{
            i18n.tf("capture.review.discovered_count", { count: snapshot.result_count })
          }}</span>
          <span>{{
            i18n.tf("capture.review.last_discovered", {
              date: formatDate(snapshot.searched_at || capture.discovery_completed_at),
            })
          }}</span>
          <span v-if="snapshot.projects_searched.length && snapshot.provider === 'wikisource'">{{
            i18n.tf("capture.review.projects_searched", {
              projects: snapshot.projects_searched
                .map((code) =>
                  code === "mul"
                    ? i18n.t("capture.project_multilingual")
                    : languageName(code, i18n.locale),
                )
                .join(" · "),
            })
          }}</span>
          <span v-if="!snapshot.pagination_complete" class="cr-warning">{{
            i18n.t("capture.review.incomplete")
          }}</span>
          <span v-for="warning in snapshot.warnings || []" :key="warning" class="cr-warning">{{
            warningLabel(warning)
          }}</span>
          <span v-for="(error, index) in snapshot.errors || []" :key="index" class="cr-error">
            {{ enumLabel(t, "error", error.code)
            }}<template v-if="error.project">
              ({{ languageName(error.project, i18n.locale) }})</template
            >: {{ error.message }}
          </span>
        </li>
      </ul>
      <p v-for="warning in capture.warnings" :key="warning" class="cr-warning">
        {{ warningLabel(warning) }}
      </p>
      <p class="cr-note">{{ i18n.t("capture.review.coverage_note") }}</p>
    </section>

    <section class="cr-summary" aria-labelledby="cr-summary-title">
      <h3 id="cr-summary-title" class="sr-only">{{ i18n.t("capture.review.summary") }}</h3>
      <dl class="cr-counts">
        <div v-for="item in counts" :key="item.key" :data-count="item.key">
          <dt>{{ i18n.t(`capture.review.count_${item.key}`) }}</dt>
          <dd>{{ item.value.toLocaleString(i18n.locale) }}</dd>
        </div>
      </dl>
      <p class="cr-breakdown">
        <span>{{ i18n.t("capture.review.by_language") }}:</span>
        <span v-for="item in languageCounts" :key="item.code" class="cr-chip"
          >{{ item.label }} · {{ item.count }}</span
        >
      </p>
      <p class="cr-breakdown">
        <span>{{ i18n.t("capture.review.by_provider") }}:</span>
        <span v-for="item in providerCounts" :key="item.provider" class="cr-chip"
          >{{ enumLabel(t, "provider", item.provider) }} · {{ item.count }}</span
        >
      </p>
    </section>

    <div class="cr-toolbar">
      <span role="status">{{
        i18n.tf("capture.review.selected_count", {
          selected: selectedCount,
          total: candidates.length,
        })
      }}</span>
      <button
        type="button"
        class="btn small"
        data-select-all
        :disabled="busy"
        @click="emit('select', null, true)"
      >
        {{ i18n.t("capture.review.select_all") }}
      </button>
      <button
        type="button"
        class="btn small"
        data-select-none
        :disabled="busy"
        @click="emit('select', null, false)"
      >
        {{ i18n.t("capture.review.select_none") }}
      </button>
    </div>

    <p v-if="!candidates.length" class="cr-empty" role="status">
      {{ i18n.t("capture.review.none_found") }}
    </p>
    <ul class="cr-works">
      <li v-for="work in groups" :key="work.workId" class="cr-work" :data-work="work.workId">
        <div class="cr-work-head">
          <label>
            <input
              :ref="(el) => setIndeterminate(el, groupSelected(work.items).some)"
              type="checkbox"
              :checked="groupSelected(work.items).all"
              :disabled="busy"
              :aria-label="i18n.tf('capture.review.select_work', { title: work.title })"
              @change="toggleGroup(work.items, ($event.target as HTMLInputElement).checked)"
            />
            <strong>{{ work.title }}</strong>
          </label>
          <UiStatusBadge
            v-if="work.status === 'possible_match'"
            :label="enumLabel(t, 'reconciliation', work.status)"
            :tone="enumTone('reconciliation', work.status)"
            :help="i18n.t('capture.review.possible_match_help')"
          />
          <small>{{ i18n.tf("capture.review.work_sources", { count: work.items.length }) }}</small>
        </div>
        <div v-for="language in work.languages" :key="language.key" class="cr-language">
          <h4 :data-language="language.key">{{ language.label }}</h4>
          <ul>
            <li
              v-for="item in language.items"
              :key="item.candidate_id"
              class="cr-item"
              :data-candidate="item.candidate_id"
            >
              <label>
                <input
                  type="checkbox"
                  :checked="item.selection_status === 'selected'"
                  :disabled="busy"
                  @change="toggle(item, ($event.target as HTMLInputElement).checked)"
                />
                <span class="cr-title">{{ item.title }}</span>
              </label>
              <span class="cr-badges">
                <UiStatusBadge
                  :label="enumLabel(t, 'role', item.contribution_role)"
                  :show-dot="false"
                />
                <UiStatusBadge
                  :label="enumLabel(t, 'confidence', item.identity_confidence)"
                  :tone="enumTone('confidence', item.identity_confidence)"
                />
                <UiStatusBadge
                  v-if="item.relationship_to_work !== 'unknown'"
                  :label="enumLabel(t, 'relationship', item.relationship_to_work)"
                  :show-dot="false"
                />
                <UiStatusBadge
                  v-if="item.acquisition_status !== 'pending'"
                  :label="enumLabel(t, 'acquisition', item.acquisition_status)"
                  :tone="enumTone('acquisition', item.acquisition_status)"
                />
                <UiStatusBadge
                  v-if="item.possible_duplicates?.length"
                  :label="i18n.t('capture.review.possible_duplicate')"
                  tone="warning"
                />
                <UiStatusBadge
                  v-if="item.upstream_status === 'missing'"
                  :label="i18n.t('capture.review.missing_upstream')"
                  tone="warning"
                />
                <UiStatusBadge
                  v-if="item.metadata_changed_fields?.length"
                  :label="i18n.t('capture.review.metadata_changed')"
                  tone="info"
                />
              </span>
              <small class="cr-meta">
                {{ enumLabel(t, "provider", item.provider) }}
                <template v-if="projectLabel(item)"> · {{ projectLabel(item) }}</template>
                <template v-if="item.translators.length">
                  · {{ i18n.t("capture.translated_by") }}
                  {{ item.translators.join("; ") }}</template
                >
                <template v-if="item.publication_year"> · {{ item.publication_year }}</template>
                <template v-if="item.original_language">
                  ·
                  {{
                    i18n.tf("capture.review.original_language", {
                      language: languageName(item.original_language, i18n.locale),
                    })
                  }}</template
                >
              </small>
              <p v-if="item.error" class="cr-error" role="note">
                {{ enumLabel(t, "error", item.error.code) }}: {{ item.error.message }}
              </p>
            </li>
          </ul>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.capture-review {
  display: grid;
  gap: 16px;
}
h3 {
  margin: 0 0 8px;
  font-size: var(--fs-md);
}
.cr-snapshots,
.cr-works,
.cr-language ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.cr-snapshots li {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  font-size: var(--fs-sm);
}
.cr-note,
.cr-meta,
.cr-work-head small {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.cr-warning {
  color: var(--tone-warn-fg);
  font-size: var(--fs-sm);
}
.cr-error {
  margin: 0;
  color: var(--tone-danger-fg);
  font-size: var(--fs-sm);
}
.cr-counts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 8px;
  margin: 0;
}
.cr-counts div {
  padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
}
.cr-counts dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
.cr-counts dd {
  margin: 0;
  font-size: var(--fs-lg);
  font-weight: var(--fw-bold);
}
.cr-breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0 0;
  font-size: var(--fs-sm);
}
.cr-chip {
  padding: 2px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
}
.cr-toolbar {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  background: var(--surface-overlay);
}
.cr-toolbar > span {
  margin-inline-end: auto;
  font-weight: var(--fw-semibold);
}
.cr-work {
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.cr-work-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.cr-work-head label,
.cr-item label {
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
}
.cr-language {
  margin: 8px 0 0 24px;
}
.cr-language h4 {
  margin: 0 0 4px;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.cr-item {
  display: grid;
  gap: 4px;
  padding: 6px 0;
  border-top: 1px solid var(--border-subtle);
}
.cr-title {
  overflow-wrap: anywhere;
}
.cr-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-inline-start: 24px;
}
.cr-meta {
  margin-inline-start: 24px;
}
.cr-empty {
  color: var(--text-secondary);
}
</style>
