<script setup lang="ts">
import UiButton from "./ui/UiButton.vue";
import { computed, ref } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";
import AppIcon from "./AppIcon.vue";

type ValidationIssue = { code?: string; record_id?: string; field?: string; reason?: string };

const props = defineProps<{ build: CorpusBuild; busy?: boolean }>();
const emit = defineEmits<{
  retryMetadata: [];
  reviewMetadata: [];
  reviewValidation: [];
  /** Open the exact record (and field) a validation finding is about. */
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
}>();
const i18n = useI18nStore();
const readiness = computed(() => props.build.publication_readiness || {});
const summary = computed(() => props.build.metadata_issue_summary || {});
const publication = computed(() => props.build.publication || null);
const publicationConformanceBlockers = computed(() => {
  const conformance = publication.value?.celf_conformance;
  const blockers = [
    ...(conformance?.core?.blockers || []),
    ...(conformance?.publication?.blockers || []),
  ];
  return blockers
    .map((blocker) => String(blocker.code || blocker.reason || blocker.message || "unknown"))
    .filter(Boolean);
});
const next = computed(() => String(readiness.value.next_action || "inspect"));
const blockers = computed(() => readiness.value.blockers || []);
const validation = computed(() => props.build.validation || {});
const validationIssues = computed(() =>
  Array.isArray(validation.value.validation_issues) ? validation.value.validation_issues : [],
);
const sourceQuality = computed(() => props.build.source_quality || {});

/** One entry per record with a finding, in first-seen order, so the same record's
 * several findings read as one thing to fix rather than several identical-looking rows. */
interface ValidationIssueGroup {
  recordId: string;
  issues: ValidationIssue[];
}
const groupedValidationIssues = computed<ValidationIssueGroup[]>(() => {
  const order: string[] = [];
  const byRecord = new Map<string, ValidationIssue[]>();
  for (const issue of validationIssues.value) {
    const recordId = String(issue?.record_id || "");
    if (!byRecord.has(recordId)) {
      order.push(recordId);
      byRecord.set(recordId, []);
    }
    byRecord.get(recordId)?.push(issue);
  }
  return order.map((recordId) => ({ recordId, issues: byRecord.get(recordId) || [] }));
});
const showAllIssueGroups = ref(false);
const shownIssueGroups = computed(() =>
  showAllIssueGroups.value
    ? groupedValidationIssues.value
    : groupedValidationIssues.value.slice(0, 5),
);
function issueGroupLabel(issue: ValidationIssue) {
  const reason = issue.reason || blockerLabel(issue.code);
  return issue.field ? `${issue.field}: ${reason}` : reason;
}
const validationIssueSummaryLabel = computed(() => {
  const issueCount = validationIssues.value.length;
  const recordCount = groupedValidationIssues.value.length;
  return recordCount > 0 && recordCount !== issueCount
    ? i18n.tf("pdf_corpus.validation_issue_summary_grouped", {
        issues: issueCount,
        records: recordCount,
      })
    : i18n.tf("pdf_corpus.validation_issue_count", { count: issueCount });
});
/** A decorative status glyph; the adjacent label already carries the state in words. */
function stateIcon(attention: boolean) {
  return attention ? "warning" : "check";
}
const noPublishable = computed(() => Boolean(readiness.value.no_publishable_records));
const ACTIONABLE_NEXT = [
  "review_records",
  "resolve_document_metadata",
  "resolve_validation",
  "publish",
];
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
  // Nothing more specific is known: go to the first blocker, else back to the Records.
  if (!ACTIONABLE_NEXT.includes(next.value)) {
    if (blockers.value.length) fixBlocker(blockers.value[0]?.code);
    else emit("reviewRecords");
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
  else if (value === "metadata_validation") {
    // Go to the first specific finding (record, field, reason) instead of just a queue.
    const first = validationIssues.value.find((item) => item?.record_id);
    if (first) emit("fixIssue", first);
    else emit("reviewValidation");
  } else if (value === "boundary_attention") emit("reviewTopology");
  else if (value === "record_attention") emit("reviewIssues");
  else if (value === "source_quality" || value === "source_validation") emit("reviewSource");
  else emit("reviewRecords");
}
</script>

