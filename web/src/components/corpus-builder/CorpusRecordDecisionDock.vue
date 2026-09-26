<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { ref } from "vue";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import CorpusActionMenu, { type CorpusActionMenuItem } from "../CorpusActionMenu.vue";

/**
 * The record decision dock, shared by the review workspace and Focus View so both decide a record the same way: what
 * still blocks it, history, secondary actions, and skip / reject / accept, always in the same place.
 */
const props = withDefaults(
  defineProps<{
    accepted?: boolean;
    editing?: boolean;
    /** Anything in flight: every action waits. */
    busy?: boolean;
    /** The review is still being prepared: only accept waits. */
    locked?: boolean;
    saving?: boolean;
    saveDisabled?: boolean;
    blockingCount?: number;
    blockingLabel?: string;
    actionItems?: CorpusActionMenuItem[];
    /** Distinguishes the id when two docks are mounted at once (the workspace sits under Focus View). */
    blockerId?: string;
  }>(),
  {
    accepted: false,
    editing: false,
    busy: false,
    locked: false,
    saving: false,
    saveDisabled: false,
    blockingCount: 0,
    blockingLabel: "",
    actionItems: () => [],
    blockerId: "record-metadata-blocker",
  },
);
const emit = defineEmits<{
  focusBlocker: [];
  undo: [];
  redo: [];
  action: [id: string];
  skip: [];
  reject: [];
  accept: [];
  cancelEdit: [];
  saveText: [];
}>();
const i18n = useI18nStore();
const acceptButton = ref<HTMLButtonElement | null>(null);
defineExpose({ focusAccept: () => acceptButton.value?.focus({ preventScroll: true }) });
</script>

<template>
  <footer class="record-decision-dock">
    <div
      v-if="props.editing"
      class="decision-bar text-edit-bar"
      role="group"
      :aria-label="i18n.t('pdf_corpus.edit_text')"
    >
      <span class="text-save-hint">{{ i18n.t("pdf_corpus.text_save_hint") }}</span>
      <div class="decision-actions">
        <button type="button" class="btn small" @click="emit('cancelEdit')">
          {{ i18n.t("ui.cancel") }}
        </button>
        <button
          type="button"
          class="btn small primary"
          :disabled="props.busy || props.saveDisabled"
          @click="emit('saveText')"
        >
          {{ props.saving ? i18n.t("ui.saving") : i18n.t("pdf_corpus.save_and_mark_reviewed") }}
        </button>
      </div>
    </div>
    <div
      v-else
      class="decision-bar"
      role="group"
      :aria-label="i18n.t('pdf_corpus.record_decision')"
    >
      <div class="dock-status">
        <button
          v-if="props.blockingCount"
          :id="props.blockerId"
          type="button"
          class="dock-blocker"
          aria-keyshortcuts="M"
          :title="
            i18n.tf('pdf_corpus.resolve_metadata_before_accept_fields', {
              fields: props.blockingLabel,
            })
          "
          @click="emit('focusBlocker')"
        >
          <AppIcon name="warning" /><b class="dock-blocker-count">{{
            i18n.tf("pdf_corpus.metadata_decisions_count", { count: props.blockingCount })
          }}</b
          ><b class="dock-blocker-short"
            ><span aria-hidden="true">{{ props.blockingCount }}</span
            ><span class="sr-only">{{
              i18n.tf("pdf_corpus.metadata_decisions_count", { count: props.blockingCount })
            }}</span></b
          ><span class="dock-blocker-text">{{ props.blockingLabel }}</span
          ><kbd aria-hidden="true">{{ i18n.t("pdf_corpus.shortcut.metadata") }}</kbd>
        </button>
        <span v-else class="dock-ready" role="status"
          ><AppIcon name="check" />{{
            props.accepted
              ? i18n.t("pdf_corpus.dock_record_accepted")
              : i18n.t("pdf_corpus.dock_metadata_complete")
          }}</span
        >
      </div>
      <div class="decision-history" role="group" :aria-label="i18n.t('pdf_corpus.record_history')">
        <button
          type="button"
          class="btn small icon-only"
          :title="i18n.t('pdf_corpus.undo')"
          aria-keyshortcuts="Z"
          :disabled="props.busy"
          @click="emit('undo')"
        >
          <AppIcon name="history" /><span class="sr-only">{{
            i18n.t("pdf_corpus.undo")
          }}</span></button
        ><button
          type="button"
          class="btn small icon-only"
          :title="i18n.t('pdf_corpus.redo')"
          aria-keyshortcuts="Shift+Z"
          :disabled="props.busy"
          @click="emit('redo')"
        >
          <AppIcon name="history" class="flip-inline" /><span class="sr-only">{{
            i18n.t("pdf_corpus.redo")
          }}</span>
        </button>
      </div>
      <CorpusActionMenu
        :label="i18n.t('pdf_corpus.more_actions')"
        :menu-label="i18n.t('pdf_corpus.more_record_actions')"
        :items="props.actionItems"
        :disabled="props.busy"
        placement="top"
        @select="emit('action', $event)"
      />
      <div class="decision-actions">
        <button type="button" class="btn small" :disabled="props.busy" @click="emit('skip')">
          {{ i18n.t("pdf_corpus.skip") }}
        </button>
        <button
          type="button"
          class="btn small danger"
          aria-keyshortcuts="R"
          :disabled="props.busy"
          @click="emit('reject')"
        >
          {{ i18n.t("pdf_corpus.reject_next")
          }}<kbd aria-hidden="true">{{ i18n.t("pdf_corpus.shortcut.reject") }}</kbd>
        </button>
        <button
          ref="acceptButton"
          type="button"
          class="btn small primary"
          aria-keyshortcuts="A"
          :disabled="props.busy || props.locked"
          :aria-describedby="props.blockingCount ? props.blockerId : undefined"
          @click="emit('accept')"
        >
          {{ props.accepted ? i18n.t("pdf_corpus.reopen") : i18n.t("pdf_corpus.accept_next")
          }}<kbd v-if="!props.accepted" aria-hidden="true">{{
            i18n.t("pdf_corpus.shortcut.accept")
          }}</kbd>
        </button>
      </div>
    </div>
  </footer>
