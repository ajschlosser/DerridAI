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
import { onBeforeUnmount, onMounted, ref } from "vue";
import type { useSplitter } from "../../composables/useSplitter";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";

type Splitter = ReturnType<typeof useSplitter>;
export interface CorpusFixContext {
  code: string;
  label: string;
  recordId: string;
  field: string;
  reason: string;
}

/**
 * Visual composition of the Review workspace: fix banner, the frame that fills the window under the top
 * bar, the queue | record | inspector grid with its splitters, and the decision dock. The parent keeps every
 * mutation and passes the panes in as slots, so review behaviour is unchanged.
 */
const props = defineProps<{
  queueSplitter: Splitter;
  inspectorSplitter: Splitter;
  heightSplitter: Splitter;
  queueCollapsed: boolean;
  /** "record" is the split view; "metadata" and "source" are full-width detail layouts. */
  mode: "record" | "metadata" | "source";
  loading: boolean;
  fixContext: CorpusFixContext | null;
  fixProgress: { position: number; total: number; remaining: number } | null;
}>();
const emit = defineEmits<{
  fixNext: [];
  backToReadiness: [];
  gridChange: [element: HTMLElement | null];
  frameChange: [element: HTMLElement | null];
}>();
const i18n = useI18nStore();
const gridEl = ref<HTMLElement | null>(null);
const frameEl = ref<HTMLElement | null>(null);
onMounted(() => {
  emit("gridChange", gridEl.value);
  emit("frameChange", frameEl.value);
});
onBeforeUnmount(() => {
  emit("gridChange", null);
  emit("frameChange", null);
});
</script>

<template>
  <div class="corpus-review-workspace">
    <div v-if="fixContext" class="fix-banner" role="status" aria-live="polite">
      <div class="fix-banner-copy">
        <span class="fix-banner-eyebrow">{{
          i18n.t("pdf_corpus.remediation_from_readiness", "From Publish readiness")
        }}</span>
        <span class="fix-banner-title-row">
          <b>{{ fixContext.label }}</b>
          <span v-if="fixProgress" class="fix-banner-progress">{{
            i18n.tf("pdf_corpus.fixing_progress", {
              position: fixProgress.position,
              total: fixProgress.total,
            })
          }}</span>
        </span>
        <span v-if="fixContext.reason" class="fix-banner-detail">{{ fixContext.reason }}</span>
        <code v-if="fixContext.field || fixContext.recordId">{{
          fixContext.field || fixContext.recordId
        }}</code>
      </div>
      <span class="fix-banner-actions">
        <UiButton
          v-if="!fixProgress || fixProgress.remaining > 1"
          size="small"
          :label="i18n.t('pdf_corpus.fix_next_issue')"
          @click="emit('fixNext')"
        />
        <UiButton
          size="small"
          variant="primary"
          :label="i18n.t('pdf_corpus.back_to_readiness')"
          @click="emit('backToReadiness')"
        />
      </span>
    </div>

    <slot name="panels"></slot>

    <div ref="frameEl" class="review-frame">
      <div class="review-frame-head">
        <slot name="header"></slot>
      </div>
      <section
        ref="gridEl"
        class="review-grid record-first-review"
        :style="{
          '--rw-queue': `${props.queueSplitter.size.value}px`,
          '--rw-inspector': `${props.inspectorSplitter.size.value}px`,
          '--rw-height': `${props.heightSplitter.size.value}px`,
        }"
        :class="{
          'queue-collapsed': queueCollapsed,
          'detail-mode': mode !== 'record',
          'metadata-workspace': mode === 'metadata',
          'source-workspace': mode === 'source',
        }"
        :aria-busy="loading"
      >
        <slot name="queue"></slot>
        <div
          v-if="!queueCollapsed"
          class="review-splitter"
          data-splitter="queue"
          role="separator"
          tabindex="0"
          aria-orientation="vertical"
          :aria-label="i18n.t('pdf_corpus.resize_queue')"
          v-bind="props.queueSplitter.aria()"
          @pointerdown="props.queueSplitter.onPointerDown"
          @keydown="props.queueSplitter.onKeydown"
          @dblclick="props.queueSplitter.reset"
        ></div>

        <slot name="record"></slot>

        <div
          v-if="mode === 'record'"
          class="review-splitter"
          data-splitter="inspector"
          role="separator"
          tabindex="0"
          aria-orientation="vertical"
          :aria-label="i18n.t('pdf_corpus.resize_inspector')"
          v-bind="props.inspectorSplitter.aria()"
          @pointerdown="props.inspectorSplitter.onPointerDown"
          @keydown="props.inspectorSplitter.onKeydown"
          @dblclick="props.inspectorSplitter.reset"
        ></div>

        <slot name="inspector"></slot>
        <slot name="dock"></slot>
      </section>
      <div
        class="review-height-splitter"
        data-splitter="review-height"
        role="separator"
        tabindex="0"
        aria-orientation="horizontal"
        :aria-label="i18n.t('pdf_corpus.resize_review_height')"
        v-bind="props.heightSplitter.aria()"
        @pointerdown="props.heightSplitter.onPointerDown"
        @keydown="props.heightSplitter.onKeydown"
        @dblclick="props.heightSplitter.reset"
      ></div>
    </div>
  </div>
