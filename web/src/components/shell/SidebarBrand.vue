<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { useI18nStore } from "../../stores/i18n";
import AppIcon from "../AppIcon.vue";
import BrandMark from "../BrandMark.vue";

defineProps<{ collapsed: boolean }>();
defineEmits<{ "navigate-home": []; toggle: [] }>();
const i18n = useI18nStore();
</script>
<template>
  <div class="shell-brand-row">
    <button
      class="shell-brand-button"
      type="button"
      :title="i18n.t('nav.home')"
      :aria-label="collapsed ? i18n.t('nav.home') : undefined"
      @click="$emit('navigate-home')"
    >
      <BrandMark :size="collapsed ? 34 : 46" compact /><span
        v-if="!collapsed"
        class="shell-brand-word"
        >DerridAI</span
      >
    </button>
    <button
      class="sidebar-toggle"
      type="button"
      :title="collapsed ? i18n.t('ui.expand_sidebar') : i18n.t('ui.collapse_sidebar')"
      :aria-label="collapsed ? i18n.t('ui.expand_sidebar') : i18n.t('ui.collapse_sidebar')"
      :aria-pressed="collapsed"
      @click="$emit('toggle')"
    >
      <AppIcon :name="collapsed ? 'chevron-right' : 'chevron-left'" aria-hidden="true" />
    </button>
  </div>
</template>
