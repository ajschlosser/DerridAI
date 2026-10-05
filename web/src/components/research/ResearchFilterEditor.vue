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
import { computed, onBeforeUnmount, ref, useId, watch } from "vue";
import { researchFiltersApi } from "../../api/researchFilters";
import type {
  ResearchFilterDiagnostic,
  ResearchFilterPreview,
  ResearchFilterPreviewRequest,
} from "../../api/researchFilters";
import {
  explainResearchFilterPlan,
  parseResearchFilterExpression,
  researchFilterCatalog,
  suggestResearchFilterCompletions,
} from "../../domain/researchFilters";
import type { ResearchFilterPlanDraft } from "../../domain/researchFilters";
import { useI18nStore } from "../../stores/i18n";

export type ResearchFilterChange = {
  /** Compiled plan, or null when the expression is empty or invalid. */
  plan: ResearchFilterPlanDraft | null;
  valid: boolean;
};

const props = withDefaults(
  defineProps<{
    modelValue: string;
    collection: string;
    fields: string[];
    locales?: string[];
    disabled?: boolean;
    debounceMs?: number;
    /** Overridable for stories and tests; defaults to the Research preview endpoint. */
    preview?: (body: ResearchFilterPreviewRequest) => Promise<ResearchFilterPreview>;
  }>(),
  { locales: () => [], disabled: false, debounceMs: 400, preview: undefined },
);
const emit = defineEmits<{
  "update:modelValue": [value: string];
  change: [value: ResearchFilterChange];
}>();

const i18n = useI18nStore();
const uid = useId();
const inputId = `research-filter-${uid}`;
const helpId = `research-filter-help-${uid}`;
const statusId = `research-filter-status-${uid}`;

const catalog = computed(() => researchFilterCatalog(props.fields));
const parsed = computed(() => parseResearchFilterExpression(props.modelValue, catalog.value));
const plan = computed<ResearchFilterPlanDraft | null>(() => {
  const result = parsed.value;
  if (!result.ok) return null;
  const { metadata_filter, document_filter } = result.plan;
  return metadata_filter || document_filter ? result.plan : null;
});
const hasText = computed(() => props.modelValue.trim().length > 0);
const clauses = computed(() => (plan.value ? explainResearchFilterPlan(plan.value) : []));
const suggestions = computed(() =>
  props.disabled ? [] : suggestResearchFilterCompletions(props.modelValue, catalog.value),
);
const localErrors = computed(() =>
  parsed.value.ok
    ? []
    : parsed.value.errors.map((error) =>
        i18n.tf(`research.filters.error.${error.code}`, {
          ...error.params,
          position: error.position + 1,
        }),
      ),
);
const planJson = computed(() => (plan.value ? JSON.stringify(plan.value, null, 2) : ""));

watch(
  [plan, () => parsed.value.ok, hasText],
  () => emit("change", { plan: plan.value, valid: parsed.value.ok }),
  { immediate: true },
);

// Authoritative server check: debounced, and a response is applied only while it
// still answers the current collection + plan.
type ServerState = "idle" | "checking" | "ok" | "invalid" | "unavailable";
const serverState = ref<ServerState>("idle");
const serverDiagnostics = ref<{ errors: string[]; warnings: string[] }>({
  errors: [],
  warnings: [],
});
let timer: ReturnType<typeof setTimeout> | undefined;
let latest = 0;

function describe(kind: "server_error" | "warning", item: ResearchFilterDiagnostic) {
  const params = Object.fromEntries(
    Object.entries(item.params || {}).map(([key, value]) => [key, String(value)]),
  );
  return i18n.tf(`research.filters.${kind}.${item.code}`, params);
}

watch(
  [() => JSON.stringify(plan.value), () => props.collection],
  () => {
    clearTimeout(timer);
    latest += 1;
    serverDiagnostics.value = { errors: [], warnings: [] };
    if (!plan.value || !props.collection) {
      serverState.value = "idle";
      return;
    }
    serverState.value = "checking";
    const ticket = latest;
    const body: ResearchFilterPreviewRequest = {
      collection: props.collection,
      metadata_filter: plan.value.metadata_filter,
      document_filter: plan.value.document_filter,
      locales: props.locales,
    };
    timer = setTimeout(async () => {
      try {
        const result = await (props.preview ?? researchFiltersApi.preview)(body);
        if (ticket !== latest) return;
        serverDiagnostics.value = {
          errors: result.errors.map((item) => describe("server_error", item)),
          warnings: result.warnings.map((item) => describe("warning", item)),
        };
        serverState.value = result.valid ? "ok" : "invalid";
      } catch {
        if (ticket !== latest) return;
        serverState.value = "unavailable";
      }
    }, props.debounceMs);
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  clearTimeout(timer);
  latest += 1;
});

function insert(text: string) {
  const current = props.modelValue;
  const partial = /[\p{L}_][\p{L}\p{N}_.-]*$/u.exec(current);
  const base = partial && !/\s$/u.test(current) ? current.slice(0, partial.index) : current;
  const spaced = base && !/\s$/u.test(base) ? `${base} ` : base;
  emit("update:modelValue", `${spaced}${text} `);
}

