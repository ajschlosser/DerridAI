<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import UiTooltip from "./UiTooltip.vue";

/**
 * Messages that can be closed: each has its own ×, and a stack of several also has one for all of them.
 *
 * `mode="acknowledge"` is for warnings that are part of a corpus's provenance. Closing one does not delete it; the
 * parent records who acknowledged it and when, and the warning is published with the corpus. The × says so.
 */
export interface Notice {
  id: string;
  tone: "error" | "warning" | "info" | "success";
  text: string;
  title?: string;
}
const props = withDefaults(
  defineProps<{
    items: Notice[];
    /** Names the stack for assistive technology. */
    label: string;
    mode?: "dismiss" | "acknowledge";
    /** Show this many, then "Show N more". */
    limit?: number;
    disabled?: boolean;
  }>(),
  { mode: "dismiss", limit: 5, disabled: false },
);
const emit = defineEmits<{ dismiss: [id: string]; dismissAll: [ids: string[]] }>();
const i18n = useI18nStore();

const root = ref<HTMLElement | null>(null);
const expanded = ref(false);
const visible = computed(() =>
  expanded.value ? props.items : props.items.slice(0, Math.max(1, props.limit)),
);
const hidden = computed(() => props.items.length - visible.value.length);
const acknowledging = computed(() => props.mode === "acknowledge");
const ICONS: Record<Notice["tone"], string> = {
  error: "warning",
  warning: "warning",
  info: "help",
  success: "check",
};

function itemLabel(notice: Notice) {
  const text = notice.text.length > 90 ? `${notice.text.slice(0, 90)}…` : notice.text;
  return i18n.tf(acknowledging.value ? "ui.acknowledge_item" : "ui.dismiss_item", { text });
}

/**
 * Keep the keyboard in the stack: once the closed message has actually gone (the parent removes it), focus the one
 * that took its place, or the previous one, else the stack itself.
 */
let focusAfterRemoval: number | null = null;
function dismiss(notice: Notice, index: number) {
  focusAfterRemoval = index;
  emit("dismiss", notice.id);
}
watch(
  () => props.items.map((item) => item.id).join("\u0000"),
  () => {
    if (focusAfterRemoval === null) return;
    const index = focusAfterRemoval;
    focusAfterRemoval = null;
    void nextTick(() => {
      const buttons = [
        ...(root.value?.querySelectorAll<HTMLButtonElement>("[data-notice-dismiss]") || []),
      ];
      const next = buttons[Math.min(index, buttons.length - 1)];
      (next || root.value)?.focus();
    });
  },
);
function dismissAll() {
  emit(
    "dismissAll",
    props.items.map((item) => item.id),
  );
  void nextTick(() => root.value?.focus());
}
</script>

<template>
  <section v-if="items.length" ref="root" class="ui-notice-stack" :aria-label="label" tabindex="-1">
    <header v-if="items.length > 1" class="notice-stack-head">
      <span class="notice-count">{{ label }} · {{ items.length }}</span>
      <UiTooltip
        v-if="acknowledging"
        :text="i18n.t('ui.acknowledge_help')"
        trigger-mode="content"
        :content-focusable="disabled"
        placement="bottom"
      >
        <button type="button" class="notice-all" :disabled="disabled" @click="dismissAll">
          {{ i18n.t("ui.acknowledge_all") }}<AppIcon name="close" />
        </button>
      </UiTooltip>
      <button v-else type="button" class="notice-all" :disabled="disabled" @click="dismissAll">
        {{ i18n.t("ui.dismiss_all") }}<AppIcon name="close" />
      </button>
    </header>
    <ul class="notice-list">
      <li
        v-for="(notice, index) in visible"
        :key="notice.id"
        class="notice"
        :data-tone="notice.tone"
      >
        <span class="notice-icon" aria-hidden="true"><AppIcon :name="ICONS[notice.tone]" /></span>
        <!-- The role is on the text, not the list item, so the list stays a list for assistive technology. -->
        <span class="notice-text" :role="notice.tone === 'error' ? 'alert' : 'status'"
          ><b v-if="notice.title">{{ notice.title }}</b> {{ notice.text }}</span
        >
        <UiTooltip
          :text="acknowledging ? i18n.t('ui.acknowledge_help') : i18n.t('ui.dismiss')"
          trigger-mode="content"
          :content-focusable="disabled"
          placement="bottom"
        >
          <button
            type="button"
            class="notice-dismiss"
            data-notice-dismiss
            :disabled="disabled"
            :aria-label="itemLabel(notice)"
            @click="dismiss(notice, index)"
          >
            <AppIcon name="close" />
          </button>
        </UiTooltip>
      </li>
    </ul>
    <button
      v-if="hidden > 0 || (expanded && items.length > limit)"
      type="button"
      class="notice-more"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      {{ expanded ? i18n.t("ui.show_fewer") : i18n.tf("ui.show_more_count", { count: hidden }) }}
    </button>
  </section>
