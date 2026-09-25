<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed } from "vue";
import { hasPages } from "../domain/sourceMedia";
import { useI18nStore } from "../stores/i18n";

const props = withDefaults(
  defineProps<{
    mediaKind?: string;
    sourceFilename?: string;
    pageCount?: number;
    blockCount?: number;
    structureSummary?: string;
    providerLabel?: string;
    modelLabel?: string;
    enrichmentMode?: "fast" | "deep";
    targetChars?: number;
    toleranceChars?: number;
    contextSafe?: boolean;
    activeBuildCount?: number;
    canStart?: boolean;
    busy?: boolean;
    warnings?: string[];
  }>(),
  {
    sourceFilename: "",
    pageCount: 0,
    blockCount: 0,
    structureSummary: "",
    providerLabel: "",
    modelLabel: "",
    enrichmentMode: "fast",
    targetChars: 0,
    toleranceChars: 0,
    contextSafe: true,
    activeBuildCount: 0,
    canStart: false,
    busy: false,
    warnings: () => [],
  },
);
const emit = defineEmits<{ build: [] }>();
const i18n = useI18nStore();
const ready = computed(() => Boolean(props.sourceFilename && props.canStart && props.contextSafe));
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
    class="build-command-bar"
    :data-ready="ready ? 'true' : 'false'"
    aria-labelledby="build-readiness-title"
  >
    <div class="build-command-status">
      <span class="build-command-indicator" aria-hidden="true"></span>
      <div>
        <h3 id="build-readiness-title">
          {{
            ready ? i18n.t("pdf_corpus.readiness.ready") : i18n.t("pdf_corpus.readiness.not_ready")
          }}
        </h3>
        <p>
          {{
            sourceFilename ||
            i18n.t("pdf_corpus.choose_source_prompt")
          }}
        </p>
      </div>
    </div>

    <div
      class="build-command-summary"
      :aria-label="i18n.t('pdf_corpus.readiness.configuration_summary')"
    >
      <span>{{ modeLabel }}</span>
      <span>{{ providerSummary }}</span>
      <span>{{ sizing }}</span>
      <span v-if="warnings.length" class="build-command-warning">
        {{ warnings.length }}
        {{ i18n.t("pdf_corpus.readiness.warnings", "warnings") }}
      </span>
    </div>

    <div class="build-command-actions">
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
          <ul
            v-if="warnings.length"
            class="readiness-warnings"
            :aria-label="i18n.t('pdf_corpus.readiness.warnings')"
          >
            <li v-for="warning in warnings" :key="warning">{{ warning }}</li>
          </ul>
          <p v-if="activeBuildCount" class="capacity-note">
            {{ i18n.tf("pdf_corpus.active_build_capacity", { count: activeBuildCount }) }}
          </p>
        </div>
      </details>

      <button
        type="button"
        class="btn primary build-action"
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
      </button>
    </div>
  </section>
</template>

<style scoped>
.build-command-bar {
  position: sticky;
  bottom: var(--space-3);
  z-index: 12;
  display: grid;
  grid-template-columns: minmax(12rem, 1fr) minmax(0, 1.5fr) auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: color-mix(in srgb, var(--surface-card) 94%, transparent);
  box-shadow: var(--shadow-card);
  backdrop-filter: blur(16px);
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
  background: var(--tone-success-fg);
  box-shadow: 0 0 0 4px var(--tone-success-bg);
}
.build-command-status h3,
.build-command-status p {
  margin: 0;
}
.build-command-status h3 {
  font-size: var(--fs-sm);
}
.build-command-status p {
  margin-top: 0.1rem;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.build-command-summary {
  min-width: 0;
  display: flex;
  gap: var(--space-2);
  align-items: center;
  overflow: hidden;
}
.build-command-summary > span {
  min-width: 0;
  padding: 0.28rem 0.55rem;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--surface-subtle);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.build-command-summary .build-command-warning {
  border-color: var(--tone-warn-border);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.build-command-actions {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
.build-command-details {
  position: relative;
}
.build-command-details > summary {
  min-height: 2.5rem;
  display: inline-flex;
  align-items: center;
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
  inset-inline-end: 0;
  bottom: calc(100% + var(--space-2));
  width: min(38rem, calc(100vw - var(--space-6)));
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
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
  padding-inline-start: 1.25rem;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.45;
}
.capacity-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
.build-action {
  min-width: 10rem;
  min-height: 2.6rem;
  font-weight: var(--fw-bold);
}
@media (max-width: 1100px) {
  .build-command-bar {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .build-command-summary {
    grid-column: 1 / -1;
    grid-row: 2;
  }
}
@media (max-width: 720px) {
  .build-command-bar {
    position: static;
    grid-template-columns: 1fr;
  }
  .build-command-summary {
    grid-column: auto;
    grid-row: auto;
    flex-wrap: wrap;
  }
  .build-command-actions {
    display: grid;
    grid-template-columns: 1fr;
  }
  .build-command-details > summary,
  .build-action {
    width: 100%;
    justify-content: center;
  }
  .build-command-popover {
    position: static;
    width: auto;
    margin-top: var(--space-2);
  }
  dl {
    grid-template-columns: 1fr;
  }
}
</style>