</template>

<style scoped>
.corpus-review-workspace {
  display: grid;
  gap: var(--space-3);
  min-width: 0;
  overflow: clip;
}
/* The frame owns the sticky layout: children inside it stay in normal flow. */
.review-frame {
  display: flex;
  flex-direction: column;
  min-width: 0;
  scroll-margin-top: var(--ref-topbar, 60px);
}
.review-frame-head {
  flex: 0 0 auto;
  min-width: 0;
}
.review-grid.record-first-review {
  position: relative;
  display: grid;
  overflow: hidden;
  flex: 1 1 auto;
  min-height: 0;
  height: var(--rw-height, 680px);
  grid-template-rows: minmax(0, 1fr);
  grid-template-columns: var(--rw-queue, 18rem) 0.5rem minmax(0, 1fr) 0.5rem var(
      --rw-inspector,
      25rem
    );
  border: 1px solid var(--border-subtle);
  border-radius: 0 0 var(--radius-card) var(--radius-card);
  background: var(--surface-card);
}
.review-grid.queue-collapsed {
  grid-template-columns: minmax(0, 1fr) 0.5rem var(--rw-inspector, 25rem);
}
.review-grid.detail-mode {
  grid-template-columns: var(--rw-queue, 18rem) 0.5rem minmax(0, 1fr);
}
.review-grid.detail-mode.queue-collapsed {
  grid-template-columns: minmax(0, 1fr);
}
/* Each pane is its own positioned scroll box. An unpositioned pane let the queue's visually-hidden
   labels escape its clipping and stretch the whole page by several thousand pixels. Scrolling passes to
   the page at the edge of a pane, since the frame fills the window. */
