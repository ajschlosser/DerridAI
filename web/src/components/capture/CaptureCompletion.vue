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
import type { CaptureCandidate, CorpusCapture } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { acquisitionOutcome } from "../../domain/captureReview";
import { enumLabel, enumTone } from "../../domain/sourceLabels";
import AppIcon from "../AppIcon.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

/** What an acquisition registered and what failed, with the ways forward. Nothing is built here. */
const props = withDefaults(
  defineProps<{ capture: CorpusCapture; candidates: CaptureCandidate[]; busy?: boolean }>(),
  { busy: false },
);
const emit = defineEmits<{ viewSources: []; retry: []; useInBuilder: [sourceIds: string[]] }>();
const i18n = useI18nStore();
const t = (key: string, fallback?: string) => i18n.t(key, fallback);
const outcome = computed(() => acquisitionOutcome(props.candidates));
const failures = computed(() =>
  props.candidates.filter((item) => item.acquisition_status === "failed"),
);
</script>

<template>
  <div class="capture-completion">
    <p class="cc-status" role="status">
      <UiStatusBadge
        :label="enumLabel(t, 'capture_status', capture.status)"
        :tone="enumTone('capture_status', capture.status)"
      />
      <span>{{
        i18n.tf("capture.done.summary", {
          registered: outcome.registered,
          failed: outcome.failed,
        })
      }}</span>
    </p>
    <ul v-if="failures.length" class="cc-failures" :aria-label="i18n.t('capture.done.failures')">
      <li v-for="item in failures" :key="item.candidate_id" :data-candidate="item.candidate_id">
        <AppIcon name="warning" />
        <span
          ><strong>{{ item.title }}</strong> —
          {{
            item.error ? `${enumLabel(t, "error", item.error.code)}: ${item.error.message}` : ""
          }}</span
        >
      </li>
    </ul>
    <p class="cc-note">{{ i18n.t("capture.done.no_build_note") }}</p>
    <div class="cc-actions">
      <button type="button" class="btn" data-action="view-sources" @click="emit('viewSources')">
        {{ i18n.t("capture.done.view_sources") }}
      </button>
      <button
        v-if="outcome.failed"
        type="button"
        class="btn"
        data-action="retry"
        :disabled="busy"
        @click="emit('retry')"
      >
        <AppIcon name="refresh" />{{
          i18n.tf("capture.done.retry_failed", { count: outcome.failed })
        }}
      </button>
      <button
        type="button"
        class="btn primary"
        data-action="use-in-builder"
        :disabled="!outcome.registeredSourceIds.length"
        @click="emit('useInBuilder', outcome.registeredSourceIds)"
      >
        {{ i18n.t("capture.done.use_in_builder") }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.capture-completion {
  display: grid;
  gap: 12px;
}
.cc-status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0;
}
.cc-failures {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.cc-failures li {
  display: flex;
  gap: 6px;
  color: var(--tone-danger-fg);
  font-size: var(--fs-sm);
}
.cc-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.cc-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
