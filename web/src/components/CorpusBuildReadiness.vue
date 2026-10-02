<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed, ref } from "vue";
import UiButton from "./ui/UiButton.vue";
import UiNoticeStack, { type Notice } from "./ui/UiNoticeStack.vue";
import { hasPages } from "../domain/sourceMedia";
import {
  firstBlockingIssue,
  type CorpusSetupIssue,
  type CorpusSetupSectionId,
} from "../features/corpus-builder/domain/setupState";
import { useI18nStore } from "../stores/i18n";

const props = withDefaults(
  defineProps<{
    mediaKind?: string;
    sourceFilename?: string;
    pageCount?: number;
    blockCount?: number;
    structureSummary?: string;
    schemaLabel?: string;
    providerLabel?: string;
    modelLabel?: string;
    enrichmentMode?: "fast" | "deep";
    targetChars?: number;
    toleranceChars?: number;
    contextSafe?: boolean;
    activeBuildCount?: number;
    canStart?: boolean;
    busy?: boolean;
    issues?: CorpusSetupIssue[];
  }>(),
  {
    sourceFilename: "",
    pageCount: 0,
    blockCount: 0,
    structureSummary: "",
    schemaLabel: "",
    providerLabel: "",
    modelLabel: "",
    enrichmentMode: "fast",
    targetChars: 0,
    toleranceChars: 0,
    contextSafe: true,
    activeBuildCount: 0,
    canStart: false,
    busy: false,
    issues: () => [],
  },
);
const emit = defineEmits<{ build: []; editSection: [section: CorpusSetupSectionId] }>();
const i18n = useI18nStore();
// Warnings describe the settings as they are now; closing one hides it until the warning itself changes.
const dismissed = ref(new Set<string>());
const warnings = computed(() =>
  props.issues.filter(
    (issue) => issue.severity === "warning" && !dismissed.value.has(issue.message),
  ),
);
const blockingCount = computed(
  () => props.issues.filter((issue) => issue.severity === "blocking").length,
);
const warningNotices = computed<Notice[]>(() =>
  warnings.value.map((issue) => ({ id: issue.message, tone: "warning", text: issue.message })),
);
const profileBusyWarning = computed(() => warnings.value.some((issue) => issue.id === "profile_busy"));
function dismissWarnings(ids: string[]) {
  dismissed.value = new Set([...dismissed.value, ...ids]);
}
const ready = computed(() => Boolean(props.sourceFilename && props.canStart && props.contextSafe));
const blocking = computed(() => firstBlockingIssue(props.issues));
const statement = computed(() =>
  ready.value
    ? i18n.t("pdf_corpus.readiness.ready")
    : blocking.value?.message || i18n.t("pdf_corpus.readiness.not_ready"),
);
const modeLabel = computed(() =>
  props.enrichmentMode === "deep"
    ? i18n.t("pdf_corpus.enrichment_deep")
    : i18n.t("pdf_corpus.enrichment_fast"),
);
const sizing = computed(() =>
  props.targetChars
    ? i18n.tf("pdf_corpus.readiness.sizing", {
        target: props.targetChars.toLocaleString(),
        tolerance: props.toleranceChars.toLocaleString(),
      })
    : "—",
);
const providerSummary = computed(() =>
  [props.providerLabel || i18n.t("pdf_corpus.provider_default"), props.modelLabel]
    .filter(Boolean)
    .join(" · "),
);
const sourceFacts = computed(() => {
  if (!props.sourceFilename) return "";
  const kind = String(props.mediaKind || "").toLowerCase();
  const media = kind ? i18n.t(`pdf_corpus.setup.media.${kind}`, kind.toUpperCase()) : "";
  const extent =
    hasPages(props.mediaKind) && props.pageCount
      ? i18n.tf("pdf_corpus.setup.summary.pages", { count: props.pageCount })
      : props.blockCount
        ? i18n.tf("pdf_corpus.setup.summary.blocks", { count: props.blockCount })
        : "";
  return [media, extent].filter(Boolean).join(" · ");
});
</script>