.review-frame :slotted(.records-pane),
.review-frame :slotted(.record-review-pane),
.review-frame :slotted(.review-inspector) {
  position: relative;
  height: 100%;
  min-height: 0;
  max-height: none;
  overflow: auto;
  overscroll-behavior: auto;
}
.review-frame :slotted(.record-review-pane) {
  display: flex;
  flex-direction: column;
}
.review-grid.queue-collapsed :slotted(.records-pane) {
  display: none;
}
/* The header and the panes read as one contiguous surface. */
.review-frame-head :deep(.review-header) {
  border-bottom: 0;
  border-radius: var(--radius-card) var(--radius-card) 0 0;
}
.review-splitter {
  position: relative;
  cursor: col-resize;
  touch-action: none;
  background: var(--surface-card);
  border-inline: 1px solid var(--border-subtle);
}
.review-splitter::before {
  content: "";
  position: absolute;
  inset-block: 0;
  inset-inline: -0.5rem;
}
.review-splitter::after {
  content: "";
  position: absolute;
  inset-block: calc(50% - 1.5rem);
  inset-inline: 0.1875rem;
  border-radius: 2px;
  background: var(--border-strong);
}
.review-splitter:hover::after,
.review-splitter:focus-visible::after {
  background: var(--ui-accent);
}
.review-splitter:focus-visible,
.review-height-splitter:focus-visible {
  outline: 3px solid var(--ui-accent-focus);
  outline-offset: -2px;
}
.review-height-splitter {
  position: relative;
  z-index: 2;
  height: 0.5rem;
  cursor: row-resize;
  touch-action: none;
  background: var(--surface-card);
  border-block: 1px solid var(--border-subtle);
}
.review-height-splitter::before {
  content: "";
  position: absolute;
  inset-block: -0.5rem;
  inset-inline: 0;
}
.review-height-splitter::after {
  content: "";
  position: absolute;
  inset-block: 0.1875rem;
  inset-inline: calc(50% - 1.5rem);
  border-radius: 2px;
  background: var(--border-strong);
}
.review-height-splitter:hover::after,
.review-height-splitter:focus-visible::after {
  background: var(--ui-accent);
}
:global(body.splitter-dragging) {
  cursor: col-resize;
  user-select: none;
}
:global(body.splitter-dragging-vertical) {
  cursor: row-resize;
}
.fix-banner {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--tone-info-border);
  border-inline-start: 4px solid var(--tone-info-fg);
  border-radius: var(--radius-control);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
  font-size: var(--fs-sm);
}
.fix-banner-copy {
  min-width: 0;
  display: grid;
  gap: 2px;
}
.fix-banner-eyebrow {
  font-size: var(--fs-xs);
  font-weight: var(--fw-bold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  opacity: 0.85;
}
.fix-banner-title-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}
.fix-banner-title-row b {
  font-size: var(--fs-md);
}
.fix-banner-detail {
  max-width: 72ch;
  line-height: 1.45;
}
.fix-banner-copy code {
  width: fit-content;
  max-width: 100%;
  overflow-wrap: anywhere;
}
.fix-banner-actions {
  display: inline-flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.fix-banner-progress {
  font-weight: var(--fw-semibold);
}
/* Wide and medium screens: the frame fills the screen under the top bar. */
@media (min-width: 800px) and (min-height: 34rem) {
  .review-frame {
    position: sticky;
    top: var(--ref-topbar, 60px);
    max-height: calc(100dvh - var(--ref-topbar, 60px) - 0.75rem);
    min-height: 0;
  }
}
/* Medium (a laptop): the queue and the record side by side, the inspector as a full-width pane below. */
@media (min-width: 800px) and (max-width: 1279.98px) and (min-height: 34rem) {
  .review-grid.record-first-review {
    grid-template-columns: var(--rw-queue, 16rem) 0.5rem minmax(0, 1fr);
    grid-template-rows: minmax(0, 1.9fr) minmax(0, 1fr);
  }
  .review-grid.queue-collapsed {
    grid-template-columns: minmax(0, 1fr);
  }
  .review-grid .review-splitter[data-splitter="inspector"] {
    display: none;
  }
  .review-frame :slotted(.review-inspector) {
    grid-column: 1/-1;
    border-inline-start: 0;
    border-top: 1px solid var(--border-subtle);
  }
  .review-grid.detail-mode {
    grid-template-columns: var(--rw-queue, 16rem) 0.5rem minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
  }
  .review-grid.detail-mode :slotted(.records-pane) {
    grid-row: 1;
  }
  .review-grid.detail-mode :slotted(.review-inspector) {
    grid-column: 3;
    grid-row: 1;
    border-top: 0;
  }
  .review-grid.detail-mode.queue-collapsed {
    grid-template-columns: minmax(0, 1fr);
  }
  .review-grid.detail-mode.queue-collapsed :slotted(.review-inspector) {
    grid-column: 1;
  }
}
/* Phones and very short windows: an ordinary page, panes at their natural height. */
@media (max-width: 799.98px), (max-height: 33.99rem) {
  .review-splitter {
    display: none;
  }
  .review-height-splitter {
    display: none;
  }
  .review-grid.record-first-review,
  .review-grid.queue-collapsed,
  .review-grid.detail-mode,
  .review-grid.detail-mode.queue-collapsed {
    overflow: visible;
    height: auto;
    grid-template-rows: auto;
    grid-template-columns: minmax(0, 1fr);
  }
  .review-frame :slotted(.records-pane) {
    max-height: 18rem;
    height: auto;
  }
  .review-frame :slotted(.record-review-pane),
  .review-frame :slotted(.review-inspector) {
    height: auto;
    overflow: visible;
  }
}
</style>
