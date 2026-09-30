<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import BrandMark from "../BrandMark.vue";
import UiTooltip from "../ui/UiTooltip.vue";

defineProps<{ collapsed: boolean }>();
defineEmits<{ "navigate-home": []; toggle: [] }>();
const i18n = useI18nStore();
</script>
<template>
  <div class="shell-brand-row">
    <UiTooltip
      :text="i18n.t('nav.home')"
      trigger-mode="content"
      :content-focusable="false"
      placement="bottom"
    >
      <button
        class="shell-brand-button"
        type="button"
        :aria-label="collapsed ? i18n.t('nav.home') : undefined"
        @click="$emit('navigate-home')"
      >
        <BrandMark :size="collapsed ? 34 : 46" compact /><span
          v-if="!collapsed"
          class="shell-brand-word"
          >DerridAI</span
        >
      </button>
    </UiTooltip>
    <UiTooltip
      :text="collapsed ? i18n.t('ui.expand_sidebar') : i18n.t('ui.collapse_sidebar')"
      trigger-mode="content"
      :content-focusable="false"
      placement="bottom"
    >
      <button
        class="sidebar-toggle"
        type="button"
        :aria-label="collapsed ? i18n.t('ui.expand_sidebar') : i18n.t('ui.collapse_sidebar')"
        :aria-pressed="collapsed"
        @click="$emit('toggle')"
      >
        <AppIcon :name="collapsed ? 'chevron-right' : 'chevron-left'" aria-hidden="true" />
      </button>
    </UiTooltip>
  </div>
</template>

<style scoped>
.shell-brand-row {
  min-height: 58px;
  margin-bottom: 10px;
  padding-bottom: 9px;
  border-bottom: 1px solid color-mix(in srgb, var(--line) 72%, transparent);
}

.shell-brand-button {
  min-height: 40px;
  border-radius: 10px;
  transition:
    background-color var(--motion-fast, 120ms) var(--ease-standard, ease),
    color var(--motion-fast, 120ms) var(--ease-standard, ease);
}

.shell-brand-button:hover,
.shell-brand-button:focus-visible {
  background: var(--surface-hover);
  color: var(--text);
}

.shell-brand-word {
  letter-spacing: -0.025em;
}

.sidebar-toggle {
  flex-basis: 32px;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  transition:
    background-color var(--motion-fast, 120ms) var(--ease-standard, ease),
    color var(--motion-fast, 120ms) var(--ease-standard, ease);
}

.sidebar-toggle:hover,
.sidebar-toggle:focus-visible {
  background: var(--surface-hover);
  color: var(--text);
}

@media (prefers-reduced-motion: reduce) {
  .shell-brand-button,
  .sidebar-toggle {
    transition: none;
  }
}
</style>
