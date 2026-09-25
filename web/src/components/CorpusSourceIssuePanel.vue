<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
const props = defineProps<{
  issues?: Array<Record<string, unknown>>;
  resolved?: boolean;
  interactive?: boolean;
}>();
const emit = defineEmits<{ editText: []; openSource: [] }>();
const i18n = useI18nStore();
const rows = computed(() => props.issues || []);
function pages(issue: Record<string, unknown>) {
  return Array.isArray(issue.pages) && issue.pages.length ? issue.pages.join(", ") : "—";
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
        }}</b
        ><span>{{
          resolved
            ? i18n.t("pdf_corpus.source_issue_resolved_help")
            : i18n.t("pdf_corpus.source_issue_help_v48")
        }}</span>
      </div>
      <div v-if="interactive && !resolved" class="source-actions">
        <button type="button" class="btn small" @click="emit('openSource')">
          {{ i18n.t("pdf_corpus.inspect_source") }}</button
        ><button type="button" class="btn small primary" @click="emit('editText')">
          {{ i18n.t("pdf_corpus.correct_reviewed_text") }}
        </button>
      </div>
    </header>
    <ol v-if="!resolved" class="resolution-steps">
      <li>{{ i18n.t("pdf_corpus.source_resolution_step_1") }}</li>
      <li>{{ i18n.t("pdf_corpus.source_resolution_step_2") }}</li>
      <li>{{ i18n.t("pdf_corpus.source_resolution_step_3") }}</li>
    </ol>
    <article v-for="(issue, index) in rows" :key="`${issue.code || 'issue'}-${index}`">
      <div>
        <strong>{{ label(issue) }}</strong
        ><span
          ><span class="severity">{{
            i18n.t(
              `pdf_corpus.source_severity.${String(issue.severity || "warning")}`,
              String(issue.severity || "warning"),
            )
          }}</span>
          · {{ i18n.t("pdf_corpus.pages") }} {{ pages(issue) }}</span
        >
      </div>
      <p>{{ String(issue.message || i18n.t("pdf_corpus.source_issue_default")) }}</p>
      <small v-if="issue.micro_line_ratio !== undefined"
        >{{ i18n.t("pdf_corpus.fragmentation_ratio") }}:
        {{ Math.round(Number(issue.micro_line_ratio || 0) * 100) }}%</small
      >
    </article>
  </section>
</template>
<style scoped>
.source-issues {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--tone-warn-border);
  border-radius: 12px;
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
  gap: 14px;
  align-items: flex-start;
}
.source-issues header > div:first-child {
  display: grid;
  gap: 4px;
  max-width: 76ch;
}
.source-issues header b {
  font-size: 0.9375rem;
}
.source-issues header span,
.source-issues p,
.source-issues small,
.resolution-steps {
  font-size: 0.8125rem;
  line-height: 1.55;
}
.source-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  flex: none;
}
.resolution-steps {
  margin: 0;
  padding: 10px 12px 10px 30px;
  border-radius: 9px;
  background: color-mix(in srgb, currentColor 6%, transparent);
}
.resolution-steps li + li {
  margin-top: 4px;
}
.source-issues article {
  display: grid;
  gap: 4px;
  padding-top: 9px;
  border-top: 1px solid color-mix(in srgb, currentColor 18%, transparent);
}
.source-issues article > div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.source-issues strong {
  font-size: 0.875rem;
}
.severity {
  font-weight: 800;
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
  .source-actions .btn {
    flex: 1;
  }
}
</style>
