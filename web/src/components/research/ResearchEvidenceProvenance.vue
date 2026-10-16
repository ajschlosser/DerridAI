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
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import type {
  ResearchClaimProvenance,
  ResearchClaimSupportBinding,
  ResearchResultEvidence,
} from "../../types/research";
import { segmentResearchAnswer } from "./researchAnswerFormatting";

// Shows only provenance the run actually recorded for one EvidenceRef. Source
// location, record revision, support binding and claim validation stay
// separate: a located passage is not a validated claim.
const props = defineProps<{
  evidence: ResearchResultEvidence;
  provenance?: ResearchClaimProvenance | null;
}>();
const i18n = useI18nStore();

function text(value: unknown) {
  if (Array.isArray(value)) return value.map(String).join(", ");
  return value == null ? "" : String(value).trim();
}
function range(start: unknown, end: unknown) {
  const from = text(start),
    to = text(end);
  if (!from) return "";
  return to && to !== from ? `${from}–${to}` : from;
}

const record = computed(() => props.evidence.record || {});
// MLA strings are built server-side from the Record's metadata; titles carry italics.
const mlaRows = computed(() =>
  [
    {
      key: "in_text",
      label: i18n.t("research.provenance_mla_in_text"),
      value: props.evidence.mla_in_text,
    },
    {
      key: "entry",
      label: i18n.t("research.provenance_mla_entry"),
      value: props.evidence.mla_citation,
    },
  ]
    .filter((row) => Boolean(row.value))
    .map((row) => ({ ...row, segments: segmentResearchAnswer(row.value || "", []) })),
);
// Source units come from the Record's own spans (or its recorded unit list);
// they are shown only when the run's evidence carried them.
const sourceUnits = computed(() => {
  const spans = Array.isArray(record.value.source_spans) ? record.value.source_spans : [];
  const fromSpans = spans.map((span: { source_unit_id?: unknown }) => text(span?.source_unit_id));
  const listed = Array.isArray(record.value.source_unit_ids) ? record.value.source_unit_ids : [];
  return [...new Set([...fromSpans, ...listed.map(text)].filter(Boolean))];
});
const sourceRows = computed(() =>
  [
    {
      key: "work",
      label: i18n.t("research.provenance_work"),
      value: text(record.value.document_title) || text(record.value.work),
    },
    {
      key: "edition",
      label: i18n.t("research.provenance_edition"),
      value: text(record.value.edition),
    },
    {
      key: "translator",
      label: i18n.t("research.provenance_translator"),
      value: text(record.value.translator),
    },
    {
      key: "source_document",
      label: i18n.t("research.provenance_source_document"),
      value: text(record.value.source_document_id),
    },
    {
      key: "source_units",
      label: i18n.t("research.provenance_source_units"),
      value: sourceUnits.value.join(", "),
    },
  ].filter((row) => row.value),
);

// Locator semantics follow the source medium: audio uses time, paged sources
// distinguish printed from physical pages. A missing locator is stated, not guessed.
const locator = computed(() => {
  const r = record.value;
  const time = range(r.time_start, r.time_end);
  if (time) {
    return i18n.tf("research.provenance_time", {
      start: text(r.time_start),
      end: text(r.time_end) || text(r.time_start),
    });
  }
  const printed = range(r.printed_page_start ?? r.printed_page_label, r.printed_page_end);
  const physical = range(
    r.physical_page_start ?? r.page_start ?? r.page,
    r.physical_page_end ?? r.page_end,
  );
  const parts = [
    printed ? i18n.tf("research.provenance_printed_pages", { pages: printed }) : "",
    physical ? i18n.tf("research.provenance_physical_pages", { pages: physical }) : "",
  ].filter(Boolean);
  return parts.join(" · ");
});

const revision = computed(() => {
  const value = Number(record.value.record_revision);
  return Number.isFinite(value) && value > 0 ? value : null;
});

const recordId = computed(() => text(record.value.record_id));
const claimsById = computed(
  () => new Map((props.provenance?.claims || []).map((claim) => [claim.claim_id, claim])),
);
// Bind by this run's evidence marker when present; otherwise by record identity.
// Never fall back to "any binding": an unrelated claim must not look supported.
const bindings = computed(() => {
  const marker = text(props.evidence.evidence_id);
  return (props.provenance?.support_bindings || []).filter((binding) => {
    const bindingMarker = text(binding.citation?.evidence_marker);
    if (bindingMarker && marker) return bindingMarker === marker;
    return Boolean(recordId.value) && binding.record_id === recordId.value;
  });
});

