<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import type { CorpusBuild } from "../api/corpus";
import { useI18nStore } from "../stores/i18n";

const props = defineProps<{
  run?: CorpusBuild["document_intelligence"] | null;
  requestedProvider?: string;
}>();
const i18n = useI18nStore();

const status = computed(() => String(props.run?.status || "queued"));
const statusLabel = computed(() =>
  i18n.t(
    `pdf_corpus.document_intelligence_status.${status.value}`,
    status.value.replaceAll("_", " "),
  ),
);
const selectedProvider = computed(() =>
  String(props.run?.selected_provider || props.requestedProvider || "auto"),
);
const actualProvider = computed(() => String(props.run?.provider || ""));
const usedFallback = computed(
  () =>
    status.value === "ok" &&
    selectedProvider.value === "auto" &&
    Boolean(actualProvider.value) &&
    actualProvider.value !== "booknlp",
);
const counts = computed(() =>
  [
    ["entity_mentions", Number(props.run?.entity_mentions || 0)],
    ["quotations", Number(props.run?.quotations || 0)],
    ["events", Number(props.run?.events || 0)],
  ].filter(([, count]) => Number(count) > 0),
);
</script>

<template>
  <section v-if="run" class="document-intelligence-result" :data-status="status" role="status">
    <div class="result-heading">
      <div>
        <span class="eyebrow">{{ i18n.t("pdf_corpus.document_intelligence") }}</span>
        <h3>{{ statusLabel }}</h3>
      </div>
      <span class="status-pill">{{ statusLabel }}</span>
    </div>
    <dl>
      <div>
        <dt>{{ i18n.t("pdf_corpus.document_intelligence_requested") }}</dt>
        <dd>{{ selectedProvider }}</dd>
      </div>
      <div>
        <dt>{{ i18n.t("pdf_corpus.document_intelligence_analyzer_used") }}</dt>
        <dd>
          {{ actualProvider || i18n.t("pdf_corpus.not_available") }}
          <template v-if="run.model"> · {{ run.model }}</template>
          <template v-if="run.provider_version"> · v{{ run.provider_version }}</template>
        </dd>
      </div>
      <div v-if="run.capabilities?.length">
        <dt>{{ i18n.t("pdf_corpus.document_intelligence_capabilities") }}</dt>
        <dd>{{ run.capabilities.join(" · ") }}</dd>
      </div>
    </dl>
    <p v-if="usedFallback" class="result-note">
      {{ i18n.t("pdf_corpus.document_intelligence_fallback") }}
    </p>
    <p v-if="run.reason" class="result-note">
      {{ i18n.tf("pdf_corpus.document_intelligence_reason", { reason: run.reason }) }}
    </p>
    <div v-if="counts.length" class="result-counts">
      <span v-for="[kind, count] in counts" :key="String(kind)">
        <b>{{ count }}</b>
        {{ i18n.t(`pdf_corpus.document_intelligence_count.${kind}`, String(kind)) }}
      </span>
    </div>
    <details v-if="run.warnings?.length">
      <summary>
        {{ i18n.tf("pdf_corpus.document_intelligence_warnings", { count: run.warnings.length }) }}
      </summary>
      <ul>
        <li v-for="warning in run.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </details>
  </section>
</template>

<style scoped>
.document-intelligence-result {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--surface-subtle);
}
.result-heading {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  justify-content: space-between;
}
.eyebrow {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
h3 {
  margin: var(--space-1) 0 0;
  font-size: 0.9375rem;
}
.status-pill {
  padding: 0.25rem 0.55rem;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-raised);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}
dl > div {
  min-width: 0;
}
dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
dd {
  margin: var(--space-1) 0 0;
  overflow-wrap: anywhere;
  font-size: var(--fs-sm);
}
.result-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.result-counts {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
details {
  font-size: var(--fs-sm);
}
summary {
  cursor: pointer;
  font-weight: var(--fw-semibold);
}
@media (max-width: 760px) {
  dl {
    grid-template-columns: 1fr;
  }
}
</style>
