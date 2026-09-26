<script setup lang="ts">
import { computed } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";

const props = defineProps<{ build: CorpusBuild; busy?: boolean }>();
const emit = defineEmits<{
  retryMetadata: [];
  reviewMetadata: [];
  reviewValidation: [];
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
}>();
const i18n = useI18nStore();
const readiness = computed(() => props.build.publication_readiness || {});
const summary = computed(() => props.build.metadata_issue_summary || {});
const publication = computed(() => props.build.publication || null);
const next = computed(() => String(readiness.value.next_action || "inspect"));
const blockers = computed(() => readiness.value.blockers || []);
const validation = computed(() => props.build.validation || {});
const validationIssues = computed(() =>
  Array.isArray(validation.value.validation_issues) ? validation.value.validation_issues : [],
);
const sourceQuality = computed(() => props.build.source_quality || {});
const noPublishable = computed(() => Boolean(readiness.value.no_publishable_records));
const primaryLabel = computed(() => {
  if (publication.value) return i18n.t("pdf_corpus.download_jsonl");
  if (noPublishable.value) return i18n.t("pdf_corpus.return_to_review");
  if (next.value === "review_records") return i18n.t("pdf_corpus.continue_review");
  if (next.value === "resolve_document_metadata")
    return i18n.t("pdf_corpus.edit_document_metadata");
  if (next.value === "resolve_validation") return i18n.t("pdf_corpus.review_validation_issues");
  if (next.value === "publish") return i18n.t("pdf_corpus.publish_corpus");
  return i18n.t("pdf_corpus.inspect_remaining_work");
});
function act() {
  if (noPublishable.value) {
    emit("reviewRejected");
    return;
  }
  if (next.value === "review_records") emit("reviewRecords");
  else if (next.value === "resolve_document_metadata") emit("editDocumentMetadata");
  else if (next.value === "resolve_validation") emit("reviewValidation");
  else if (next.value === "publish") emit("publish");
}
function blockerLabel(code?: string) {
  return i18n.t(
    `pdf_corpus.readiness_blocker.${code || "unknown"}`,
    String(code || "unknown").replace(/_/g, " "),
  );
}
function fixBlocker(code?: string) {
  const value = String(code || "");
  if (value === "required_document_metadata") emit("editDocumentMetadata");
  else if (value === "required_metadata") emit("reviewMetadata");
  else if (value === "metadata_validation") emit("reviewValidation");
  else if (value === "boundary_attention") emit("reviewTopology");
  else if (value === "record_attention") emit("reviewIssues");
  else if (value === "source_quality" || value === "source_validation") emit("reviewSource");
  else emit("reviewRecords");
}
</script>

