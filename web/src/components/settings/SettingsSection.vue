<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import UiCard from "../ui/UiCard.vue";
import SettingsSaveState from "./SettingsSaveState.vue";
import type { SaveStatus } from "../../domain/settings";

withDefaults(
  defineProps<{
    sectionId: string;
    title: string;
    description: string;
    persistence: string;
    status?: SaveStatus;
    statusLabel?: string;
    headingLevel?: 2 | 3;
  }>(),
  { status: "saved", statusLabel: "", headingLevel: 2 },
);
</script>
<template>
  <UiCard
    :as="'section'"
    class="settings-section"
    :padded="false"
    :heading-id="`settings-heading-${sectionId}`"
  >
    <header class="settings-section-head">
      <div>
        <p class="settings-kicker">{{ persistence }}</p>
        <component :is="`h${headingLevel}`" :id="`settings-heading-${sectionId}`">{{
          title
        }}</component>
        <p class="settings-section-copy">{{ description }}</p>
      </div>
      <SettingsSaveState v-if="statusLabel" :status="status" :label="statusLabel" />
    </header>
    <div class="settings-section-body">
      <slot />
    </div>
    <footer v-if="$slots.actions" class="settings-section-actions">
      <slot name="actions" />
    </footer>
  </UiCard>
</template>
<style scoped>
.settings-section {
  display: grid;
  gap: 16px;
  padding: 20px;
}
.settings-section-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  flex-wrap: wrap;
}
.settings-kicker {
  margin: 0 0 4px;
  font-size: 0.8125rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-fg);
}
.settings-section-head :is(h2, h3) {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.25rem;
  line-height: 1.25;
  font-weight: 650;
}
.settings-section-copy {
  margin: 6px 0 0;
  max-width: 68ch;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.5;
}
.settings-section-body {
  display: grid;
  gap: 14px;
}
.settings-section-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding-top: 4px;
}
@media (max-width: 640px) {
  .settings-section {
    padding: 16px;
  }
  .settings-section-head :is(h2, h3) {
    font-size: 1.125rem;
  }
}
</style>
