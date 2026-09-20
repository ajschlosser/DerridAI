<script setup lang="ts">
// The bar at the foot of a metadata form: what will change, in words, and the buttons that act on it.
defineProps<{ summary: string; detail?: string; sticky?: boolean }>();
</script>

<template>
  <footer class="metadata-form-footer" :class="{ 'is-sticky': sticky }" aria-live="polite">
    <div class="metadata-form-summary"><b>{{ summary }}</b><span v-if="detail">{{ detail }}</span></div>
    <div class="metadata-form-buttons"><slot /></div>
  </footer>
</template>

<style scoped>
.metadata-form-footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding-top: 14px; border-top: 1px solid var(--line); }
/* On a long form the actions stay in reach at the bottom of the panel that scrolls. */
.metadata-form-footer.is-sticky { position: sticky; bottom: -20px; z-index: 3; margin: 2px -22px -20px; padding: 14px 22px; background: var(--panel); box-shadow: 0 -10px 24px color-mix(in srgb, var(--text) 8%, transparent); }
.metadata-form-summary { display: grid; gap: 2px; min-inline-size: 0; }
.metadata-form-summary b { font-size: 0.875rem; }
.metadata-form-summary span { font-size: 0.8125rem; color: var(--muted); line-height: 1.45; }
.metadata-form-buttons { display: flex; gap: 8px; flex: none; }
@media (max-width: 640px) {
  .metadata-form-footer { flex-direction: column; align-items: stretch; }
  .metadata-form-buttons > * { flex: 1; }
}
</style>