function revisionMismatch(binding: ResearchClaimSupportBinding) {
  if (binding.record_revision == null || revision.value == null) return "";
  if (Number(binding.record_revision) === revision.value) return "";
  return i18n.tf("research.provenance_revision_mismatch", {
    bound: binding.record_revision,
    current: revision.value,
  });
}
</script>

<template>
  <section class="research-evidence-provenance">
    <h5>{{ i18n.t("research.provenance_title") }}</h5>
    <dl class="research-evidence-provenance-source">
      <template v-for="row in sourceRows" :key="row.key">
        <dt>{{ row.label }}</dt>
        <dd>{{ row.value }}</dd>
      </template>
      <template v-for="row in mlaRows" :key="row.key">
        <dt>{{ row.label }}</dt>
        <dd>
          <template v-for="(segment, index) in row.segments" :key="index"
            ><em v-if="segment.italic">{{ segment.text }}</em
            ><template v-else>{{ segment.text }}</template></template
          >
        </dd>
      </template>
      <dt>{{ i18n.t("research.provenance_locator") }}</dt>
      <dd :class="{ 'research-evidence-provenance-missing': !locator }">
        {{ locator || i18n.t("research.provenance_locator_missing") }}
      </dd>
      <dt>{{ i18n.t("research.provenance_revision") }}</dt>
      <dd :class="{ 'research-evidence-provenance-missing': revision == null }">
        {{ revision ?? i18n.t("research.provenance_revision_missing") }}
      </dd>
    </dl>
    <h6>{{ i18n.t("research.provenance_bindings") }}</h6>
    <p v-if="!bindings.length" class="research-evidence-provenance-missing">
      {{ i18n.t("research.provenance_no_binding") }}
    </p>
    <ul v-else class="research-evidence-provenance-bindings">
      <li v-for="binding in bindings" :key="binding.support_binding_id">
        <p class="research-evidence-provenance-claim">
          {{ claimsById.get(binding.claim_id)?.claim_text || binding.claim_id }}
        </p>
        <dl>
          <dt>{{ i18n.t("research.provenance_relation") }}</dt>
          <dd>{{ binding.relation || i18n.t("research.provenance_relation_missing") }}</dd>
          <dt>{{ i18n.t("research.provenance_binding_status") }}</dt>
          <dd :data-status="binding.validation_status || 'unvalidated'">
            {{ i18n.t(`claims.binding_status_${binding.validation_status || "unvalidated"}`) }}
          </dd>
          <dt>{{ i18n.t("research.provenance_claim_status") }}</dt>
          <dd :data-status="claimsById.get(binding.claim_id)?.validation_status || 'unvalidated'">
            {{
              i18n.t(
                `claims.status_${claimsById.get(binding.claim_id)?.validation_status || "unvalidated"}`,
              )
            }}
          </dd>
        </dl>
        <p v-if="revisionMismatch(binding)" class="research-evidence-provenance-warning">
          {{ revisionMismatch(binding) }}
        </p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.research-evidence-provenance {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  overflow-wrap: anywhere;
}
.research-evidence-provenance h5,
.research-evidence-provenance h6 {
  margin: 0 0 8px;
  font-size: 0.875rem;
  line-height: 1.4;
}
.research-evidence-provenance h6 {
  margin-top: 12px;
}
.research-evidence-provenance dl {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 6px 16px;
  margin: 0;
}
.research-evidence-provenance dt {
  color: var(--text-tertiary);
}
.research-evidence-provenance dd {
  margin: 0;
}
.research-evidence-provenance-missing {
  color: var(--text-secondary);
  font-style: italic;
}
.research-evidence-provenance-bindings {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.research-evidence-provenance-bindings li {
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 7px;
}
.research-evidence-provenance-claim {
  margin: 0 0 8px;
}
.research-evidence-provenance-warning {
  margin: 8px 0 0;
  color: var(--warning);
  font-weight: 600;
}
</style>