<template>
  <section class="finish-workspace" :aria-label="i18n.t('pdf_corpus.publish.actions_label')">
    <div v-if="publication" class="publication-head">
      <div class="publication-primary finish-primary">
        <a
          class="btn primary"
          :href="`/api/pdf/publications/${encodeURIComponent(publication.publication_id)}/download`"
          >{{ primaryLabel }}</a
        >
      </div>
    </div>

    <section
      v-else-if="!noPublishable"
      class="publish-decision"
      :data-state="blockers.length ? 'blocked' : 'ready'"
      aria-labelledby="publish-decision-title"
    >
      <div class="publish-decision-copy">
        <span class="readiness-state" :data-tone="blockers.length ? 'attention' : 'ok'">
          <AppIcon :name="stateIcon(Boolean(blockers.length))" />
          {{
            blockers.length
              ? i18n.t("pdf_corpus.attention_required")
              : i18n.t("pdf_corpus.complete")
          }}
        </span>
        <h3 id="publish-decision-title">
          {{
            blockers.length
              ? i18n.tf("pdf_corpus.view_publication_blockers", { count: blockers.length })
              : i18n.t("pdf_corpus.publish.status_ready")
          }}
        </h3>
        <p>
          {{
            blockers.length
              ? i18n.t("pdf_corpus.publication_waiting_help")
              : i18n.t("pdf_corpus.publication_ready_help")
          }}
        </p>
      </div>
      <div class="publication-primary finish-primary">
        <UiButton variant="primary" :disabled="busy" @click="act">
          {{ primaryLabel }}
        </UiButton>
      </div>
    </section>

    <section
      v-if="noPublishable"
      class="no-publishable"
      role="status"
      aria-labelledby="no-publishable-title"
    >
      <div>
        <span class="readiness-state" data-tone="attention"
          ><AppIcon :name="stateIcon(true)" />{{ i18n.t("pdf_corpus.no_publishable_status") }}</span
        >
        <h3 id="no-publishable-title">{{ i18n.t("pdf_corpus.no_publishable_title") }}</h3>
        <p>{{ i18n.t("pdf_corpus.no_publishable_help") }}</p>
      </div>
      <div class="readiness-actions">
        <UiButton variant="primary" @click="emit('reviewRejected')">
          {{ i18n.t("pdf_corpus.return_to_review") }}</UiButton
        ><UiButton :disabled="busy" @click="emit('restoreRejected')">
          {{ i18n.t("pdf_corpus.restore_all_rejected") }}</UiButton
        ><UiButton @click="emit('startNew')">
          {{ i18n.t("pdf_corpus.start_new_build") }}
        </UiButton>
      </div>
    </section>

    <section
      v-if="publication"
      class="publication-snapshot"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div>
        <span class="readiness-state" data-tone="ok"
          ><AppIcon :name="stateIcon(false)" />{{ i18n.t("pdf_corpus.complete") }}</span
        >
        <b>{{ i18n.t("pdf_corpus.publication") }}</b>
      </div>
      <p>
        {{
          i18n.tf("pdf_corpus.publication_snapshot_summary", { count: publication.record_count })
        }}
      </p>
      <p v-if="publication.review_mode">
        {{
          i18n.tf("pdf_corpus.publication_decision_mode", {
            mode: publication.review_mode,
            human: publication.human_reviewed_record_count || 0,
            autonomous: publication.autonomous_record_count || 0,
          })
        }}
      </p>
      <p v-if="publication.celf_conformant === true" class="conformant">
        {{ i18n.t("pdf_corpus.publication_celf_conformant") }}
      </p>
      <p v-if="publication.celf_conformant === false" class="not-conformant">
        {{
          i18n.tf("pdf_corpus.publication_not_conformant", {
            count: publication.unreviewed_record_count || 0,
            fields: publication.unreviewed_accepted_field_count || 0,
          })
        }}
      </p>
      <p v-if="publicationConformanceBlockers.length" class="not-conformant">
        {{
          i18n.tf("pdf_corpus.publication_celf_blockers", {
            blockers: publicationConformanceBlockers.join(", "),
          })
        }}
      </p>
      <code>{{ publication.publication_id }}</code>
    </section>

    <section
      v-if="!publication && blockers.length && !noPublishable"
      class="publication-blockers blockers"
      aria-labelledby="publication-blockers-title"
    >
      <div class="publication-blockers-head">
        <div>
          <span class="readiness-state" data-tone="attention"
            ><AppIcon :name="stateIcon(true)" />{{ i18n.t("pdf_corpus.attention_required") }}</span
          >
          <h3 id="publication-blockers-title">
            {{ i18n.tf("pdf_corpus.view_publication_blockers", { count: blockers.length }) }}
          </h3>
        </div>
        <span class="blocker-count">{{ blockers.length }}</span>
      </div>
      <ul>
        <li v-for="(blocker, index) in blockers" :key="`${blocker.code}-${index}`">
          <div class="blocker-copy">
            <span class="blocker-title">
              <b>{{ blockerLabel(blocker.code) }}</b>
              <small v-if="blocker.count" class="count-pill">{{ blocker.count }}</small>
            </span>
            <small
              v-if="
                blocker.code === 'required_document_metadata' &&
                readiness.missing_document_fields?.length
              "
              class="blocker-detail"
            >
              {{
                readiness.missing_document_fields
                  .map((field) => i18n.t(`record.${field}`, field.replace(/_/g, " ")))
                  .join(", ")
              }}
            </small>
            <small v-else-if="blocker.code === 'required_metadata'" class="blocker-detail">
              {{
                i18n.tf("pdf_corpus.finish_metadata_summary", {
                  records: Number(summary.records_incomplete || 0),
                  fields: Number(summary.fields_unresolved || 0),
                })
              }}
            </small>
            <small
              v-else-if="blocker.code === 'metadata_validation' && validationIssues.length"
              class="blocker-detail"
            >
              {{ validationIssueSummaryLabel }}
            </small>
          </div>
          <button
            type="button"
            class="btn small"
            :aria-label="
              i18n.tf('pdf_corpus.fix_blocker_labelled', { blocker: blockerLabel(blocker.code) })
            "
            @click="fixBlocker(blocker.code)"
          >
            {{ i18n.t("pdf_corpus.go_fix") }}
          </button>
        </li>
      </ul>
    </section>

    <details v-if="!publication && !noPublishable" class="readiness-details">
      <summary>
        <span>
          <b>{{ i18n.t("pdf_corpus.publish.readiness_title") }}</b>
          <small>
            {{
              blockers.length
                ? i18n.t("pdf_corpus.publication_waiting_help")
                : i18n.t("pdf_corpus.publication_ready_help")
            }}
          </small>
        </span>
        <span class="readiness-details-affordance">{{ i18n.t("pdf_corpus.inspect") }}</span>
      </summary>
      <div class="publication-readiness-list">
      <section
        class="readiness-row"
        :data-state="Number(readiness.records_pending || 0) > 0 ? 'attention' : 'complete'"
      >
        <div class="readiness-row-copy">
          <span
            class="readiness-state"
            :data-tone="Number(readiness.records_pending || 0) > 0 ? 'attention' : 'ok'"
          >
            <AppIcon :name="stateIcon(Number(readiness.records_pending || 0) > 0)" />
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
          <UiButton
            v-if="Number(readiness.records_pending || 0) > 0"
            @click="emit('reviewRecords')"
          >
            {{ i18n.t("pdf_corpus.continue_review") }}
          </UiButton>
          <UiButton
            v-if="Number(readiness.records_rejected || 0) > 0"
            @click="emit('reviewRejected')"
          >
            {{ i18n.t("pdf_corpus.review_rejected_records") }}
          </UiButton>
        </div>
      </section>

      <section
        class="readiness-row"
        :data-state="Number(summary.fields_unresolved || 0) > 0 ? 'attention' : 'complete'"
      >
        <div class="readiness-row-copy">
          <span
            class="readiness-state"
            :data-tone="Number(summary.fields_unresolved || 0) > 0 ? 'attention' : 'ok'"
          >
            <AppIcon :name="stateIcon(Number(summary.fields_unresolved || 0) > 0)" />
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
          <UiButton
            v-if="Number(summary.fields_unresolved || 0) > 0"
            @click="emit('reviewMetadata')"
          >
            {{ i18n.t("pdf_corpus.open_metadata_queue") }}
          </UiButton>
          <UiButton
            v-if="
              Number(summary.fields_unresolved || 0) > 0 &&
              Number(summary.auto_retry_fields || 0) > 0
            "
            :disabled="busy"
            @click="emit('retryMetadata')"
          >
            {{
              i18n.tf("pdf_corpus.retry_metadata_fields", {
                count: Number(summary.auto_retry_fields || 0),
              })
            }}
          </UiButton>
          <UiButton :disabled="busy" @click="emit('rerunEnrichment')">
            {{ i18n.t("pdf_corpus.metadata_enrichment_again") }}
          </UiButton>
        </div>
      </section>

      <section class="readiness-row" :data-state="validation.valid ? 'complete' : 'attention'">
        <div class="readiness-row-copy">
          <span class="readiness-state" :data-tone="validation.valid ? 'ok' : 'attention'">
            <AppIcon :name="stateIcon(!validation.valid)" />
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
          <UiButton v-if="!validation.valid" @click="emit('reviewValidation')">
            {{ i18n.t("pdf_corpus.review_validation_issues") }}
          </UiButton>
        </div>
        <div v-if="groupedValidationIssues.length" class="validation-issue-summary">
          <b>{{ validationIssueSummaryLabel }}</b>
          <ul>
            <li
              v-for="group in shownIssueGroups"
              :key="group.recordId || 'ungrouped'"
              class="issue-group"
            >
              <div class="issue-group-head">
                <span class="issue-group-heading">
                  <code v-if="group.recordId">{{ group.recordId }}</code>
                  <span v-if="group.issues.length > 1" class="count-pill">{{
                    group.issues.length
                  }}</span>
                </span>
                <button
                  v-if="group.recordId"
                  type="button"
                  class="btn small"
                  :aria-label="
                    group.issues.length > 1
                      ? i18n.tf('pdf_corpus.fix_record_issues', {
                          count: group.issues.length,
                          record: group.recordId,
                        })
                      : i18n.tf('pdf_corpus.fix_issue_labelled', {
                          reason: issueGroupLabel(group.issues[0]),
                        })
                  "
                  @click="emit('fixIssue', group.issues[0])"
                >
                  {{ i18n.t("pdf_corpus.fix_this_issue") }}
                </button>
              </div>
              <ul class="issue-group-reasons">
                <li v-for="(issue, index) in group.issues" :key="`${issue.code}-${index}`">
                  {{ issueGroupLabel(issue) }}
                </li>
              </ul>
            </li>
          </ul>
          <button
            v-if="groupedValidationIssues.length > 5"
            type="button"
            class="link-button"
            :aria-expanded="showAllIssueGroups"
            @click="showAllIssueGroups = !showAllIssueGroups"
          >
            {{
              showAllIssueGroups
                ? i18n.t("pdf_corpus.validation_show_fewer")
                : i18n.tf("pdf_corpus.validation_more_records", {
                    count: groupedValidationIssues.length - 5,
                  })
            }}
          </button>
        </div>
      </section>
      </div>
    </details>
  </section>
