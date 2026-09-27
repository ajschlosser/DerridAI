<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { ref, useId, watch } from "vue";
import { corpusBuilderApi, type RecordResearchClaim } from "../api/corpus";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";

// Research claims a reviewer validated that cite this record. A cross-reference for the
// metadata reviewer, not metadata memory: it never suggests or sets a field value, and
// support bound to an earlier revision is shown as stale.
const props = withDefaults(
  defineProps<{
    buildId: string;
    recordId: string;
    /** Injected for Storybook and tests; defaults to the corpus API. */
    load?: (buildId: string, recordId: string) => Promise<{ items: RecordResearchClaim[] }>;
  }>(),
  { load: undefined },
);

const i18n = useI18nStore();
const panelId = useId();
const open = ref(false);
const loading = ref(false);
const error = ref("");
const items = ref<RecordResearchClaim[] | null>(null);

watch(
  () => [props.buildId, props.recordId],
  () => {
    items.value = null;
    error.value = "";
    if (open.value) void fetchClaims();
  },
);

async function fetchClaims() {
  loading.value = true;
  error.value = "";
  try {
    const load = props.load ?? corpusBuilderApi.researchClaims;
    items.value = (await load(props.buildId, props.recordId)).items;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

function toggle() {
  open.value = !open.value;
  if (open.value && items.value === null && !loading.value) void fetchClaims();
}

function statusBadge(item: RecordResearchClaim) {
  if (item.binding_status === "current")
    return { label: i18n.t("pdf_corpus.research_claim_current"), tone: "success" as const };
  if (item.binding_status === "stale")
    return { label: i18n.t("pdf_corpus.research_claim_stale"), tone: "warning" as const };
  return { label: i18n.t("pdf_corpus.research_claim_unresolved"), tone: "neutral" as const };
}
</script>

<template>
  <section class="record-research-claims">
    <button
      type="button"
      class="btn small record-research-claims-toggle"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="toggle"
    >
      {{ i18n.t("pdf_corpus.research_claims_toggle") }}
    </button>
    <div v-if="open" :id="panelId" class="record-research-claims-panel">
      <p class="record-research-claims-note">{{ i18n.t("pdf_corpus.research_claims_advisory") }}</p>
      <p v-if="loading" role="status">{{ i18n.t("pdf_corpus.research_claims_loading") }}</p>
      <p v-else-if="error" role="alert" class="record-research-claims-error">
        {{ i18n.tf("pdf_corpus.research_claims_error", { detail: error }) }}
      </p>
      <p v-else-if="items && !items.length" role="status">
        {{ i18n.t("pdf_corpus.research_claims_empty") }}
      </p>
      <ul v-else-if="items" class="record-research-claims-list">
        <li v-for="item in items" :key="`${item.claim_id}:${item.record_revision}`">
          <div class="record-research-claims-head">
            <UiStatusBadge :label="statusBadge(item).label" :tone="statusBadge(item).tone" />
            <span v-if="item.relation" class="record-research-claims-meta">{{
              item.relation
            }}</span>
          </div>
          <p class="record-research-claims-text">{{ item.claim_text }}</p>
          <p class="record-research-claims-meta">
            <span v-if="item.citation.inline">{{ item.citation.inline }} · </span>
            {{
              i18n.tf("pdf_corpus.research_claim_validated", {
                reviewer: item.validated_by || "—",
                revision: item.record_revision ?? "—",
              })
            }}
          </p>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.record-research-claims {
  display: grid;
  gap: 6px;
}
.record-research-claims-toggle {
  justify-self: start;
}
.record-research-claims-panel {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
}
.record-research-claims-note,
.record-research-claims-meta {
  margin: 0;
  color: var(--muted);
  font-size: 0.75rem;
}
.record-research-claims-error {
  margin: 0;
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
}
.record-research-claims-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.record-research-claims-head {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
}
.record-research-claims-text {
  margin: 0;
  font-size: 0.8125rem;
  overflow-wrap: anywhere;
}
</style>
