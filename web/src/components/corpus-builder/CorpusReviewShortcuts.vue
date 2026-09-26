<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";

/** The review keyboard shortcuts, in a popover. The keys are the review command vocabulary (reviewCommands.ts). */
const i18n = useI18nStore();
const shortcuts = computed(() => [
  { keys: ["A", "R", "N"], label: i18n.t("pdf_corpus.focus_shortcut_decide") },
  { keys: ["Z", "Shift Z"], label: i18n.t("pdf_corpus.focus_shortcut_history") },
  { keys: ["J", "K"], label: i18n.t("pdf_corpus.focus_shortcut_queue") },
  { keys: ["Alt ←", "Alt →"], label: i18n.t("record.previous_next") },
  { keys: ["M"], label: i18n.t("pdf_corpus.focus_shortcut_metadata") },
  { keys: ["Ctrl/Cmd S"], label: i18n.t("pdf_corpus.save_reviewed_text") },
  { keys: ["Esc"], label: i18n.t("ui.close") },
]);
</script>

<template>
  <details class="review-shortcuts">
    <summary :title="i18n.t('record.keyboard_shortcuts')">
      <AppIcon name="help" /><span class="sr-only">{{ i18n.t("record.keyboard_shortcuts") }}</span>
    </summary>
    <div class="shortcuts-popover">
      <strong>{{ i18n.t("record.keyboard_shortcuts") }}</strong>
      <dl>
        <div v-for="item in shortcuts" :key="item.label">
          <dt>
            <template v-for="key in item.keys" :key="key"
              ><kbd>{{ key }}</kbd></template
            >
          </dt>
          <dd>{{ item.label }}</dd>
        </div>
      </dl>
    </div>
  </details>
</template>

<style scoped>
.review-shortcuts {
  position: relative;
}
.review-shortcuts summary {
  display: grid;
  place-items: center;
  inline-size: 2.5rem;
  block-size: 2.5rem;
  list-style: none;
  border: 1px solid var(--line);
  border-radius: var(--radius-control, 9px);
  background: var(--surface-card, var(--card));
  cursor: pointer;
}
.review-shortcuts summary::-webkit-details-marker {
  display: none;
}
.review-shortcuts summary svg {
  inline-size: 1.125rem;
  block-size: 1.125rem;
}
.shortcuts-popover {
  position: absolute;
  inset-inline-end: 0;
  inset-block-start: calc(100% + 0.5rem);
  z-index: 20;
  inline-size: min(22rem, 90vw);
  display: grid;
  gap: 0.5rem;
  padding: 0.875rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-overlay, 12px);
  background: var(--surface-overlay, var(--card));
  box-shadow: var(--shadow-overlay);
  font-size: 0.8125rem;
}
.shortcuts-popover dl {
  display: grid;
  gap: 0.375rem;
  margin: 0;
}
.shortcuts-popover dl > div {
  display: grid;
  grid-template-columns: 8rem 1fr;
  gap: 0.75rem;
  align-items: baseline;
}
.shortcuts-popover dt {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
.shortcuts-popover dd {
  margin: 0;
  color: var(--muted);
}
kbd {
  padding: 0 0.3rem;
  border: 1px solid color-mix(in srgb, currentColor 35%, transparent);
  border-radius: 4px;
  font: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.4;
}
</style>
