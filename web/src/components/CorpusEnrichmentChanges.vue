<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";

// What the last enrichment pass did to this record: the values it added, the values it replaced (with the ones it
// replaced), and the fields where it disagreed with the current value and left it for a person to decide. The record
// is reopened for review with the words "review the highlighted changes"; this is where they are.
interface Replaced { field: string; previous: unknown; value: unknown }
interface Candidate { value: unknown; source?: string; model?: string }
interface Dispute { field: string; existing: unknown; proposed: unknown; candidates?: Candidate[]; reason?: string | null }
interface HistoryEntry { run_id?: string; model?: string; outcome?: string; added_fields?: string[]; replaced?: Replaced[]; disputes?: Dispute[] }

const props = defineProps<{ record: Record<string, unknown>; busy?: boolean }>();
const emit = defineEmits<{ resolve: [field: string, value: unknown] }>();
const i18n = useI18nStore();

const owned = new Set(["human_confirmed", "human_override"]);
const stateOf = (field: string) => String(((props.record.metadata_field_status as Record<string, { status?: string }> | undefined)?.[field]?.status) ?? "");
const last = computed<HistoryEntry | null>(() => {
  const history = (props.record.metadata_enrichment_history as HistoryEntry[] | undefined) ?? [];
  const entry = [...history].reverse().find(item => item.outcome === "enriched" || item.outcome === "disputed");
  return entry ?? null;
});
// A change stays listed until a person has decided that field.
const added = computed(() => (last.value?.added_fields ?? []).filter(field => !owned.has(stateOf(field))));
const replaced = computed(() => (last.value?.replaced ?? []).filter(item => !owned.has(stateOf(item.field))));
const disputes = computed(() => (last.value?.disputes ?? []).filter(item => !owned.has(stateOf(item.field))));
const visible = computed(() => Boolean(props.record.needs_review) && added.value.length + replaced.value.length + disputes.value.length > 0);

const label = (field: string) => i18n.t(`record.${field}`, field.replaceAll("_", " "));
const candidatesFor = (item: Dispute): Candidate[] => item.candidates?.length ? item.candidates : [{ value: item.existing, source: "current" }, { value: item.proposed, source: "proposed" }];
const candidateLabel = (candidate: Candidate) => candidate.source === "current" ? i18n.t("pdf_corpus.change_keep_current", "Keep current") : candidate.source === "proposed" && !candidate.model ? i18n.t("pdf_corpus.change_use_proposed", "Use proposed") : i18n.tf("pdf_corpus.change_use_candidate", "Use {candidate}", { candidate: candidate.model || candidate.source || i18n.t("pdf_corpus.change_proposed", "proposed") });
function show(value: unknown): string {
  if (value === true) return i18n.t("ui.yes", "Yes");
  if (value === false) return i18n.t("ui.no", "No");
  if (Array.isArray(value)) return value.join(", ") || "—";
  return value === null || value === undefined || value === "" ? "—" : String(value);
}
</script>

<template>
  <section v-if="visible" class="enrichment-changes" aria-labelledby="enrichment-changes-title">
    <header>
      <h4 id="enrichment-changes-title">{{ i18n.t("pdf_corpus.enrichment_changes_title", "Changed by the last enrichment pass") }}</h4>
      <p v-if="last?.model">{{ i18n.tf("pdf_corpus.enrichment_changes_model", "Model: {model}. Nothing here is confirmed until you decide it.", { model: last.model }) }}</p>
    </header>
    <ul>
      <li v-for="field in added" :key="`a-${field}`" data-kind="added">
        <span class="kind">{{ i18n.t("pdf_corpus.change_added", "Added") }}</span>
        <span class="what"><b>{{ label(field) }}</b>: {{ show(record[field]) }}</span>
      </li>
      <li v-for="item in replaced" :key="`r-${item.field}`" data-kind="replaced">
        <span class="kind">{{ i18n.t("pdf_corpus.change_replaced", "Replaced") }}</span>
        <span class="what"><b>{{ label(item.field) }}</b>: <s>{{ show(item.previous) }}</s> → {{ show(item.value) }}</span>
        <button type="button" class="btn small" :disabled="busy" @click="emit('resolve', item.field, item.previous)">{{ i18n.t("pdf_corpus.change_restore", "Restore previous") }}</button>
      </li>
      <li v-for="item in disputes" :key="`d-${item.field}`" data-kind="disputed">
        <span class="kind">{{ i18n.t("pdf_corpus.change_disputed", "Disagreement") }}</span>
        <span class="what">
          <b>{{ label(item.field) }}</b>:
          {{ i18n.tf("pdf_corpus.change_dispute_values", "kept “{existing}”; the pass proposed “{proposed}”.", { existing: show(item.existing), proposed: show(item.proposed) }) }}
        </span>
        <span class="choices">
          <button v-for="(candidate, index) in candidatesFor(item)" :key="`${item.field}-${index}`" type="button" class="btn small" :disabled="busy" @click="emit('resolve', item.field, candidate.value)">{{ candidateLabel(candidate) }}<template v-if="candidate.model">: {{ show(candidate.value) }}</template></button>
        </span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.enrichment-changes { display: grid; gap: 8px; padding: 12px 14px; border: 1px solid var(--tone-info-border); border-radius: 12px; background: var(--tone-info-bg); color: var(--text); }
h4 { margin: 0; font-size: 0.9375rem; color: var(--tone-info-fg); }
header p { margin: 2px 0 0; font-size: 0.8125rem; color: var(--text-2); }
ul { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
/* The inspector is narrow, so the actions sit on their own line under the description instead of squeezing it. */
li { display: grid; grid-template-columns: max-content minmax(0, 1fr); align-items: baseline; gap: 6px 12px; padding: 8px 10px; border: 1px solid var(--line); border-inline-start-width: 4px; border-radius: 8px; background: var(--card); }
li[data-kind="added"] { border-inline-start-color: var(--tone-ok-edge); }
li[data-kind="replaced"] { border-inline-start-color: var(--tone-warn-edge); }
li[data-kind="disputed"] { border-inline-start-color: var(--tone-danger-edge); }
.kind { min-inline-size: 5.5rem; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-2); }
.what { font-size: 0.875rem; overflow-wrap: anywhere; }
.what s { color: var(--muted); }
.choices { display: flex; gap: 6px; flex-wrap: wrap; }
li > .choices, li > .btn { grid-column: 2; justify-self: start; }
@media (max-width: 420px) { li { grid-template-columns: minmax(0, 1fr); } li > .choices, li > .btn { grid-column: 1; } }
</style>
