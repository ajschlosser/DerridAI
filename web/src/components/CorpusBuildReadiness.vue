<script setup lang="ts">
// Copyright 2026 Aaron John Schlosser, PhD.
import { computed } from "vue";
import { hasPages } from "../domain/sourceMedia";
import { useI18nStore } from "../stores/i18n";
import UiButton from "./ui/UiButton.vue";

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
const buildActionLabel = computed(() =>
  props.busy
    ? i18n.t("pdf_corpus.starting")
    : i18n.t(
        props.activeBuildCount ? "pdf_corpus.start_another_build" : "pdf_corpus.build_records",
      ),
);
</script>

<template>
  <section
    class="build-readiness"
    :data-ready="ready ? 'true' : 'false'"
    aria-labelledby="build-readiness-title"
    data-surface="glass"
  >
    <div class="readiness-copy">
      <div class="readiness-heading">
        <span class="eyebrow">{{ i18n.t("pdf_corpus.readiness.eyebrow") }}</span>
        <h3 id="build-readiness-title">
          {{
            ready ? i18n.t("pdf_corpus.readiness.ready") : i18n.t("pdf_corpus.readiness.not_ready")
          }}
        </h3>
      </div>

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
          <dd>
            {{ structureSummary || i18n.t("pdf_corpus.readiness.structure_unset") }}
          </dd>
        </div>
        <div>
          <dt>{{ i18n.t("pdf_corpus.readiness.enrichment") }}</dt>
          <dd>{{ modeLabel }}</dd>
        </div>
        <div>
          <dt>{{ i18n.t("pdf_corpus.readiness.llm") }}</dt>
          <dd>
            {{ providerLabel || i18n.t("pdf_corpus.provider_default") }}
            <small v-if="modelLabel">{{ modelLabel }}</small>
          </dd>
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

    <UiButton
      class="build-action-wrap"
      button-class="build-action"
      variant="primary"
      :label="buildActionLabel"
      :disabled="!ready || busy"
      @click="emit('build')"
    />
  </section>
</template>

<style scoped>
.build-readiness {
  position: sticky;
  bottom: var(--space-3);
  z-index: 12;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-glass);
  box-shadow: var(--shadow-overlay);
  backdrop-filter: blur(10px);
}

.readiness-copy {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
}

.readiness-heading {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.readiness-heading h3 {
  margin: 0;
  font-size: var(--fs-md);
}

.eyebrow,
dt {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  font-weight: var(--fw-bold);
}

dl {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: var(--space-2);
  margin: 0;
}

dl > div {
  min-width: 0;
  display: grid;
  gap: var(--space-1);
  padding-inline-end: var(--space-2);
  border-inline-end: 1px solid var(--border-subtle);
}

dl > div:last-child {
  border-inline-end: 0;
}

dd {
  min-width: 0;
  margin: 0;
  font-size: var(--fs-base);
  font-weight: var(--fw-bold);
  overflow-wrap: anywhere;
}

dd small {
  display: block;
  margin-top: var(--space-1);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  font-weight: var(--fw-medium);
}

.readiness-alert {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--tone-danger-border);
  border-radius: var(--radius-control);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
}

.readiness-warnings {
  margin: 0;
  padding-inline-start: var(--space-5);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: var(--lh-normal);
}

.capacity-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}

.build-action-wrap {
  min-width: 160px;
}

.build-action-wrap :deep(.build-action) {
  width: 100%;
}

@media (max-width: 1100px) {
  .build-readiness {
    position: static;
    grid-template-columns: 1fr;
  }

  dl {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  dl > div {
    border-inline-end: 0;
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: var(--space-2);
  }

  .build-action-wrap {
    width: 100%;
  }
}

@media (max-width: 620px) {
  dl {
    grid-template-columns: 1fr;
  }

  .build-readiness {
    padding: var(--space-3);
  }

  .readiness-heading {
    display: grid;
    gap: var(--space-1);
  }
}

@media (forced-colors: active) {
  .build-readiness {
    border-color: CanvasText;
    box-shadow: none;
  }
}
</style>