</template>

<style scoped>
.finish-workspace {
  display: grid;
  min-width: 0;
  gap: var(--space-4);
}
.publication-head {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: flex-start;
}
.publish-decision {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-5);
  align-items: center;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.publish-decision[data-state="blocked"] {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
}
.publish-decision[data-state="ready"] {
  border-color: var(--tone-ok-border);
  background: var(--tone-ok-bg);
}
.publish-decision-copy {
  min-width: 0;
}
.publish-decision-copy h3 {
  margin: var(--space-1) 0;
  font-size: var(--fs-lg);
}
.publish-decision-copy p {
  max-width: 72ch;
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.5;
}
.eyebrow,
.readiness-state {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.readiness-state {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}
.readiness-state svg {
  width: 0.9em;
  height: 0.9em;
  flex: none;
}
.readiness-state[data-tone="attention"] svg {
  color: var(--tone-warn-fg);
}
.readiness-state[data-tone="ok"] svg {
  color: var(--tone-ok-fg);
}
.publication-primary {
  display: flex;
  min-width: 0;
  align-items: center;
}
.publication-primary :deep(.btn),
.publication-primary :deep(.ui-button) {
  max-width: 100%;
  white-space: normal;
}
.no-publishable,
.publication-snapshot,
.publication-blockers,
.readiness-details {
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
  border-color: var(--tone-ok-border);
  background: var(--tone-ok-bg);
}
.publication-snapshot .not-conformant {
  grid-column: 1 / -1;
  margin: 0;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--tone-warn-border);
  border-radius: var(--radius-card);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
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
.blocker-copy {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}
.blocker-title {
  display: flex;
  gap: var(--space-2);
  align-items: baseline;
}
.blocker-detail {
  max-width: 72ch;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  line-height: 1.45;
}
.count-pill {
  display: inline-grid;
  min-width: 1.3rem;
  height: 1.3rem;
  padding-inline: 0.35em;
  place-items: center;
  border-radius: 999px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  line-height: 1;
}
.readiness-details {
  overflow: hidden;
  background: var(--surface-card);
}
.readiness-details > summary {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  cursor: pointer;
  list-style: none;
}
.readiness-details > summary::-webkit-details-marker {
  display: none;
}
.readiness-details > summary > span:first-child {
  display: grid;
  min-width: 0;
  gap: 2px;
}
.readiness-details > summary small {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: normal;
}
.readiness-details-affordance {
  color: var(--accent-fg);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.readiness-details[open] .readiness-details-affordance {
  opacity: 0.75;
}
.publication-readiness-list {
  display: grid;
  border-top: 1px solid var(--border-subtle);
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
  box-shadow: inset 3px 0 0 var(--tone-ok-fg);
}
/* A gate that has passed is one quiet line; only the gates still blocking publication take room. */
.readiness-row[data-state="complete"] {
  padding-block: var(--space-2);
}
.readiness-row[data-state="complete"] > dl {
  display: none;
}
.readiness-row[data-state="complete"] .readiness-row-copy {
  display: flex;
  flex-wrap: wrap;
  gap: 0 var(--space-3);
  align-items: baseline;
}
.readiness-row[data-state="complete"] .readiness-row-copy h3 {
  margin: 0;
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
  padding-block: var(--space-2);
}
.validation-issue-summary li + li {
  border-top: 1px solid var(--border-subtle);
}
.issue-group-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}
.issue-group-heading {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: var(--space-2);
}
.issue-group-heading code {
  overflow-wrap: anywhere;
  font-size: var(--fs-xs);
}
.issue-group-reasons {
  display: grid;
  gap: var(--space-1);
  margin: var(--space-1) 0 0;
  padding-left: var(--space-4);
  list-style: disc;
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
  .publish-decision,
  .no-publishable {
    display: grid;
    grid-template-columns: 1fr;
  }
  .publication-primary :deep(.btn),
  .publication-primary :deep(.ui-button) {
    width: 100%;
  }
  .publication-snapshot {
    grid-template-columns: 1fr;
  }
  .publication-blockers li {
    align-items: flex-start;
    flex-direction: column;
  }
  .issue-group-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