function clauseOperator(operator: string) {
  return i18n.t(`research.filters.op.${operator.replace(/^\$/u, "")}`, operator);
}
function clauseField(field: string) {
  return field === "document" ? i18n.t("research.filters.field.document", field) : field;
}
function clauseValue(value: unknown) {
  return Array.isArray(value) ? value.join(", ") : String(value);
}
</script>

<template>
  <section class="research-filter-editor" :aria-labelledby="`${inputId}-title`">
    <h3 :id="`${inputId}-title`">{{ i18n.t("research.filters.title") }}</h3>
    <p class="note">{{ i18n.t("research.filters.help") }}</p>
    <label class="research-filter-label" :for="inputId">{{
      i18n.t("research.filters.label")
    }}</label>
    <textarea
      :id="inputId"
      class="research-filter-input"
      rows="2"
      spellcheck="false"
      autocomplete="off"
      :value="modelValue"
      :disabled="disabled"
      :placeholder="i18n.t('research.filters.placeholder')"
      :aria-invalid="!parsed.ok"
      :aria-describedby="`${helpId} ${statusId}`"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    ></textarea>
    <p :id="helpId" class="note">
      {{
        fields.length
          ? i18n.tf("research.filters.syntax_help", { fields: fields.join(", ") })
          : i18n.t("research.filters.no_fields")
      }}
    </p>

    <div v-if="suggestions.length" class="research-filter-suggestions">
      <span>{{ i18n.t("research.filters.suggestions") }}</span>
      <button
        v-for="item in suggestions"
        :key="`${item.kind}:${item.text}`"
        type="button"
        class="btn"
        :aria-label="i18n.tf('research.filters.insert', { text: item.text })"
        @click="insert(item.text)"
      >
        {{ item.text }}
      </button>
    </div>

    <div :id="statusId" class="research-filter-status" role="status" aria-live="polite">
      <p v-if="!hasText">{{ i18n.t("research.filters.status_none") }}</p>
      <template v-else-if="!parsed.ok">
        <p class="research-filter-bad">
          <span aria-hidden="true">✕ </span>{{ i18n.t("research.filters.status_invalid") }}
        </p>
        <ul>
          <li v-for="message in localErrors" :key="message">{{ message }}</li>
        </ul>
      </template>
      <template v-else>
        <p class="research-filter-good">
          <span aria-hidden="true">✓ </span>{{ i18n.t("research.filters.status_valid") }}
        </p>
        <p v-if="serverState === 'checking'">{{ i18n.t("research.filters.status_checking") }}</p>
        <p v-else-if="serverState === 'ok'" class="research-filter-good">
          <span aria-hidden="true">✓ </span>{{ i18n.t("research.filters.status_server_ok") }}
        </p>
        <template v-else-if="serverState === 'invalid'">
          <p class="research-filter-bad">
            <span aria-hidden="true">✕ </span>{{ i18n.t("research.filters.status_server_invalid") }}
          </p>
          <ul>
            <li v-for="message in serverDiagnostics.errors" :key="message">{{ message }}</li>
          </ul>
        </template>
        <p v-else-if="serverState === 'unavailable'">
          <span aria-hidden="true">⚠ </span
          >{{ i18n.t("research.filters.status_server_unavailable") }}
        </p>
        <ul v-if="serverDiagnostics.warnings.length">
          <li v-for="message in serverDiagnostics.warnings" :key="message">
            <span aria-hidden="true">⚠ </span>{{ message }}
          </li>
        </ul>
      </template>
    </div>

    <div v-if="clauses.length" class="research-filter-interpreted">
      <h4>{{ i18n.t("research.filters.interpreted") }}</h4>
      <ul>
        <li v-for="(clause, index) in clauses" :key="index">
          <b>{{ clauseField(clause.field) }}</b>
          {{ clauseOperator(clause.operator) }}
          <code>{{ clauseValue(clause.value) }}</code>
        </li>
      </ul>
    </div>

    <details v-if="plan" class="research-filter-json">
      <summary>{{ i18n.t("research.filters.view_expression") }}</summary>
      <pre tabindex="0">{{ planJson }}</pre>
    </details>
  </section>
</template>

<style scoped>
.research-filter-editor {
  display: grid;
  gap: 8px;
}
.research-filter-editor h3,
.research-filter-editor h4 {
  margin: 0;
  font-size: 0.875rem;
}
.research-filter-label {
  font-size: 0.8125rem;
  font-weight: 700;
}
.research-filter-input {
  width: 100%;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.875rem;
}
.research-filter-suggestions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 0.8125rem;
}
.research-filter-status {
  font-size: 0.8125rem;
}
.research-filter-status p,
.research-filter-status ul,
.research-filter-interpreted ul {
  margin: 0;
}
.research-filter-status ul,
.research-filter-interpreted ul {
  padding-inline-start: 18px;
}
.research-filter-good {
  color: var(--tone-ok-fg);
}
.research-filter-bad {
  color: var(--tone-danger-fg);
  font-weight: 700;
}
.research-filter-json pre {
  margin: 6px 0 0;
  padding: 8px;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-inset);
  font-size: 0.75rem;
}
.research-filter-json pre:focus-visible {
  outline: 2px solid var(--border-interactive);
}
</style>
