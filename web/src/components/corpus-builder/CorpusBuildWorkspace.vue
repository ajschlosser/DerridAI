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
import { useI18nStore } from "../../stores/i18n";
import { openBuildWarnings } from "../../features/corpus-builder/domain/buildWarnings";
import UiButton from "../ui/UiButton.vue";
import UiNoticeStack, { type Notice } from "../ui/UiNoticeStack.vue";
import CorpusBuildActivity from "./CorpusBuildActivity.vue";
import CorpusBuildDiagnostics from "./CorpusBuildDiagnostics.vue";
import CorpusBuildPrimaryStatus from "./CorpusBuildPrimaryStatus.vue";

interface GuidanceItem {
  field: string;
  label: string;
  instructions: string;
  lookFor: string[];
}

const props = defineProps<{
  build: CorpusBuild;
  running: boolean;
  canResume: boolean;
  hasRecordTopology: boolean;
  readyCount?: number;
  enrichingCount?: number;
  preparingCount?: number;
  attentionCount?: number;
  awaitingManifestReview: boolean;
  retryingSegmentation: boolean;
  segmentationNeedsReview: boolean;
  contextSafe: boolean;
  busy?: boolean;
  providerLabel?: string;
  modelLabel?: string;
  runGuidance?: GuidanceItem[];
}>();
const emit = defineEmits<{
  pause: [];
  cancel: [];
  resume: [];
  delete: [];
  openReview: [];
  openPublish: [];
  confirmManifest: [];
  acknowledgeWarnings: [warnings: string[]];
}>();
const i18n = useI18nStore();
const stopped = computed(() =>
  ["failed", "interrupted", "cancelled"].includes(String(props.build.status || "")),
);
// One user-facing representation per warning: the notice stack. Acknowledgement stays in provenance.
const warningNotices = computed<Notice[]>(() =>
  openBuildWarnings(props.build).map((text) => ({ id: text, tone: "warning", text })),
);
// The stopped card already carries the error text, so only a running/blocked build shows it as a notice.
const errorNotices = computed<Notice[]>(() =>
  props.build.error && !stopped.value
    ? [{ id: "build-error", tone: "error", text: String(props.build.error) }]
    : [],
);
</script>

<template>
  <div class="corpus-build-workspace corpus-workspace-surface">
    <CorpusBuildPrimaryStatus
      :build="build"
      :running="running"
      :can-resume="canResume"
      :has-record-topology="hasRecordTopology"
      :ready-count="readyCount"
      :enriching-count="enrichingCount"
      :preparing-count="preparingCount"
      :attention-count="attentionCount"
      :busy="busy"
      :provider-label="providerLabel"
      :model-label="modelLabel"
      @pause="emit('pause')"
      @cancel="emit('cancel')"
      @resume="emit('resume')"
      @delete="emit('delete')"
      @open-review="emit('openReview')"
      @open-publish="emit('openPublish')"
    />
    <UiNoticeStack :items="errorNotices" :label="i18n.t('pdf_corpus.build_error')" />
    <UiNoticeStack
      :items="warningNotices"
      :label="i18n.t('pdf_corpus.build_warnings_label')"
      mode="acknowledge"
      :limit="3"
      :disabled="busy"
      @dismiss="(id) => emit('acknowledgeWarnings', [id])"
      @dismiss-all="(ids) => emit('acknowledgeWarnings', ids)"
    />

    <section
      v-if="awaitingManifestReview"
      class="manifest-gate"
      aria-labelledby="manifest-review-title"
    >
      <div class="manifest-gate-head">
        <div>
          <h3 id="manifest-review-title">
            {{ i18n.t("pdf_corpus.manifest_review_required") }}
          </h3>
          <p>{{ i18n.t("pdf_corpus.manifest_review_required_help") }}</p>
        </div>
        <UiButton
          variant="primary"
          :label="i18n.t('pdf_corpus.confirm_manifest_continue')"
          :disabled="busy || !contextSafe"
          @click="emit('confirmManifest')"
        />
      </div>
      <slot name="manifest"></slot>
    </section>

    <section
      v-if="retryingSegmentation"
      class="build-guidance running-guidance"
      role="status"
      aria-live="polite"
    >
      <h3>{{ i18n.t("pdf_corpus.retry_in_progress") }}</h3>
      <p>{{ i18n.t("pdf_corpus.retry_in_progress_help") }}</p>
    </section>
    <section v-else-if="stopped" class="build-guidance failure-guidance" role="alert">
      <h3>{{ i18n.t("pdf_corpus.build_stopped_title") }}</h3>
      <p>{{ build.error || i18n.t("pdf_corpus.build_stopped_help") }}</p>
      <small>{{ i18n.t("pdf_corpus.build_stopped_checkpoint") }}</small>
    </section>

    <section
      v-if="segmentationNeedsReview"
      class="segmentation-review"
      role="status"
      aria-labelledby="segmentation-review-title"
    >
      <h3 id="segmentation-review-title">{{ i18n.t("pdf_corpus.segmentation_review_title") }}</h3>
      <p>{{ i18n.t("pdf_corpus.segmentation_review_help") }}</p>
      <details v-if="build.segmentation_unresolved_regions?.length">
        <summary>
          {{
            i18n.tf("pdf_corpus.unresolved_count", {
              count: build.segmentation_unresolved_regions.length,
            })
          }}
        </summary>
        <ul>
          <li
            v-for="(region, index) in build.segmentation_unresolved_regions.slice(0, 20)"
            :key="index"
          >
            <code>{{
              region.after_block_id || region.left_block_id || region.start_block_id || "?"
            }}</code>
            →
            <code>{{
              region.next_block_id || region.right_block_id || region.end_block_id || "?"
            }}</code
            ><span v-if="region.reason"> · {{ region.reason }}</span>
          </li>
        </ul>
      </details>
    </section>

    <CorpusBuildDiagnostics
      :build="build"
      :model-label="modelLabel"
      :run-guidance="runGuidance"
      :summary-label="i18n.t('pdf_corpus.run_details', 'Run details')"
      :summary-help="
        i18n.t(
          'pdf_corpus.run_details_help',
          'Activity history, quality checks, model activity, and technical diagnostics.',
        )
      "
    >
      <template #activity>
        <CorpusBuildActivity :build="build" />
      </template>
      <template v-if="!awaitingManifestReview" #manifest>
        <slot name="manifest"></slot>
      </template>
    </CorpusBuildDiagnostics>
  </div>
</template>

<style scoped>
.corpus-build-workspace {
  display: grid;
  gap: var(--space-4);
}
.manifest-gate,
.build-guidance,
.segmentation-review {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.manifest-gate {
  border-color: var(--tone-warn-border);
}
.manifest-gate-head {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  align-items: center;
  justify-content: space-between;
}
.failure-guidance {
  border-color: var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.running-guidance {
  border-color: var(--tone-info-border);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
}
.segmentation-review {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.manifest-gate h3,
.manifest-gate p,
.build-guidance h3,
.build-guidance p,
.segmentation-review h3,
.segmentation-review p {
  margin: 0;
}
</style>
