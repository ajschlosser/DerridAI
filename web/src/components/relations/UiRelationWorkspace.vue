<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    inspectorOpen?: boolean;
    inspectorLabel?: string;
  }>(),
  {
    inspectorOpen: false,
    inspectorLabel: "",
  },
);
</script>

<template>
  <section class="ui-relation-workspace" :class="{ 'has-inspector': inspectorOpen }">
    <header v-if="$slots.header || $slots.toolbar" class="ui-relation-workspace-header">
      <div v-if="$slots.header" class="ui-relation-workspace-heading"><slot name="header" /></div>
      <div v-if="$slots.toolbar" class="ui-relation-workspace-toolbar"><slot name="toolbar" /></div>
    </header>
    <div class="ui-relation-workspace-body">
      <div class="ui-relation-workspace-main"><slot /></div>
      <aside
        v-if="inspectorOpen && $slots.inspector"
        class="ui-relation-workspace-inspector"
        :aria-label="inspectorLabel || undefined"
      >
        <slot name="inspector" />
      </aside>
    </div>
    <footer v-if="$slots.footer" class="ui-relation-workspace-footer"><slot name="footer" /></footer>
  </section>
</template>

<style scoped>
.ui-relation-workspace {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  gap: var(--space-3, 12px);
  color: var(--text-primary);
}
.ui-relation-workspace-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2, 8px);
}
.ui-relation-workspace-heading,
.ui-relation-workspace-toolbar,
.ui-relation-workspace-main {
  min-width: 0;
}
.ui-relation-workspace-body {
  display: grid;
  min-width: 0;
  min-height: 0;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-3, 12px);
}
.ui-relation-workspace.has-inspector .ui-relation-workspace-body {
  grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
}
.ui-relation-workspace-inspector {
  min-width: 0;
  overflow: auto;
}
@media (max-width: 800px) {
  .ui-relation-workspace.has-inspector .ui-relation-workspace-body {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
