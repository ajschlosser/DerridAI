<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import type { CorpusCapture, SourceProviderId } from "../../api/corpus";
import { useI18nStore } from "../../stores/i18n";
import { languageName } from "../../domain/languages";
import { enumLabel, enumTone } from "../../domain/sourceLabels";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

/** Live discovery/acquisition progress for one capture, per library (and Wikisource project). */
const props = defineProps<{ capture: CorpusCapture; mode: "discovering" | "acquiring" }>();
const i18n = useI18nStore();
const t = (key: string, fallback?: string) => i18n.t(key, fallback);

const job = computed(() => props.capture.active_job);
const phase = computed(() => job.value?.stage || props.capture.phase);
const done = computed(() => Number(job.value?.completed ?? props.capture.progress?.done ?? 0));
const total = computed(() => Number(job.value?.total ?? props.capture.progress?.total ?? 0));
const finished = computed(() =>
  ["complete", "completed", "partial", "failed", "cancelled", "canceled"].includes(
    String(props.capture.status || ""),
  ),
);
const progressValue = computed(() =>
  total.value ? Math.min(total.value, Math.max(0, done.value)) : finished.value ? 1 : undefined,
);
const detail = computed(
  () =>
    job.value?.stage_detail ||
    props.capture.progress?.current ||
    props.capture.progress?.project ||
    "",
);
const detailLabel = computed(() => {
  const value = String(detail.value || "");
  if (!value) return "";
  // Wikisource discovery reports the project code; show it as a language name.
  return phase.value === "discovering_wikisource" && /^[a-z]{2,3}(-[a-z]+)?$/.test(value)
    ? i18n.tf("sources.project", { project: languageName(value, i18n.locale) })
    : value;
});

type ProviderState = "done" | "running" | "waiting" | "failed";
const providers = computed(() =>
  (props.capture.options.providers || []).map((provider: SourceProviderId) => {
    const snapshot = props.capture.provider_snapshots.find((item) => item.provider === provider);
    const failed = props.capture.errors.some((item) => item.provider === provider);
    let state: ProviderState = "waiting";
    if (failed) state = "failed";
    else if (snapshot && !job.value) state = "done";
    else if (phase.value === `discovering_${provider}`) state = "running";
    else if (snapshot) state = "done";
    return { provider, state, snapshot };
  }),
);
const tone = { done: "success", running: "info", waiting: "neutral", failed: "danger" } as const;
</script>

<template>
  <div class="capture-progress">
    <p class="cp-phase" role="status" aria-live="polite">
      <strong>{{ enumLabel(t, "phase", phase) }}</strong>
      <span v-if="detailLabel"> · {{ detailLabel }}</span>
      <span v-if="total">
        ·
        {{
          i18n.tf("capture.progress_count", {
            done: done.toLocaleString(i18n.locale),
            total: total.toLocaleString(i18n.locale),
          })
        }}</span
      >
    </p>
    <progress
      class="cp-bar"
      :value="progressValue"
      :max="total || 1"
      :aria-label="i18n.t('capture.progress_label')"
    />
    <ul v-if="mode === 'discovering'" class="cp-providers">
      <li v-for="item in providers" :key="item.provider" :data-provider="item.provider">
        <strong>{{ enumLabel(t, "provider", item.provider) }}</strong>
        <UiStatusBadge
          :label="i18n.t(`capture.provider_state.${item.state}`)"
          :tone="tone[item.state]"
        />
        <small v-if="item.snapshot">
          {{
            i18n.tf("capture.snapshot_found", {
              count: item.snapshot.result_count,
              projects: item.snapshot.projects_searched.length,
            })
          }}
        </small>
      </li>
    </ul>
    <ul v-if="capture.errors.length" class="cp-errors" role="alert">
      <li v-for="(error, index) in capture.errors" :key="index">
        <UiStatusBadge
          :label="enumLabel(t, 'error', error.code)"
          :tone="enumTone('capture_status', 'failed')"
        />
        <span
          >{{ error.provider ? `${enumLabel(t, "provider", error.provider)}: ` : ""
          }}{{ error.message }}</span
        >
      </li>
    </ul>
    <p class="cp-note">{{ i18n.t("capture.background_note") }}</p>
  </div>
</template>

<style scoped>
.capture-progress {
  display: grid;
  gap: 12px;
}
.cp-phase {
  margin: 0;
}
.cp-bar {
  width: 100%;
  height: 10px;
  accent-color: var(--accent-fg);
}
.cp-providers,
.cp-errors {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.cp-providers li,
.cp-errors li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.cp-providers small,
.cp-note {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.cp-note {
  margin: 0;
}
</style>
