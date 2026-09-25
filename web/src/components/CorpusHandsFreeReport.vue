<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { AutonomousReport } from "../api/pdfCorpus";

// What a hands-free run did and did not settle, so a person reviews only the exceptions.
const props = defineProps<{ report: AutonomousReport | null | undefined }>();
const emit = defineEmits<{ "open-record": [recordId: string] }>();
const i18n = useI18nStore();
const shown = computed(() => (props.report?.exceptions ?? []).slice(0, 12));
const more = computed(() => Math.max(0, (props.report?.left_for_review ?? 0) - shown.value.length));
</script>

<template>
  <section v-if="report" class="hf-report" aria-labelledby="hf-report-title">
    <h3 id="hf-report-title">{{ i18n.t("pdf_corpus.hands_free_report_title") }}</h3>
    <p>
      {{
        i18n.tf("pdf_corpus.hands_free_report_summary", {
          accepted: report.accepted,
          records: report.records,
          filled: report.fields_filled,
          left: report.left_for_review,
        })
      }}
      <span v-if="report.published">{{ i18n.t("pdf_corpus.hands_free_published") }}</span>
    </p>
    <ul v-if="report.notes?.length" class="hf-notes">
      <li v-for="note in report.notes" :key="note">{{ note }}</li>
    </ul>
    <ul
      v-if="shown.length"
      class="hf-exceptions"
      :aria-label="i18n.t('pdf_corpus.hands_free_left')"
    >
      <li v-for="item in shown" :key="item.record_id">
        <button type="button" class="link-button" @click="emit('open-record', item.record_id)">
          {{ item.record_id }}
        </button>
        <span>{{ item.reasons.join("; ") }}</span>
      </li>
    </ul>
    <p v-if="more" class="hf-more">{{ i18n.tf("pdf_corpus.hands_free_more", { count: more }) }}</p>
  </section>
</template>

<style scoped>
.hf-report {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid var(--tone-info-border);
  border-radius: 12px;
  background: var(--tone-info-bg);
  color: var(--text);
}
h3 {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--tone-info-fg);
}
p {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
}
ul {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.hf-exceptions li {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  align-items: baseline;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--card);
  font-size: 0.8125rem;
}
.hf-exceptions span {
  color: var(--text-2);
}
.link-button {
  border: 0;
  background: none;
  padding: 0;
  color: var(--accent-fg);
  font: inherit;
  font-weight: 700;
  text-decoration: underline;
  cursor: pointer;
}
.link-button:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
.hf-notes {
  color: var(--text-2);
  font-size: 0.8125rem;
}
.hf-more {
  color: var(--muted);
  font-size: 0.8125rem;
}
</style>
