<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(
  defineProps<{
    kicker?: string;
    title: string;
    description?: string;
    titleId?: string;
    actionsLabel?: string;
  }>(),
  {
    kicker: "",
    description: "",
    titleId: "page-title",
    actionsLabel: "",
  },
);
</script>

<template>
  <header class="ui-page-header" :aria-labelledby="titleId">
    <div class="ui-page-header-heading">
      <p v-if="kicker" class="ui-page-header-kicker">{{ kicker }}</p>
      <h1 :id="titleId">{{ title }}</h1>
      <p v-if="description" class="ui-page-header-description">{{ description }}</p>
    </div>
    <div
      v-if="$slots.actions"
      class="ui-page-header-actions"
      :aria-label="actionsLabel || undefined"
    >
      <slot name="actions" />
    </div>
    <div v-if="$slots.meta" class="ui-page-header-meta">
      <slot name="meta" />
    </div>
  </header>
</template>

<style scoped>
.ui-page-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: start;
  padding: 4px 2px;
}

.ui-page-header-heading {
  min-width: 0;
}

.ui-page-header-kicker {
  margin: 0 0 4px;
  color: var(--accent-fg);
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
  letter-spacing: 0.08em;
  line-height: var(--lh-tight);
  text-transform: uppercase;
}

.ui-page-header h1 {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-reading);
  font-size: clamp(1.5rem, 2.2vw, 2rem);
  font-weight: var(--fw-semibold);
  letter-spacing: -0.02em;
  line-height: var(--lh-tight);
}

.ui-page-header-description {
  max-width: var(--measure);
  margin: 8px 0 0;
  color: var(--text-tertiary);
  font-size: var(--fs-base);
  line-height: var(--lh-normal);
}

.ui-page-header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.ui-page-header-meta {
  grid-column: 1 / -1;
  min-width: 0;
}

@media (max-width: 800px) {
  .ui-page-header {
    grid-template-columns: 1fr;
  }

  .ui-page-header-actions {
    justify-content: flex-start;
  }
}
</style>