<template>
  <section class="finish-workspace" aria-labelledby="finish-corpus-title">
    <header class="publication-head">
      <div>
        <span class="eyebrow">{{ i18n.t("pdf_corpus.finish_phase") }}</span>
        <h2 id="finish-corpus-title">
          {{
            publication
              ? i18n.t("pdf_corpus.published_revision")
              : readiness.can_publish
                ? i18n.t("pdf_corpus.ready_to_publish")
                : i18n.t("pdf_corpus.finish_corpus_title")
          }}
        </h2>
        <p>
          {{
            publication
              ? i18n.t("pdf_corpus.finish_published_help")
              : readiness.can_publish
                ? i18n.t("pdf_corpus.finish_ready_help")
                : i18n.t("pdf_corpus.finish_blocked_help")
          }}
        </p>
      </div>
      <div class="publication-primary finish-primary">
        <a
          v-if="publication"
          class="btn primary"
          :href="`/api/pdf/publications/${encodeURIComponent(publication.publication_id)}/download`"
          >{{ primaryLabel }}</a
        >
        <button
          v-else
          type="button"
          class="btn primary"
          :disabled="
            busy ||
            (!noPublishable &&
              ![
                'review_records',
                'resolve_document_metadata',
                'resolve_validation',
                'publish',
              ].includes(next))
          "
          @click="act"
        >
          {{ primaryLabel }}
        </button>
      </div>
    </header>

    <section
      v-if="noPublishable"
      class="no-publishable"
      role="status"
      aria-labelledby="no-publishable-title"
    >
      <div>
        <span class="readiness-state">{{ i18n.t("pdf_corpus.no_publishable_status") }}</span>
        <h3 id="no-publishable-title">{{ i18n.t("pdf_corpus.no_publishable_title") }}</h3>
        <p>{{ i18n.t("pdf_corpus.no_publishable_help") }}</p>
      </div>
      <div class="readiness-actions">
        <button type="button" class="btn primary" @click="emit('reviewRejected')">
          {{ i18n.t("pdf_corpus.return_to_review") }}</button
        ><button type="button" class="btn" :disabled="busy" @click="emit('restoreRejected')">
          {{ i18n.t("pdf_corpus.restore_all_rejected") }}</button
        ><button type="button" class="btn" @click="emit('startNew')">
          {{ i18n.t("pdf_corpus.start_new_build") }}
        </button>
      </div>
    </section>

    <section v-if="publication" class="publication-snapshot" role="status">
      <div>
        <span class="readiness-state">{{ i18n.t("pdf_corpus.complete") }}</span>
        <b>{{ i18n.t("pdf_corpus.publication") }}</b>
      </div>
      <p>
        {{
          i18n.tf("pdf_corpus.publication_snapshot_summary", { count: publication.record_count })
        }}
      </p>
      <code>{{ publication.publication_id }}</code>
    </section>

    <div v-if="readiness.missing_document_fields?.length" class="document-blocker" role="alert">
      <b>{{ i18n.t("pdf_corpus.readiness_blocker.required_document_metadata") }}</b
      ><span>{{
        readiness.missing_document_fields
          .map((field) => i18n.t(`record.${field}`, field.replace(/_/g, " ")))
          .join(", ")
      }}</span>
    </div>

    <section
      v-if="blockers.length && !noPublishable"
      class="publication-blockers blockers"
      aria-labelledby="publication-blockers-title"
    >
      <div class="publication-blockers-head">
        <div>
          <span class="readiness-state">{{ i18n.t("pdf_corpus.attention_required") }}</span>
          <h3 id="publication-blockers-title">
            {{ i18n.tf("pdf_corpus.view_publication_blockers", { count: blockers.length }) }}
          </h3>
        </div>
        <span class="blocker-count">{{ blockers.length }}</span>
      </div>
      <ul>
        <li v-for="(blocker, index) in blockers" :key="`${blocker.code}-${index}`">
          <span>
            <b>{{ blockerLabel(blocker.code) }}</b>
            <small v-if="blocker.count">{{ blocker.count }}</small>
          </span>
          <button type="button" class="btn small" @click="fixBlocker(blocker.code)">
            {{ i18n.t("pdf_corpus.go_fix") }}
          </button>
        </li>
      </ul>
    </section>

    <div v-if="!noPublishable" class="publication-readiness-list">
      <section
        class="readiness-row"
        :data-state="Number(readiness.records_pending || 0) > 0 ? 'attention' : 'complete'"
      >
        <div class="readiness-row-copy">
          <span class="readiness-state">
            {{
              Number(readiness.records_pending || 0) > 0
                ? i18n.t("pdf_corpus.attention_required")
                : i18n.t("pdf_corpus.complete")
            }}
          </span>
          <h3>{{ i18n.t("pdf_corpus.record_review") }}</h3>
          <p>
            {{ readiness.records_reviewed || 0 }} / {{ readiness.records_total || 0 }}
            {{ i18n.t("pdf_corpus.reviewed") }}
          </p>
        </div>
        <dl>
          <div>
            <dt>{{ i18n.t("pdf_corpus.accepted_label") }}</dt>
            <dd>{{ readiness.records_accepted || 0 }}</dd>
          </div>
          <div>
            <dt>{{ i18n.t("pdf_corpus.rejected") }}</dt>
            <dd>{{ readiness.records_rejected || 0 }}</dd>
          </div>
          <div>
            <dt>{{ i18n.t("pdf_corpus.pending") }}</dt>
            <dd>{{ readiness.records_pending || 0 }}</dd>
          </div>
        </dl>
        <div class="readiness-actions">
          <button
            v-if="Number(readiness.records_pending || 0) > 0"
            type="button"
            class="btn"
            @click="emit('reviewRecords')"
          >
            {{ i18n.t("pdf_corpus.continue_review") }}
          </button>
          <button
            v-if="Number(readiness.records_rejected || 0) > 0"
            type="button"
            class="btn"
            @click="emit('reviewRejected')"
          >
            {{ i18n.t("pdf_corpus.review_rejected_records") }}
          </button>
        </div>
      </section>

      <section
        class="readiness-row"
        :data-state="Number(summary.fields_unresolved || 0) > 0 ? 'attention' : 'complete'"
      >
        <div class="readiness-row-copy">
          <span class="readiness-state">
            {{
              Number(summary.fields_unresolved || 0) > 0
                ? i18n.t("pdf_corpus.attention_required")
                : i18n.t("pdf_corpus.complete")
            }}
          </span>
          <h3>{{ i18n.t("pdf_corpus.required_metadata") }}</h3>
          <p v-if="Number(summary.fields_unresolved || 0) > 0">
            {{
              i18n.tf("pdf_corpus.finish_metadata_summary", {
                records: Number(summary.records_incomplete || 0),
                fields: Number(summary.fields_unresolved || 0),
              })
            }}
          </p>
          <p v-else>{{ i18n.t("pdf_corpus.finish_metadata_complete") }}</p>
        </div>
        <dl>
          <div>
            <dt>{{ i18n.t("pdf_corpus.auto_retry") }}</dt>
            <dd>{{ summary.auto_retry_fields || 0 }}</dd>
          </div>
          <div>
            <dt>{{ i18n.t("pdf_corpus.human_review") }}</dt>
            <dd>{{ summary.human_review_fields || 0 }}</dd>
          </div>
        </dl>
        <div class="readiness-actions">
          <button
            v-if="Number(summary.fields_unresolved || 0) > 0"
            type="button"
            class="btn"
            @click="emit('reviewMetadata')"
          >
            {{ i18n.t("pdf_corpus.open_metadata_queue") }}
          </button>
          <button
            v-if="
              Number(summary.fields_unresolved || 0) > 0 &&
              Number(summary.auto_retry_fields || 0) > 0
            "
            type="button"
            class="btn"
            :disabled="busy"
            @click="emit('retryMetadata')"
          >
            {{
              i18n.tf("pdf_corpus.retry_metadata_fields", {
                count: Number(summary.auto_retry_fields || 0),
              })
            }}
          </button>
          <button type="button" class="btn" :disabled="busy" @click="emit('rerunEnrichment')">
            {{ i18n.t("pdf_corpus.metadata_enrichment_again") }}
          </button>
        </div>
      </section>

      <section class="readiness-row" :data-state="validation.valid ? 'complete' : 'attention'">
        <div class="readiness-row-copy">
          <span class="readiness-state">
            {{
              validation.valid
                ? i18n.t("pdf_corpus.complete")
                : i18n.t("pdf_corpus.attention_required")
            }}
          </span>
          <h3>{{ i18n.t("pdf_corpus.final_validation") }}</h3>
          <p>
            {{
              validation.valid
                ? i18n.t("pdf_corpus.publication_ready_help")
                : i18n.t("pdf_corpus.publication_waiting_help")
            }}
          </p>
        </div>
        <dl>
          <div>
            <dt>{{ i18n.t("pdf_corpus.source_fidelity") }}</dt>
            <dd>
              {{
                validation.source_valid
                  ? i18n.t("pdf_corpus.passed")
                  : i18n.t("pdf_corpus.needs_attention")
              }}
            </dd>
          </div>
          <div>
            <dt>{{ i18n.t("pdf_corpus.metadata_validation") }}</dt>
            <dd>
              {{
                validation.metadata_valid
                  ? i18n.t("pdf_corpus.passed")
                  : i18n.t("pdf_corpus.needs_attention")
              }}
            </dd>
          </div>
          <div>
            <dt>{{ i18n.t("pdf_corpus.source_quality") }}</dt>
            <dd>
              {{
                Number(sourceQuality.blocking_page_count || 0) === 0
                  ? i18n.t("pdf_corpus.passed")
                  : i18n.tf("pdf_corpus.blocking_pages", {
                      count: Number(sourceQuality.blocking_page_count || 0),
                    })
              }}
            </dd>
          </div>
          <div>
            <dt>{{ i18n.t("pdf_corpus.coverage") }}</dt>
            <dd>{{ Math.round(Number(validation.coverage || 0) * 100) }}%</dd>
          </div>
        </dl>
        <div class="readiness-actions">
          <button
            v-if="!validation.valid"
            type="button"
            class="btn"
            @click="emit('reviewValidation')"
          >
            {{ i18n.t("pdf_corpus.review_validation_issues") }}
          </button>
        </div>
        <div v-if="validationIssues.length" class="validation-issue-summary">
          <b>{{
            i18n.tf("pdf_corpus.validation_issue_count", {
              count: validationIssues.length,
            })
          }}</b>
          <ul>
            <li
              v-for="(issue, index) in validationIssues.slice(0, 5)"
              :key="`${issue.code}-${issue.record_id}-${issue.field}-${index}`"
            >
              <code>{{ issue.field || issue.record_id || issue.code || "validation" }}</code>
              <span>{{ issue.reason || blockerLabel(issue.code) }}</span>
            </li>
          </ul>
          <small v-if="validationIssues.length > 5">{{
            i18n.tf("pdf_corpus.validation_more_issues", {
              count: validationIssues.length - 5,
            })
          }}</small>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.finish-workspace {
  display: grid;
  min-width: 0;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.publication-head {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-5);
  align-items: flex-start;
}
.publication-head > div:first-child {
  min-width: 0;
  flex: 1 1 32rem;
}
.publication-head h2 {
  margin: var(--space-1) 0 var(--space-2);
  font-size: var(--fs-xl);
}
.publication-head p {
  max-width: 78ch;
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.55;
}
.eyebrow,
.readiness-state {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.publication-primary {
  display: flex;
  min-width: 0;
  align-items: center;
}
.publication-primary .btn {
  max-width: 100%;
  white-space: normal;
}
.no-publishable,
.publication-snapshot,
.document-blocker,
.publication-blockers {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-subtle);
}
.no-publishable {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-4);
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
}
.no-publishable h3 {
  margin: var(--space-1) 0;
  font-size: var(--fs-base);
}
.no-publishable p {
  max-width: 72ch;
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.5;
}
.publication-snapshot {
  display: grid;
  grid-template-columns: minmax(10rem, auto) minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  border-color: var(--tone-success-border);
  background: var(--tone-success-bg);
}
.publication-snapshot > div {
  display: grid;
  gap: var(--space-1);
}
.publication-snapshot p {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.publication-snapshot code {
  max-width: 24rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.document-blocker {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  flex-wrap: wrap;
  padding: var(--space-3) var(--space-4);
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: var(--fs-sm);
}
.document-blocker span {
  color: var(--text-secondary);
}
.publication-blockers {
  overflow: hidden;
  border-color: var(--tone-warn-border);
}
.publication-blockers-head {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--tone-warn-bg);
}
.publication-blockers-head h3 {
  margin: var(--space-1) 0 0;
  font-size: var(--fs-base);
}
.blocker-count {
  display: grid;
  min-width: 2rem;
  height: 2rem;
  place-items: center;
  border-radius: 999px;
  background: var(--tone-warn-fg);
  color: var(--tone-warn-bg);
  font-weight: var(--fw-bold);
}
.publication-blockers ul {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}
.publication-blockers li {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-subtle);
}
.publication-blockers li > span {
  display: flex;
  gap: var(--space-2);
  align-items: baseline;
}
.publication-blockers small {
  color: var(--text-secondary);
}
.publication-readiness-list {
  display: grid;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  overflow: hidden;
}
.readiness-row {
  display: grid;
  grid-template-columns: minmax(14rem, 1.25fr) minmax(18rem, 1fr) auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-4);
  background: var(--surface-card);
}
.readiness-row + .readiness-row {
  border-top: 1px solid var(--border-subtle);
}
.readiness-row[data-state="attention"] {
  box-shadow: inset 3px 0 0 var(--tone-warn-fg);
}
.readiness-row[data-state="complete"] {
  box-shadow: inset 3px 0 0 var(--tone-success-fg);
}
.readiness-row-copy {
  min-width: 0;
}
.readiness-row-copy h3 {
  margin: var(--space-1) 0;
  font-size: var(--fs-base);
}
.readiness-row-copy p {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.45;
}
dl {
  display: flex;
  min-width: 0;
  gap: var(--space-4);
  margin: 0;
}
dl > div {
  min-width: 4.5rem;
}
dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
}
dd {
  margin: var(--space-1) 0 0;
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
}
.readiness-actions {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
  flex-wrap: wrap;
}
.validation-issue-summary {
  grid-column: 1 / -1;
  display: grid;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.validation-issue-summary ul {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}
.validation-issue-summary li {
  display: grid;
  grid-template-columns: minmax(8rem, auto) minmax(0, 1fr);
  gap: var(--space-3);
  padding-block: var(--space-1);
}
.validation-issue-summary code {
  overflow-wrap: anywhere;
  font-size: var(--fs-xs);
}
.validation-issue-summary li span,
.validation-issue-summary small {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  line-height: 1.4;
}
@media (max-width: 1000px) {
  .readiness-row {
    grid-template-columns: 1fr;
  }
  .readiness-actions {
    justify-content: flex-start;
  }
  dl {
    flex-wrap: wrap;
  }
}
@media (max-width: 760px) {
  .publication-head,
  .no-publishable {
    display: grid;
  }
  .publication-primary .btn {
    width: 100%;
  }
  .publication-snapshot {
    grid-template-columns: 1fr;
  }
  .publication-blockers li {
    align-items: flex-start;
    flex-direction: column;
  }
  .validation-issue-summary li {
    grid-template-columns: 1fr;
  }
}
</style>