<template>
  <section
    class="build-command-bar build-readiness"
    :data-ready="ready ? 'true' : 'false'"
    aria-labelledby="build-readiness-title"
  >
    <header class="build-plan-head">
      <span class="build-plan-eyebrow">{{ i18n.t("pdf_corpus.readiness.build_plan") }}</span>
      <div class="build-command-status">
        <span class="build-command-indicator" aria-hidden="true"></span>
        <h3 id="build-readiness-title" role="status">{{ statement }}</h3>
      </div>
    </header>

    <dl
      class="build-command-summary"
      :aria-label="i18n.t('pdf_corpus.readiness.configuration_summary')"
    >
      <div>
        <dt>{{ i18n.t("pdf_corpus.readiness.source") }}</dt>
        <dd>
          <span>
            {{ sourceFilename || i18n.t("pdf_corpus.choose_source_prompt") }}
            <small v-if="sourceFacts">{{ sourceFacts }}</small>
          </span>
          <button
            type="button"
            class="build-plan-edit"
            :aria-label="
              i18n.tf('pdf_corpus.setup.edit_section', {
                section: i18n.t('pdf_corpus.configure_source'),
              })
            "
            @click="emit('editSection', 'source')"
          >
            {{ i18n.t("pdf_corpus.setup.edit") }}
          </button>
        </dd>
      </div>
      <div v-if="hasPages(mediaKind)">
        <dt>{{ i18n.t("pdf_corpus.readiness.structure") }}</dt>
        <dd>
          <span>
            {{ structureSummary || i18n.t("pdf_corpus.readiness.structure_unset") }}
            <small>{{ i18n.t("pdf_corpus.readiness.record_size") }} · {{ sizing }}</small>
          </span>
          <button
            type="button"
            class="build-plan-edit"
            :aria-label="
              i18n.tf('pdf_corpus.setup.edit_section', {
                section: i18n.t('pdf_corpus.configure_structure'),
              })
            "
            @click="emit('editSection', 'structure')"
          >
            {{ i18n.t("pdf_corpus.setup.edit") }}
          </button>
        </dd>
      </div>
      <div v-if="schemaLabel">
        <dt>{{ i18n.t("pdf_corpus.configure_metadata") }}</dt>
        <dd>
          <span>{{ schemaLabel }}</span>
          <button
            type="button"
            class="build-plan-edit"
            :aria-label="
              i18n.tf('pdf_corpus.setup.edit_section', {
                section: i18n.t('pdf_corpus.configure_metadata'),
              })
            "
            @click="emit('editSection', 'metadata')"
          >
            {{ i18n.t("pdf_corpus.setup.edit") }}
          </button>
        </dd>
      </div>
      <div>
        <dt>{{ i18n.t("pdf_corpus.readiness.enrichment") }}</dt>
        <dd>
          <span>{{ modeLabel }} · {{ providerSummary }}</span>
          <button
            type="button"
            class="build-plan-edit"
            :aria-label="
              i18n.tf('pdf_corpus.setup.edit_section', {
                section: i18n.t('pdf_corpus.configure_enrichment'),
              })
            "
            @click="emit('editSection', 'enrichment')"
          >
            {{ i18n.t("pdf_corpus.setup.edit") }}
          </button>
        </dd>
      </div>
      <div v-if="!hasPages(mediaKind)">
        <dt>{{ i18n.t("pdf_corpus.readiness.record_size") }}</dt>
        <dd>
          <span>{{ sizing }}</span>
          <button
            type="button"
            class="build-plan-edit"
            :aria-label="
              i18n.tf('pdf_corpus.setup.edit_section', {
                section: i18n.t('pdf_corpus.configure_structure'),
              })
            "
            @click="emit('editSection', 'structure')"
          >
            {{ i18n.t("pdf_corpus.setup.edit") }}
          </button>
        </dd>
      </div>
      <div v-if="blockingCount || warnings.length" class="build-command-warning">
        <dt>{{ i18n.t("pdf_corpus.attention_required") }}</dt>
        <dd>
          <span>
            <template v-if="blockingCount">{{
              i18n.tf("pdf_corpus.readiness.blocker_count", { count: blockingCount })
            }}</template>
            <template v-if="blockingCount && warnings.length"> · </template>
            <template v-if="warnings.length">{{
              i18n.tf("pdf_corpus.readiness.note_count", { count: warnings.length })
            }}</template>
          </span>
        </dd>
      </div>
    </dl>

    <div v-if="!contextSafe" class="readiness-alert" role="alert">
      {{ i18n.t("pdf_corpus.context_unsafe") }}
    </div>
    <UiNoticeStack
      v-if="warningNotices.length"
      class="readiness-warnings"
      :items="warningNotices"
      :label="i18n.t('pdf_corpus.readiness_warnings_label')"
      @dismiss="(id) => dismissWarnings([id])"
      @dismiss-all="dismissWarnings"
    />
    <p v-if="activeBuildCount && !profileBusyWarning" class="capacity-note">
      {{ i18n.tf("pdf_corpus.active_build_capacity", { count: activeBuildCount }) }}
    </p>

    <div class="build-command-actions">
      <UiButton
        v-if="blocking"
        variant="primary"
        :label="i18n.t('pdf_corpus.setup.fix')"
        @click="emit('editSection', blocking.section)"
      />
      <UiButton
        :variant="blocking ? 'default' : 'primary'"
        button-class="build-action"
        :disabled="!ready || busy"
        @click="emit('build')"
      >
        {{
          busy
            ? i18n.t("pdf_corpus.starting")
            : i18n.t(
                activeBuildCount ? "pdf_corpus.start_another_build" : "pdf_corpus.build_records",
                activeBuildCount ? "Start another build" : "Build record set",
              )
        }}
      </UiButton>
    </div>
  </section>
