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
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, ref } from "vue";
import type { CorpusBuild } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import CorpusFinishWorkspace from "../CorpusFinishWorkspace.vue";
import CorpusUnreviewedPublishDialog from "../CorpusUnreviewedPublishDialog.vue";
import UiButton from "../ui/UiButton.vue";

const props = defineProps<{
  build: CorpusBuild;
  busy?: boolean;
  /** Skipping review is offered once processing is done and until a publication exists. */
  canPublishUnreviewed?: boolean;
}>();
const emit = defineEmits<{
  retryMetadata: [];
  reviewMetadata: [];
  reviewValidation: [];
  fixIssue: [issue: { code?: string; record_id?: string; field?: string; reason?: string }];
  reviewTopology: [];
  reviewIssues: [];
  reviewRejected: [];
  reviewRecords: [];
  reviewSource: [];
  restoreRejected: [];
  startNew: [];
  editDocumentMetadata: [];
  rerunEnrichment: [];
  publish: [];
  publishUnreviewed: [];
}>();
const i18n = useI18nStore();
const confirmingUnreviewed = ref(false);
const readiness = computed(() => props.build.publication_readiness || {});
const published = computed(() => Boolean(props.build.publication));
const blockerCount = computed(() => readiness.value.blockers?.length || 0);
const pending = computed(() => Number(readiness.value.records_pending || 0));
const metadataIssues = computed(() =>
  Number(props.build.metadata_issue_summary?.fields_unresolved || 0),
);
const validationBlockers = computed(() =>
  Array.isArray(props.build.validation?.validation_issues)
    ? props.build.validation.validation_issues.length
    : 0,
);
const summary = computed<{ label: string; tone: "success" | "warning" | "neutral" }>(() => {
  if (published.value)
    return { label: i18n.t("pdf_corpus.publish.status_published"), tone: "success" };
  if (readiness.value.no_publishable_records)
    return { label: i18n.t("pdf_corpus.publish.status_none_publishable"), tone: "warning" };
  if (blockerCount.value > 1 || (blockerCount.value === 1 && !pending.value))
    return {
      label: i18n.tf("pdf_corpus.publish.status_issues", { count: blockerCount.value }),
      tone: "warning",
    };
  if (pending.value > 0)
    return {
      label: i18n.tf("pdf_corpus.publish.status_unreviewed", { count: pending.value }),
      tone: "warning",
    };
  if (readiness.value.can_publish)
    return { label: i18n.t("pdf_corpus.publish.status_ready"), tone: "success" };
  return { label: i18n.t("pdf_corpus.publish.status_inspect"), tone: "neutral" };
});
const counts = computed(() => [
  {
    id: "pending",
    label: i18n.t("pdf_corpus.pending_review"),
    value: pending.value,
  },
  {
    id: "metadata",
    label: i18n.t("pdf_corpus.publish.metadata_issues"),
    value: metadataIssues.value,
  },
  {
    id: "validation",
    label: i18n.t("pdf_corpus.publish.validation_blockers"),
    value: validationBlockers.value,
  },
]);
</script>

<template>
  <section
    class="corpus-publish-workspace corpus-workspace-surface"
    aria-labelledby="corpus-publish-title"
  >
    <header class="publish-summary" :data-tone="summary.tone">
      <div class="publish-summary-copy">
        <span class="eyebrow">
          {{
            published
              ? i18n.t("pdf_corpus.publication")
              : i18n.t("pdf_corpus.publish.readiness_title")
          }}
        </span>
        <h2 id="corpus-publish-title" role="status">{{ summary.label }}</h2>
        <dl v-if="!published" class="publish-counts">
          <div v-for="item in counts" :key="item.id" :data-count="item.id">
            <dt>{{ item.label }}</dt>
            <dd>{{ Number(item.value).toLocaleString() }}</dd>
          </div>
        </dl>
      </div>
      <UiButton
        v-if="canPublishUnreviewed"
        :label="i18n.t('pdf_corpus.accept_unreviewed')"
        :disabled="busy"
        @click="confirmingUnreviewed = true"
      />
    </header>

    <CorpusFinishWorkspace
      :build="build"
      :busy="busy"
      @retry-metadata="emit('retryMetadata')"
      @review-metadata="emit('reviewMetadata')"
      @review-validation="emit('reviewValidation')"
      @fix-issue="(issue) => emit('fixIssue', issue)"
      @review-topology="emit('reviewTopology')"
      @review-issues="emit('reviewIssues')"
      @review-rejected="emit('reviewRejected')"
      @review-records="emit('reviewRecords')"
      @review-source="emit('reviewSource')"
      @restore-rejected="emit('restoreRejected')"
      @start-new="emit('startNew')"
      @edit-document-metadata="emit('editDocumentMetadata')"
      @rerun-enrichment="emit('rerunEnrichment')"
      @publish="emit('publish')"
    />
    <CorpusUnreviewedPublishDialog
      :open="Boolean(canPublishUnreviewed) && confirmingUnreviewed"
      :busy="busy"
      :pending-records="pending"
      :unresolved-fields="metadataIssues"
      @close="confirmingUnreviewed = false"
      @confirm="
        confirmingUnreviewed = false;
        emit('publishUnreviewed');
      "
    />
  </section>
</template>

<style scoped>
.corpus-publish-workspace {
  display: grid;
  gap: var(--space-4);
}
.publish-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--border-subtle);
  border-inline-start: 4px solid var(--border-interactive);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.publish-summary[data-tone="success"] {
  border-inline-start-color: var(--tone-ok-fg);
}
.publish-summary[data-tone="warning"] {
  border-inline-start-color: var(--tone-warn-fg);
}
.publish-summary-copy {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}
.eyebrow {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.publish-summary h2 {
  margin: 0;
  font-size: var(--fs-xl);
}
.publish-counts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-5);
  margin: 0;
}
.publish-counts div {
  display: grid;
  gap: 2px;
}
.publish-counts dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
.publish-counts dd {
  margin: 0;
  font-size: var(--fs-lg, 1.125rem);
  font-weight: var(--fw-bold);
}
</style>