</template>

<style scoped>
/* The decision dock: one row across the bottom of the workspace, always in the same place, primary action last and
   directly under the inspector where adjudication ends. */
.record-decision-dock {
  grid-column: 1 / -1;
  container: dock / inline-size;
  z-index: 8;
  border-top: 1px solid var(--line);
  background: var(--surface-overlay, var(--card));
  padding-bottom: env(safe-area-inset-bottom);
}
.record-decision-dock .text-edit-bar .text-save-hint {
  flex: 1 1 14rem;
  font-size: 0.8125rem;
  color: var(--muted);
}
.record-decision-dock .decision-bar {
  position: static;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.5rem;
  min-height: 0;
  padding: 0.5rem 0.75rem;
  border-top: 0;
  background: transparent;
  backdrop-filter: none;
}
.dock-status {
  display: flex;
  flex: 1 1 auto;
  min-width: 0;
}
.dock-blocker,
.dock-ready {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  max-width: 100%;
  min-height: 2.25rem;
  padding: 0 0.75rem;
  border-radius: var(--radius-control);
  font-size: 0.8125rem;
  font-weight: 700;
}
.dock-blocker {
  overflow: hidden;
  border: 1px solid var(--tone-warn-edge);
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
}
.dock-blocker:hover {
  border-color: var(--tone-warn-border);
}
.dock-blocker:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
.dock-blocker-count,
.dock-blocker-short {
  flex: none;
  white-space: nowrap;
}
.dock-blocker-short {
  display: none;
}
.dock-blocker-text {
  font-weight: 500;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dock-ready {
  color: var(--tone-ok-fg);
}
.dock-blocker svg,
.dock-ready svg {
  flex: none;
  inline-size: 1rem;
  block-size: 1rem;
}
.record-decision-dock kbd {
  margin-inline-start: 0.5rem;
  padding: 0 0.3rem;
  border: 1px solid color-mix(in srgb, currentColor 35%, transparent);
  border-radius: 4px;
  font: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.35;
  opacity: 0.85;
}
.decision-history,
.decision-actions {
  display: flex;
  flex: none;
  align-items: center;
  gap: 0.5rem;
}
.decision-history .btn.icon-only {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-inline-size: 2.25rem;
  padding-inline: 0.5rem;
}
.decision-history .btn svg {
  inline-size: 1rem;
  block-size: 1rem;
}
.decision-actions .btn {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}
.flip-inline {
  transform: scaleX(-1);
}
.decision-bar .btn {
  min-height: 2.5rem;
  font-size: 0.8125rem;
}
.decision-actions .primary {
  min-width: 8.25rem;
  font-weight: 800;
}
/* A narrower dock drops the key hints first, then More actions shrinks to its dots, so it stays on one row. */
@container dock (max-width: 56rem) {
  .record-decision-dock .decision-actions kbd,
  .dock-blocker kbd,
  .dock-blocker-text,
  .dock-blocker-count {
    display: none;
  }
  .dock-blocker-short {
    display: inline;
  }
}
@container dock (max-width: 44rem) {
  .record-decision-dock :deep(.action-menu-label),
  .record-decision-dock :deep(.action-menu-caret) {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }
  .record-decision-dock :deep(.action-menu-dots) {
    display: inline-block;
  }
  .record-decision-dock :deep(.action-menu-trigger) {
    min-inline-size: 2.25rem;
    justify-content: center;
  }
}
@container dock (max-width: 30rem) {
  .record-decision-dock .decision-bar {
    flex-wrap: wrap;
  }
  .dock-status {
    flex-basis: 100%;
  }
  .decision-actions {
    flex: 1 1 100%;
  }
  .decision-actions .btn {
    flex: 1 1 0;
    justify-content: center;
  }
}
/* Phones: the page scrolls, so the dock stays pinned to the bottom of the window. */
@media (max-width: 799.98px), (max-height: 33.99rem) {
  .record-decision-dock {
    position: sticky;
    inset-block-end: 0;
    box-shadow: 0 -0.75rem 2rem color-mix(in srgb, var(--text) 12%, transparent);
  }
}
</style>