</template>

<style scoped>
.build-command-bar {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
  box-shadow: var(--shadow-sm);
}
.build-plan-head {
  display: grid;
  gap: var(--space-2);
}
.build-plan-eyebrow {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.build-command-status {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-3);
  align-items: center;
  min-width: 0;
}
.build-command-indicator {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 999px;
  background: var(--tone-warn-fg);
  box-shadow: 0 0 0 4px var(--tone-warn-bg);
}
.build-command-bar[data-ready="true"] .build-command-indicator {
  background: var(--tone-ok-fg);
  box-shadow: 0 0 0 4px var(--tone-ok-bg);
}
.build-command-status h3 {
  margin: 0;
  font-size: var(--fs-lg, 1.125rem);
  line-height: 1.3;
}
.build-command-summary {
  min-width: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  margin: 0;
  border-block: 1px solid var(--border-subtle);
}
.build-command-summary > div {
  min-width: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 2px;
  padding: var(--space-2) 0;
}
.build-command-summary dd {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: center;
}
.build-command-summary dd > span {
  min-width: 0;
}
.build-command-summary > div + div {
  border-top: 1px solid var(--border-subtle);
}
.build-command-summary dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.build-command-summary dd {
  min-width: 0;
  margin: 0;
  color: var(--text-primary);
  font-size: var(--fs-sm);
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.build-command-summary dd small {
  display: block;
  margin-top: 2px;
  color: var(--text-secondary);
  font-size: var(--fs-xs) !important;
  font-weight: normal;
}
.build-command-summary .build-command-warning dt,
.build-command-summary .build-command-warning dd {
  color: var(--tone-warn-fg);
}
.build-plan-edit {
  min-height: 30px;
  padding: 0 var(--space-2);
  border: 0;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--accent-fg);
  cursor: pointer;
  font: inherit;
  font-size: var(--fs-xs);
  font-weight: var(--fw-semibold);
}
.build-plan-edit:hover {
  background: var(--surface-hover);
}
.build-plan-edit:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.build-command-actions {
  display: grid;
  gap: var(--space-2);
}
.build-command-actions :deep(.ui-button-wrap),
.build-command-actions :deep(.ui-button) {
  width: 100%;
}
.readiness-alert {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--tone-danger-border);
  border-radius: var(--radius-control);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
}
.readiness-warnings {
  margin: 0;
}
.capacity-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.build-command-bar :deep(.build-action) {
  min-height: 2.75rem;
  font-weight: var(--fw-bold);
}
@media (max-width: 1100px) {
  .build-command-bar {
    padding: var(--space-4);
  }
  .build-command-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-2) var(--space-4);
    border-block: 0;
  }
  .build-command-summary > div {
    padding: 0;
  }
  .build-command-summary > div + div {
    border-top: 0;
  }
  .build-command-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .build-command-summary,
  .build-command-actions {
    grid-template-columns: 1fr;
  }
}
</style>
