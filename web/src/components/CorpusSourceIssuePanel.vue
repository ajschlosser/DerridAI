<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";

const props = defineProps<{
  issues?: Array<Record<string, unknown>>;
  resolved?: boolean;
  interactive?: boolean;
}>();
const emit = defineEmits<{ editText: []; openSource: [] }>();
const i18n = useI18nStore();
const rows = computed(() => props.issues || []);

function hasPages(issue: Record<string, unknown>) {
  return Array.isArray(issue.pages) && issue.pages.length > 0;
}

function pages(issue: Record<string, unknown>) {
  return hasPages(issue) ? (issue.pages as unknown[]).join(", ") : "";
}

function label(issue: Record<string, unknown>) {
  const code = String(issue.code || "source_quality");
  const key = `pdf_corpus.source_issue.${code}`;
  const text = i18n.t(key);
  return text === key ? i18n.t("pdf_corpus.source_issue_title") : text;
}
</script>

<template>
  <section
    v-if="rows.length"
    class="source-issues"
    :data-resolved="resolved ? 'true' : 'false'"
    role="note"
    :aria-label="
      resolved
        ? i18n.t('pdf_corpus.source_issue_resolved')
        : i18n.t('pdf_corpus.source_issue_title')
    "
  >
    <header>
      <div>
        <b>{{
          resolved
            ? i18n.t("pdf_corpus.source_issue_resolved")
            : i18n.t("pdf_corpus.source_issue_title")
        }}</b>
        <span>{{
          resolved
            ? i18n.t("pdf_corpus.source_issue_resolved_help")
            : i18n.t("pdf_corpus.source_issue_help_v48")
        }}</span>
      </div>
      <div v-if="interactive && !resolved" class="source-actions">
        <UiButton
          size="small"
          :label="i18n.t('pdf_corpus.inspect_source')"
          @click="emit('openSource')"
        />
        <UiButton
          size="small"
          variant="primary"
          :label="i18n.t('pdf_corpus.correct_reviewed_text')"
          @click="emit('editText')"
        />
      </div>
    </header>

    <ol v-if="!resolved" class="resolution-steps">
      <li>{{ i18n.t("pdf_corpus.source_resolution_step_1") }}</li>
      <li>{{ i18n.t("pdf_corpus.source_resolution_step_2") }}</li>
      <li>{{ i18n.t("pdf_corpus.source_resolution_step_3") }}</li>
    </ol>

    <article v-for="(issue, index) in rows" :key="`${issue.code || 'issue'}-${index}`">
      <div>
        <strong>{{ label(issue) }}</strong>
        <span>
          <span class="severity">{{
            i18n.t(
              `pdf_corpus.source_severity.${String(issue.severity || "warning")}`,
              String(issue.severity || "warning"),
            )
          }}</span>
          <template v-if="hasPages(issue)">
            · {{ i18n.t("pdf_corpus.pages") }} {{ pages(issue) }}
          </template>
        </span>
      </div>
      <p>{{ String(issue.message || i18n.t("pdf_corpus.source_issue_default")) }}</p>
      <small v-if="issue.micro_line_ratio !== undefined">
        {{ i18n.t("pdf_corpus.fragmentation_ratio") }}:
        {{ Math.round(Number(issue.micro_line_ratio || 0) * 100) }}%
      </small>
    </article>
  </section>
</template>

<style scoped>
.source-issues {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--tone-warn-border);
  border-radius: var(--radius-card);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}

.source-issues[data-resolved="true"] {
  border-color: var(--tone-ok-border);
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}

.source-issues header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: flex-start;
}

.source-issues header > div:first-child {
  display: grid;
  gap: var(--space-1);
  max-width: var(--measure);
}

.source-issues header b {
  font-size: var(--fs-base);
}

.source-issues header span,
.source-issues p,
.source-issues small,
.resolution-steps {
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}

.source-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  flex: none;
}

.resolution-steps {
  margin: 0;
  padding: var(--space-3) var(--space-4) var(--space-3) var(--space-7);
  border-radius: var(--radius-control);
  background: color-mix(in srgb, currentColor 6%, transparent);
}

.resolution-steps li + li {
  margin-top: var(--space-1);
}

.source-issues article {
  display: grid;
  gap: var(--space-1);
  padding-top: var(--space-2);
  border-top: 1px solid color-mix(in srgb, currentColor 18%, transparent);
}

.source-issues article > div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.source-issues strong {
  font-size: var(--fs-base);
}

.severity {
  font-weight: var(--fw-bold);
  text-transform: capitalize;
}

.source-issues p {
  margin: 0;
}

.source-issues small {
  opacity: 0.85;
}

@media (max-width: 720px) {
  .source-issues header {
    flex-direction: column;
  }

  .source-actions {
    width: 100%;
  }

  .source-actions :deep(.ui-button-wrap) {
    flex: 1;
  }

  .source-actions :deep(.ui-button) {
    width: 100%;
  }
}
</style>
