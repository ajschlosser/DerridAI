<script setup lang="ts">
import { computed } from "vue";
import type { CorpusBuild } from "../api/pdfCorpus";
import { useI18nStore } from "../stores/i18n";

const props = defineProps<{ build: CorpusBuild; busy?: boolean }>();
const emit = defineEmits<{
  retryMetadata: [];
  reviewMetadata: [];
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
  else if (next.value === "resolve_validation") emit("reviewRecords");
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
  else if (value === "required_metadata" || value === "metadata_validation") emit("reviewMetadata");
  else if (value === "source_quality" || value === "source_validation") emit("reviewSource");
  else emit("reviewRecords");
}
</script>

<template>
  <section class="finish-workspace" aria-labelledby="finish-corpus-title">
    <header class="finish-head">
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
      <div class="finish-primary">
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
        <span class="card-state">{{ i18n.t("pdf_corpus.no_publishable_status") }}</span>
        <h3 id="no-publishable-title">{{ i18n.t("pdf_corpus.no_publishable_title") }}</h3>
        <p>{{ i18n.t("pdf_corpus.no_publishable_help") }}</p>
      </div>
      <div class="card-actions">
        <button type="button" class="btn primary" @click="emit('reviewRejected')">
          {{ i18n.t("pdf_corpus.return_to_review") }}</button
        ><button type="button" class="btn" :disabled="busy" @click="emit('restoreRejected')">
          {{ i18n.t("pdf_corpus.restore_all_rejected") }}</button
        ><button type="button" class="btn" @click="emit('startNew')">
          {{ i18n.t("pdf_corpus.start_new_build") }}
        </button>
      </div>
    </section>

    <div v-if="readiness.missing_document_fields?.length" class="document-blocker" role="alert">
      <b>{{ i18n.t("pdf_corpus.readiness_blocker.required_document_metadata") }}</b
      ><span>{{
        readiness.missing_document_fields
          .map((field) => i18n.t(`record.${field}`, field.replace(/_/g, " ")))
          .join(", ")
      }}</span>
    </div>

    <div v-if="!noPublishable" class="finish-grid">
      <article class="finish-card" data-state="complete">
        <span class="card-state">{{ i18n.t("pdf_corpus.complete") }}</span>
        <h3>{{ i18n.t("pdf_corpus.record_review") }}</h3>
        <dl>
          <div>
            <dt>{{ i18n.t("pdf_corpus.reviewed") }}</dt>
            <dd>{{ readiness.records_reviewed || 0 }} / {{ readiness.records_total || 0 }}</dd>
          </div>
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
        <button
          v-if="Number(readiness.records_rejected || 0) > 0"
          type="button"
          class="link-action"
          @click="emit('reviewRejected')"
        >
          {{ i18n.t("pdf_corpus.review_rejected_records") }}
        </button>
      </article>

      <article
        class="finish-card"
        :data-state="Number(summary.fields_unresolved || 0) > 0 ? 'attention' : 'complete'"
      >
        <span class="card-state">{{
          Number(summary.fields_unresolved || 0) > 0
            ? i18n.t("pdf_corpus.attention_required")
            : i18n.t("pdf_corpus.complete")
        }}</span>
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
        <div class="card-actions">
          <button
            v-if="Number(summary.fields_unresolved || 0) > 0"
            type="button"
            class="btn"
            @click="emit('reviewMetadata')"
          >
            {{ i18n.t("pdf_corpus.open_metadata_queue") }}</button
          ><button
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
            }}</button
          ><button type="button" class="btn" :disabled="busy" @click="emit('rerunEnrichment')">
            {{ i18n.t("pdf_corpus.metadata_enrichment_again") }}
          </button>
        </div>
      </article>

      <article class="finish-card" :data-state="validation.valid ? 'complete' : 'attention'">
        <span class="card-state">{{
          validation.valid ? i18n.t("pdf_corpus.complete") : i18n.t("pdf_corpus.attention_required")
        }}</span>
        <h3>{{ i18n.t("pdf_corpus.final_validation") }}</h3>
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
      </article>

      <article
        class="finish-card"
        :data-state="publication ? 'complete' : readiness.can_publish ? 'ready' : 'waiting'"
      >
        <span class="card-state">{{
          publication
            ? i18n.t("pdf_corpus.complete")
            : readiness.can_publish
              ? i18n.t("pdf_corpus.ready")
              : i18n.t("pdf_corpus.waiting")
        }}</span>
        <h3>{{ i18n.t("pdf_corpus.publication") }}</h3>
        <p v-if="publication">
          {{
            i18n.tf("pdf_corpus.publication_snapshot_summary", { count: publication.record_count })
          }}
        </p>
        <p v-else-if="readiness.can_publish">{{ i18n.t("pdf_corpus.publication_ready_help") }}</p>
        <p v-else>{{ i18n.t("pdf_corpus.publication_waiting_help") }}</p>
      </article>
    </div>

    <details v-if="blockers.length && !noPublishable" class="blockers">
      <summary>
        {{ i18n.tf("pdf_corpus.view_publication_blockers", { count: blockers.length }) }}
      </summary>
      <ul>
        <li v-for="(blocker, index) in blockers" :key="`${blocker.code}-${index}`">
          <span
            ><b>{{ blockerLabel(blocker.code) }}</b
            ><span v-if="blocker.count"> · {{ blocker.count }}</span></span
          ><button type="button" class="link-action" @click="fixBlocker(blocker.code)">
            {{ i18n.t("pdf_corpus.go_fix") }}
          </button>
        </li>
      </ul>
    </details>
  </section>
