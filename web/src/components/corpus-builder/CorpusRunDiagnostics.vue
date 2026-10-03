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
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed } from "vue";
import type { CorpusBuild } from "../../api/corpus";
import type { ProviderProfile } from "../../api/system";
import CorpusProviderSwitcher from "../CorpusProviderSwitcher.vue";
import CorpusMetadataLiveStatus from "../CorpusMetadataLiveStatus.vue";
import CorpusEnrichmentPassStatus from "../CorpusEnrichmentPassStatus.vue";
import CorpusHandsFreeReport from "../CorpusHandsFreeReport.vue";
import CorpusEnrichmentMetrics from "../CorpusEnrichmentMetrics.vue";
import CorpusTextCleanupSummary from "../CorpusTextCleanupSummary.vue";
import CorpusLlmEffectivenessPanel from "../CorpusLlmEffectivenessPanel.vue";

/** The detailed body of a background run: live status, passes, provider switching and metrics. */
const props = defineProps<{
  build: CorpusBuild;
  profiles: ProviderProfile[];
  activeProfileId?: string;
  activeModel?: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{
  switchProfile: [profileId: string, model: string];
  settle: [];
  cancel: [];
  runAnother: [];
  openRecord: [recordId: string];
  inspectEditorialMemory: [];
}>();
const running = computed(() => ["queued", "running"].includes(String(props.build.status || "")));
const contribution = computed(() => props.build.llm_contribution || {});
</script>

<template>
  <div class="run-diagnostics">
    <CorpusMetadataLiveStatus
      v-if="running && build.stage === 'enriching'"
      :build="build"
      :disabled="disabled"
      @settle="emit('settle')"
      @cancel="emit('cancel')"
    />
    <CorpusEnrichmentPassStatus
      :build="build"
      :disabled="disabled"
      @stop="emit('cancel')"
      @run-another="emit('runAnother')"
    />
    <CorpusHandsFreeReport
      :report="build.autonomous_report"
      @open-record="emit('openRecord', $event)"
    />
    <CorpusProviderSwitcher
      v-if="profiles.length"
      :profiles="profiles"
      :active-profile-id="activeProfileId || ''"
      :active-model="activeModel || ''"
      :history="build.provider_profile_history || []"
      :disabled="disabled || !running"
      @change="(profileId, model) => emit('switchProfile', profileId, model)"
    />
    <CorpusEnrichmentMetrics :build-id="build.build_id" />
    <CorpusTextCleanupSummary v-if="build.text_cleanup" :summary="build.text_cleanup" />
    <CorpusLlmEffectivenessPanel
      v-if="build.llm_contribution"
      :contribution="contribution"
      :family-effectiveness="build.llm_family_effectiveness || {}"
      :confidence-calibration="build.llm_confidence_calibration || {}"
      :model-effectiveness="build.llm_model_effectiveness || {}"
      :editorial-examples-used="Number(build.llm_metrics?.editorial_examples_used || 0)"
      @inspect-editorial-memory="emit('inspectEditorialMemory')"
    />
  </div>
</template>

<style scoped>
.run-diagnostics {
  display: grid;
  gap: var(--space-3);
}
</style>
