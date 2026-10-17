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

<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../stores/i18n";
import type { CorpusBuild } from "../api/corpus";
import { groupBuildWarnings, currentWarningRecordIds } from "../domain/corpusBuildPresentation";

const props = defineProps<{
  warnings: string[];
  issueSummary?: CorpusBuild["metadata_issue_summary"];
  disabled?: boolean;
}>();
const emit = defineEmits<{
  review: [recordId: string];
  acknowledgeWarnings: [warnings: string[]];
}>();
const i18n = useI18nStore();
const groups = computed(() =>
  groupBuildWarnings(props.warnings).map((group) => ({
    ...group,
    recordIds: currentWarningRecordIds(group.messages, props.issueSummary),
  })),
);
</script>

<template>
  <details v-if="warnings.length" class="warnings build-warnings">
    <summary>
      {{ i18n.tf("pdf_corpus.warnings_count", { count: warnings.length }) }}
      <span>{{ i18n.t("pdf_corpus.warning_details_hint", "Inspect grouped messages") }}</span>
    </summary>
    <div class="warning-groups">
      <button
        type="button"
        class="btn"
        :disabled="disabled"
        @click="emit('acknowledgeWarnings', warnings)"
      >
        {{ i18n.t("ui.acknowledge_all") }}
      </button>
      <p>
        {{
          i18n.t(
            "pdf_corpus.warning_count_help",
            "Warning entries are separate from affected records and failed tasks. Inspect the original messages before acting.",
          )
        }}
      </p>
      <details v-for="group in groups" :key="group.key" class="warning-group">
        <summary>
          <span>{{ group.label }}</span>
          <b>{{ i18n.tf("pdf_corpus.warning_entries", { count: group.messages.length }) }}</b>
        </summary>
        <button
          type="button"
          class="btn"
          :disabled="disabled"
          @click="emit('acknowledgeWarnings', group.messages)"
        >
          {{ i18n.t("pdf_corpus.acknowledge_group") }}
        </button>
        <div v-if="group.recordIds.length" class="warning-records">
          <p>
            {{
              i18n.t(
                "pdf_corpus.warning_current_records",
                "These records also appear in the current metadata issue summary. Historical warnings may describe an earlier failure.",
              )
            }}
          </p>
          <button
            v-for="recordId in group.recordIds"
            :key="recordId"
            type="button"
            class="btn"
            :disabled="disabled"
            @click="emit('review', recordId)"
          >
            {{ i18n.tf("pdf_corpus.warning_review_record", { record: recordId }) }}
          </button>
        </div>
        <ol>
          <li v-for="(message, index) in group.messages" :key="index">{{ message }}</li>
        </ol>
      </details>
    </div>
  </details>
</template>

<style scoped>
.build-warnings {
  border: 1px solid var(--tone-warn-border);
  border-radius: 9px;
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font-size: 0.875rem;
}
summary {
  cursor: pointer;
  padding: 10px 12px;
  overflow-wrap: anywhere;
  font-weight: 700;
}
summary > span:last-child {
  font-weight: 400;
}
.build-warnings > summary > span {
  margin-inline-start: 12px;
}
.warning-groups {
  display: grid;
  gap: 8px;
  padding: 0 12px 12px;
}
.warning-groups > p {
  margin: 0;
  line-height: 1.5;
}
.warning-group {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  color: var(--text-primary);
}
.warning-group summary b {
  margin-inline-start: 10px;
  white-space: nowrap;
  font-size: 0.8125rem;
}
.warning-group ol {
  max-height: 280px;
  overflow: auto;
  margin: 0;
  padding: 0 14px 12px 32px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.warning-group li + li {
  margin-top: 7px;
}
summary:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.warning-records {
  display: grid;
  gap: 8px;
  padding: 0 12px 12px;
}
.warning-records p {
  margin: 0;
  line-height: 1.5;
}
.warning-records button {
  min-height: 44px;
  white-space: normal;
  overflow-wrap: anywhere;
  text-align: start;
}
.warning-records button:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
</style>
