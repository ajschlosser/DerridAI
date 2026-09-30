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
const warningNotices = computed<Notice[]>(() =>
  warnings.value.map((issue) => ({ id: issue.message, tone: "warning", text: issue.message })),
);
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

    <div
      class="build-command-summary"
      :aria-label="i18n.t('pdf_corpus.readiness.configuration_summary')"
    >
      <span>{{ sourceFilename || i18n.t("pdf_corpus.choose_source_prompt") }}</span>
      <span v-if="schemaLabel">{{ schemaLabel }}</span>
      <span>{{ providerSummary }}</span>
      <span>{{ sizing }}</span>
      <span v-if="warnings.length" class="build-command-warning">
        {{ warnings.length }}
        {{ i18n.t("pdf_corpus.readiness.warnings", "warnings") }}
      </span>
    </div>

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
      <details class="build-command-details">
        <summary>{{ i18n.t("pdf_corpus.readiness.review_setup", "Review setup") }}</summary>
        <div class="build-command-popover">
          <dl>
            <div>
              <dt>{{ i18n.t("pdf_corpus.readiness.source") }}</dt>
              <dd>
                {{ sourceFilename || i18n.t("pdf_corpus.choose_source_prompt") }}
                <small v-if="sourceFilename">
                  <template v-if="hasPages(mediaKind)">
                    {{ pageCount }} {{ i18n.t("pdf_corpus.pages") }} ·
                  </template>
                  {{ blockCount }} {{ i18n.t("pdf_corpus.blocks") }}
                </small>
              </dd>
            </div>
            <div v-if="hasPages(mediaKind)">
              <dt>{{ i18n.t("pdf_corpus.readiness.structure") }}</dt>
              <dd>{{ structureSummary || i18n.t("pdf_corpus.readiness.structure_unset") }}</dd>
            </div>
            <div>
              <dt>{{ i18n.t("pdf_corpus.readiness.enrichment") }}</dt>
              <dd>{{ modeLabel }}</dd>
            </div>
            <div>
              <dt>{{ i18n.t("pdf_corpus.readiness.llm") }}</dt>
              <dd>{{ providerSummary }}</dd>
            </div>
            <div>
              <dt>{{ i18n.t("pdf_corpus.readiness.record_size") }}</dt>
              <dd>{{ sizing }}</dd>
            </div>
          </dl>
          <div v-if="!contextSafe" class="readiness-alert" role="alert">
            {{ i18n.t("pdf_corpus.context_unsafe") }}
          </div>
          <UiNoticeStack
            class="readiness-warnings"
            :items="warningNotices"
            :label="i18n.t('pdf_corpus.readiness_warnings_label')"
            @dismiss="(id) => dismissWarnings([id])"
            @dismiss-all="dismissWarnings"
          />
          <p v-if="activeBuildCount" class="capacity-note">
            {{ i18n.tf("pdf_corpus.active_build_capacity", { count: activeBuildCount }) }}
          </p>
        </div>
      </details>
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
  gap: 0;
  border-block: 1px solid var(--border-subtle);
}
.build-command-summary > span {
  min-width: 0;
  padding: var(--space-2) 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.build-command-summary > span + span {
  border-top: 1px solid var(--border-subtle);
}
.build-command-summary .build-command-warning {
  color: var(--tone-warn-fg);
  font-weight: var(--fw-semibold);
}
.build-command-actions {
  display: grid;
  gap: var(--space-2);
}
.build-command-actions :deep(.ui-button-wrap),
.build-command-actions :deep(.ui-button),
.build-command-details > summary {
  width: 100%;
}
.build-command-details {
  position: relative;
}
.build-command-details > summary {
  min-height: 2.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding-inline: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-card);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  cursor: pointer;
  list-style: none;
}
.build-command-details > summary::-webkit-details-marker {
  display: none;
}
.build-command-details > summary:hover {
  color: var(--text-primary);
}
.build-command-details > summary:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: 1px;
}
.build-command-popover {
  position: absolute;
  z-index: 20;
  inset-inline-end: 0;
  top: calc(100% + var(--space-2));
  width: min(38rem, calc(100vw - var(--space-6)));
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-overlay);
  box-shadow: var(--shadow-overlay);
}
dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}
dl > div {
  min-width: 0;
  display: grid;
  gap: var(--space-1);
}
dt {
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
dd {
  min-width: 0;
  margin: 0;
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  overflow-wrap: anywhere;
}
dd small {
  display: block;
  margin-top: var(--space-1);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-weight: normal;
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
  .build-command-summary > span {
    padding: 0;
  }
  .build-command-summary > span + span {
    border-top: 0;
  }
  .build-command-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .build-command-details {
    grid-column: 1 / -1;
  }
}
@media (max-width: 720px) {
  .build-command-summary,
  .build-command-actions,
  dl {
    grid-template-columns: 1fr;
  }
  .build-command-popover {
    position: static;
    width: auto;
    margin-top: var(--space-2);
  }
}
</style>
