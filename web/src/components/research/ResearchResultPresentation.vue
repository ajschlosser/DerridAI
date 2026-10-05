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
import type { ResearchDraftState } from "../../features/research/useResearchDraft";
import ResearchAnswerWorkspace from "./ResearchAnswerWorkspace.vue";
import ResearchEvidencePanel from "./ResearchEvidencePanel.vue";
import type { ResearchEvidenceSelection, ResearchJob, ResearchResult } from "../../types/research";

withDefaults(
  defineProps<{
    job?: ResearchJob | null;
    result?: ResearchResult | null;
    /** A streamed, unverified draft of the running job's answer (see useResearchDraft). */
    draft?: ResearchDraftState | null;
    selectedEvidence?: ResearchEvidenceSelection[];
    activeEvidenceIndex?: number;
    busy?: boolean;
    canGrade?: boolean;
    readOnly?: boolean;
    instanceId?: string;
    instanceLabel?: string;
    canRemoveSelected?: boolean;
    researcher?: boolean;
  }>(),
  {
    job: null,
    result: null,
    draft: null,
    selectedEvidence: () => [],
    activeEvidenceIndex: 0,
    busy: false,
    canGrade: true,
    readOnly: false,
    instanceId: "",
    instanceLabel: "",
    canRemoveSelected: false,
    researcher: false,
  },
);

const emit = defineEmits<{
  copy: [];
  grade: [];
  rerun: [];
  details: [];
  evidence: [index: number];
  selectEvidence: [index: number];
  removeSelected: [key: string];
  clearSelected: [];
  openRecord: [index: number];
  openRelationships: [index: number, mode: "trace" | "model"];
}>();
</script>

<template>
  <div class="research-workspace-grid research-result-presentation">
    <ResearchAnswerWorkspace
      :job="job"
      :result="result"
      :draft="draft"
      :busy="busy"
      :can-grade="canGrade"
      :read-only="readOnly"
      :instance-id="instanceId"
      :context-label="instanceLabel"
      @copy="emit('copy')"
      @grade="emit('grade')"
      @rerun="emit('rerun')"
      @details="emit('details')"
      @evidence="emit('evidence', $event)"
    />
    <ResearchEvidencePanel
      :panel-id="instanceId ? `${instanceId}-evidence` : 'researchEvidencePanel'"
      :context-label="instanceLabel"
      :selected-evidence="selectedEvidence"
      :result-evidence="result?.evidence || []"
      :active-index="activeEvidenceIndex"
      :can-remove="canRemoveSelected"
      :researcher="researcher"
      @select="emit('selectEvidence', $event)"
      @remove="emit('removeSelected', $event)"
      @clear="emit('clearSelected')"
      @open-record="emit('openRecord', $event)"
      @open-relationships="(index, mode) => emit('openRelationships', index, mode)"
    />
  </div>
</template>