</template>

<style scoped>
.ui-notice-stack {
  display: grid;
  gap: 6px;
  min-width: 0;
}
.ui-notice-stack:focus-visible {
  outline: 3px solid var(--focus-ring, var(--accent));
  outline-offset: 2px;
  border-radius: var(--radius-control, 8px);
}
.notice-stack-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.notice-count {
  color: var(--text-tertiary, var(--muted));
  font-size: var(--fs-sm, 0.8125rem);
  font-weight: 700;
}
.notice-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.notice {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  padding: 6px 6px 6px 10px;
  border: 1px solid var(--border-subtle, var(--line));
  border-radius: var(--radius-control, 8px);
  background: var(--surface-inset, var(--soft));
  color: var(--text);
  font-size: var(--fs-sm, 0.8125rem);
  line-height: 1.45;
}
.notice[data-tone="error"] {
  border-color: var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
}
.notice[data-tone="warning"] {
  border-color: var(--tone-warn-edge, var(--tone-warn-border));
  background: var(--tone-warn-bg);
  color: var(--tone-warn-fg);
}
.notice[data-tone="info"] {
  border-color: var(--tone-info-edge, var(--tone-info-border));
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
}
.notice[data-tone="success"] {
  border-color: var(--tone-ok-edge, var(--tone-ok-border));
  background: var(--tone-ok-bg);
  color: var(--tone-ok-fg);
}
.notice-icon {
  display: inline-flex;
  flex: none;
  margin-top: 2px;
}
.notice-icon :deep(svg),
.notice-dismiss :deep(svg),
.notice-all :deep(svg) {
  inline-size: 14px;
  block-size: 14px;
}
.notice-text {
  flex: 1 1 auto;
  min-width: 0;
  overflow-wrap: anywhere;
  padding-top: 1px;
}
.notice-dismiss,
.notice-all,
.notice-more {
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.notice-dismiss {
  display: inline-grid;
  flex: none;
  place-items: center;
  inline-size: 28px;
  block-size: 28px;
  margin: -2px 0;
  border-radius: 6px;
  opacity: 0.8;
}
.notice-dismiss:hover:not(:disabled) {
  background: color-mix(in srgb, currentColor 12%, transparent);
  opacity: 1;
}
.notice-all {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
  padding: 0 6px;
  border-radius: 6px;
  color: var(--text-secondary, var(--muted));
  font-size: var(--fs-sm, 0.8125rem);
  font-weight: 700;
}
.notice-all:hover:not(:disabled) {
  background: var(--surface-hover);
}
.notice-more {
  justify-self: start;
  min-height: 28px;
  padding: 0;
  color: var(--accent-fg, var(--accent));
  font-size: var(--fs-sm, 0.8125rem);
  font-weight: 700;
}
:is(.notice-dismiss, .notice-all, .notice-more):focus-visible {
  outline: 3px solid var(--focus-ring, var(--accent));
  outline-offset: 1px;
}
:is(.notice-dismiss, .notice-all):disabled {
  cursor: default;
  opacity: 0.45;
}
@media (forced-colors: active) {
  .notice {
    border-color: CanvasText;
  }
}
</style>