</template>

<style scoped>
.finish-workspace {
  display: grid;
  min-width: 0;
  gap: 16px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: var(--card);
}
.finish-head {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 22px;
  align-items: flex-start;
}
.finish-head > div {
  min-width: 0;
  flex: 1 1 320px;
}
.finish-head h2 {
  margin: 3px 0 6px;
  font-size: 1.25rem;
}
.finish-head p {
  margin: 0;
  max-width: 78ch;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--muted);
}
.eyebrow {
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-weight: 800;
}
.finish-primary {
  display: flex;
  min-width: 0;
  flex: 0 1 auto;
  align-items: center;
}
.finish-primary .btn {
  max-width: 100%;
  white-space: normal;
}
.no-publishable {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 16px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 11px;
  background: var(--tone-warn-bg);
}
.no-publishable h3 {
  margin: 3px 0 5px;
  font-size: 1rem;
}
.no-publishable p {
  margin: 0;
  max-width: 72ch;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--muted);
}
.document-blocker {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
  padding: 11px 13px;
  border: 1px solid var(--tone-warn-edge);
  border-radius: 9px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.8125rem;
}
.document-blocker span {
  color: var(--muted);
}
.finish-grid {
  display: grid;
  min-width: 0;
  grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
  gap: 10px;
}
.finish-card {
  display: grid;
  min-width: 0;
  align-content: start;
  gap: 9px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.finish-card[data-state="attention"] {
  background: var(--tone-warn-bg);
  border-color: var(--tone-warn-edge);
}
.finish-card[data-state="ready"],
.finish-card[data-state="complete"] {
  background: var(--tone-ok-bg);
}
.card-state {
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  font-weight: 800;
}
.finish-card h3 {
  margin: 0;
  font-size: 0.8125rem;
}
.finish-card p {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.48;
  color: var(--muted);
}
dl {
  display: grid;
  min-width: 0;
  grid-template-columns: repeat(auto-fit, minmax(min(140px, 100%), 1fr));
  gap: 7px;
  margin: 0;
}
dl div {
  padding-inline-start: 8px;
  border-inline-start: 2px solid var(--line);
}
dt {
  font-size: 0.8125rem;
  color: var(--muted);
}
dd {
  margin: 2px 0 0;
  font-size: 0.8125rem;
  font-weight: 800;
}
.card-actions {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}
.card-actions .btn {
  max-width: 100%;
  white-space: normal;
  text-align: center;
}
.link-action {
  justify-self: start;
  border: 0;
  background: transparent;
  color: var(--accent-fg);
  padding: 0;
  text-decoration: underline;
  font-size: 0.8125rem;
  cursor: pointer;
}
.blockers {
  font-size: 0.8125rem;
}
.blockers summary {
  cursor: pointer;
  font-weight: 800;
}
.blockers ul {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 7px;
  color: var(--muted);
}
.blockers li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-top: 1px solid var(--line);
}
@media (max-width: 760px) {
  .finish-head {
    display: grid;
  }
  .finish-grid {
    grid-template-columns: 1fr;
  }
  .finish-primary .btn {
    width: 100%;
  }
}
</style>
